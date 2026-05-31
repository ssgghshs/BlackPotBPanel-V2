local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_whitelist_config()
    local config_path = "/usr/local/openresty/nginx/rules/urlwhitelist/config.json"
    local default_config = {
        enabled = true,
        normal_routes = {
            "/", "/login", "/logout", "/register", "/home",
            "/dashboard", "/api/", "/admin/"
        },
        static_paths = {
            "/assets/", "/static/", "/images/", "/img/",
            "/css/", "/js/", "/fonts/", "/uploads/", "/media/"
        },
        static_extensions = {
            ".css", ".js", ".jpg", ".jpeg", ".png", ".gif", ".ico",
            ".svg", ".woff", ".woff2", ".ttf", ".eot", ".otf",
            ".mp4", ".webm", ".mp3", ".wav",
            ".pdf", ".zip", ".rar", ".7z", ".gz", ".tar", ".bz2"
        }
    }

    local file = io.open(config_path, "r")
    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then
        ngx.log(ngx.ERR, "[WAF] Whitelist Config Parse Error: " .. tostring(config))
        return default_config
    end
    return config
end

function _M.is_static_resource()
    local uri = ngx.var.request_uri or ""
    local config = _M.load_whitelist_config()

    for _, ext in ipairs(config.static_extensions) do
        if string.sub(uri, -string.len(ext)) == ext then return true end
    end
    for _, path in ipairs(config.static_paths) do
        if string.sub(uri, 1, string.len(path)) == path then return true end
    end
    return false
end

-- ============================================================
-- 全量攻击检测引擎
-- ============================================================

-- ============================================================
-- Payload 特征驱动分类器（特异性评分机制）
-- ============================================================
-- 参考 AAWAF 设计原则：
-- 1. 特异性越高的规则权重越大（如 UNION SELECT > <script）
-- 2. 综合得分最高的类型胜出，而非先到先得
-- 3. 所有攻击类型（cmd/ssrf/ldap/file_inclusion/sql/xss）纳入评分
-- 4. 没有特征匹配时，按危险度优先级（RCE > SSRF > SQL > ...）取结果

local function classify_payload(payload)
    if not payload then return nil end
    local lower = string.lower(payload)
    local upper = string.upper(payload)

    local scores = {
        cmd_injection = 0,
        ssrf = 0,
        ldap_injection = 0,
        file_inclusion = 0,
        sql = 0,
        xss = 0,
    }

    -- 规则表：{ 文本, 使用大写, 类别, 权重 }
    -- use_upper=true 匹配 upper，否则匹配 lower
    local rules = {
        -- cmd_injection: shell 元字符 + 系统命令（RCE，最高危）
        { ";cat ", true, "cmd_injection", 25 },
        { ";ls ", true, "cmd_injection", 25 },
        { ";id ", true, "cmd_injection", 25 },
        { ";whoami", true, "cmd_injection", 25 },
        { ";pwd ", true, "cmd_injection", 22 },
        { ";curl ", true, "cmd_injection", 22 },
        { ";wget ", true, "cmd_injection", 22 },
        { ";bash ", true, "cmd_injection", 22 },
        { ";sh ", true, "cmd_injection", 20 },
        { ";nc ", true, "cmd_injection", 20 },
        { ";net ", true, "cmd_injection", 15 },
        { ";ping ", true, "cmd_injection", 15 },
        { ";php ", true, "cmd_injection", 15 },
        { ";python", true, "cmd_injection", 15 },
        { "`cat", false, "cmd_injection", 25 },
        { "`id", false, "cmd_injection", 25 },
        { "`ls", false, "cmd_injection", 22 },
        { "$(", false, "cmd_injection", 20 },
        { "exec(", false, "cmd_injection", 18 },
        { "system(", false, "cmd_injection", 18 },
        { "passthru(", false, "cmd_injection", 18 },
        { "shell_exec(", false, "cmd_injection", 18 },
        { "popen(", false, "cmd_injection", 18 },
        { "eval(", false, "cmd_injection", 15 },

        -- ssrf: 危险协议 + 内网地址
        { "gopher://", false, "ssrf", 25 },
        { "dict://", false, "ssrf", 25 },
        { "expect://", false, "ssrf", 25 },
        { "tftp://", false, "ssrf", 20 },
        { "jar://", false, "ssrf", 20 },
        { "netdoc://", false, "ssrf", 20 },
        { "file://", false, "ssrf", 12 },
        { "127.0.0.1", false, "ssrf", 10 },
        { "0.0.0.0", false, "ssrf", 10 },
        { "localhost", false, "ssrf", 6 },

        -- ldap_injection: LDAP 过滤器语法
        { ")(&(", false, "ldap_injection", 25 },
        { ")(|(", false, "ldap_injection", 25 },
        { ")(!(", false, "ldap_injection", 25 },
        { "objectclass=", false, "ldap_injection", 15 },
        { "uid=*", false, "ldap_injection", 10 },
        { "cn=*", false, "ldap_injection", 10 },

        -- file_inclusion: PHP 封装器 + 路径穿越
        { "php://", false, "file_inclusion", 22 },
        { "phar://", false, "file_inclusion", 22 },
        { "zip://", false, "file_inclusion", 20 },
        { "/etc/passwd", false, "file_inclusion", 15 },
        { "/windows/win.ini", false, "file_inclusion", 15 },
        { "../..", false, "file_inclusion", 8 },
        { "..\\..", false, "file_inclusion", 8 },
        { "%2e%2e%2f", true, "file_inclusion", 12 },
        { "%2e%2e%5c", true, "file_inclusion", 12 },

        -- sql: 高特异性关键字
        { "UNION(", true, "sql", 20 },
        { "UNION ALL", true, "sql", 20 },
        { "UNION SELECT", true, "sql", 30 },
        { "INSERT INTO", true, "sql", 20 },
        { "DELETE FROM", true, "sql", 20 },
        { "INFORMATION_SCHEMA", true, "sql", 25 },
        { "SLEEP(", true, "sql", 20 },
        { "BENCHMARK(", true, "sql", 20 },
        { "LOAD_FILE(", true, "sql", 25 },
        { "INTO OUTFILE", true, "sql", 25 },
        { "INTO DUMPFILE", true, "sql", 25 },
        { "CONCAT(", true, "sql", 10 },
        { "SUBSTRING(", true, "sql", 10 },
        { "MID(", true, "sql", 5 },
        { "' OR ", true, "sql", 15 },
        { " OR '1'='1", true, "sql", 20 },
        { " OR 1=1", true, "sql", 15 },
        { " AND '1'='1", true, "sql", 15 },
        { " AND 1=1", true, "sql", 10 },
        { "SELECT ", true, "sql", 4 },
        { "DROP ", true, "sql", 15 },
        { "FROM ", true, "sql", 2 },
        { "WHERE ", true, "sql", 2 },
        { "GROUP BY", true, "sql", 8 },
        { "ORDER BY", true, "sql", 8 },

        -- xss: 低权重避免误判
        { "document.cookie", false, "xss", 12 },
        { "javascript:", false, "xss", 10 },
        { "onerror=", false, "xss", 8 },
        { "onload=", false, "xss", 8 },
        { "alert(", false, "xss", 8 },
        { "confirm(", false, "xss", 8 },
        { "prompt(", false, "xss", 8 },
        { "<iframe", false, "xss", 8 },
        { "<script", false, "xss", 5 },
        { "<svg ", false, "xss", 5 },
        { "<img ", false, "xss", 4 },
        { "onfocus=", false, "xss", 4 },
        { "onclick=", false, "xss", 4 },
        { "<a href=", false, "xss", 4 },
        { "onmouseover=", false, "xss", 6 },
        { "expression(", false, "xss", 10 },
        { "onblur=", false, "xss", 3 },
        { "onchange=", false, "xss", 3 },
        { "onsubmit=", false, "xss", 4 },
        { "<body", false, "xss", 2 },
    }

    for _, rule in ipairs(rules) do
        local source = rule[2] and upper or lower
        if string.find(source, rule[1], 1, true) then
            scores[rule[3]] = scores[rule[3]] + rule[4]
        end
    end

    -- 找出得分最高的类别
    local best_type = nil
    local best_score = 0
    for t, s in pairs(scores) do
        if s > best_score then
            best_score = s
            best_type = t
        end
    end

    return best_type
end

-- 全量检测 + payload驱动分类
-- 返回值: 命中结果 table 或 nil, 所有命中列表
function _M.evaluate_all_attacks()
    local hits = {}
    local modules = {
        "cmd_injection", "ssrf", "ldap_injection",
        "sql", "csrf", "file_inclusion",
        "file_upload", "xss"
    }

    for _, name in ipairs(modules) do
        local mod = require(name)
        local ok, result = pcall(mod.evaluate)
        if ok and result then
            result.module_name = name
            hits[#hits + 1] = result
        end
    end

    if #hits == 0 then return nil end

    if #hits == 1 then
        return hits[1], hits
    end

    -- 多个命中：payload驱动分类
    local uri = ngx.var.request_uri or ""
    local payload = uri
    if ngx.var.request_method == "POST" then
        ngx.req.read_body()
        local body = ngx.req.get_body_data()
        if body then payload = payload .. body end
    end
    -- URL解码后再分类，否则 %3C/UNION%20SELECT 匹配不到 <script/UNION SELECT
    payload = ngx.unescape_uri(payload)

    local best_type = classify_payload(payload)
    -- 兜底：按危险度优先级取第一个命中（cmd > ssrf > ldap > sql > csrf > file_inclusion > file_upload > xss）
    local best_hit = hits[1]

    if best_type then
        for _, h in ipairs(hits) do
            if h.module_name == best_type then
                best_hit = h
                break
            end
        end
    end

    return best_hit, hits
end

-- 统一处理攻击结果：全量日志 + 最优拦截
function _M.handle_attack_results(best_hit, all_hits)
    local waf_mode = best_hit.action
    local hit_count = all_hits and #all_hits or 0

    -- 全量日志：所有条目统一使用最终分类的 attack_type
    if hit_count > 0 then
        for i = 1, hit_count do
            local h = all_hits[i]
            if h then
                local action = h.action == "block" and "blocked" or h.action
                local meta = {
                    action = action,
                    detected_by = h.attack_type,
                    detected_reason = h.reason
                }
                local log_ok = logger.log_attack(best_hit.attack_type, ngx.var.remote_addr, ngx.var.host,
                    ngx.var.request_uri, ngx.var.request_method,
                    best_hit.reason, meta)
                if not log_ok then
                    ngx.log(ngx.ERR, "[WAF] Failed to write attack log for " .. best_hit.attack_type)
                end
            end
        end
    elseif best_hit then
        local action = waf_mode == "block" and "blocked" or waf_mode
        local log_ok = logger.log_attack(best_hit.attack_type, ngx.var.remote_addr, ngx.var.host,
            ngx.var.request_uri, ngx.var.request_method,
            best_hit.reason, { action = action })
        if not log_ok then
            ngx.log(ngx.ERR, "[WAF] Failed to write attack log for " .. best_hit.attack_type)
        end
    end

    -- 最优拦截
    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        content = content:gsub("{{reason}}", best_hit.reason)
        content = content:gsub("{{attack_type}}", best_hit.attack_type)
        ngx.say(content)
        ngx.exit(403)
    end
end

-- ============================================================
-- 主入口
-- ============================================================

function _M.check()
    -- 0. 加载站点 JSON 配置并写入 ngx.var
    local site_config = require("site_config")
    site_config.apply_to_ngx_var()

    -- 1. 静态资源白名单
    if _M.is_static_resource() then return true end

    -- 1. 正常路由白名单
    local uri = ngx.var.request_uri or ""
    local config = _M.load_whitelist_config()
    for _, route in ipairs(config.normal_routes) do
        if string.sub(uri, 1, string.len(route)) == route then return true end
    end

    -- 2. 维护模式
    local waf_mode = site_config.get("waf_mode", "")
    if waf_mode == "Maintenance" then
        local file = io.open("/usr/local/openresty/nginx/waf_html/maintenance.html", "r")
        if file then
            local content = file:read("*a")
            file:close()
            ngx.status = 503
            ngx.header.content_type = "text/html"
            ngx.say(content)
            ngx.exit(503)
        else
            ngx.status = 503
            ngx.header.content_type = "text/html"
            ngx.say("<html><body><h1>System under maintenance</h1><p>Please try again later.</p></body></html>")
            ngx.exit(503)
        end
    end

    -- 3. 黑白名单（基础访问控制，短路机制）
    local blackwhite = require "blackwhite"
    if not blackwhite.check() then return false end

    -- 4. 扫描器与爬虫识别
    local scanner = require "scanner"
    if not scanner.check() then return false end

    -- 5. BOT 验证
    local bot = require "bot"
    if not bot.check() then return false end

    -- 6. CC 防护
    local cc = require "cc"
    if not cc.check() then return false end

    -- ============================================================
    -- 攻击检测：全量评估 + 最优分类（不再短路）
    -- ============================================================
    local best_hit, all_hits = _M.evaluate_all_attacks()
    if best_hit then
        _M.handle_attack_results(best_hit, all_hits)
        return false
    end

    return true
end

_M.check()
