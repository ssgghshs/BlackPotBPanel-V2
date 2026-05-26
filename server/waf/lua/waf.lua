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
-- Payload 特征驱动分类器（与检测模块解耦）
-- ============================================================

local function classify_payload(payload)
    if not payload then return nil end
    local lower = string.lower(payload)
    local upper = string.upper(payload)

    -- XSS: 标签 + 事件 + 协议特征（高度特异性）
    local xss_patterns = {
        "<script", "javascript:", "onerror=", "onload=",
        "onclick=", "onmouseover=", "onfocus=", "onblur=",
        "onchange=", "onsubmit=",
        "<img ", "<svg ", "<iframe", "<body",
        "document%.cookie", "alert%(", "confirm%(", "prompt%(",
        "<a href=", "expression%("
    }
    for _, p in ipairs(xss_patterns) do
        if string.find(lower, p, 1, true) then return "xss" end
    end

    -- SQL: 关键字 + 运算符特征（高度特异性）
    local sql_patterns = {
        "UNION", "SELECT", "INSERT", "UPDATE", "DELETE", "DROP",
        "CREATE", "ALTER", "EXECUTE", "FROM", "WHERE",
        "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET",
        "INFORMATION_SCHEMA", "SLEEP%(", "BENCHMARK%(",
        "COUNT%(", "CONCAT%(", "SUBSTR", "MID%(",
        "LOAD_FILE%(", "INTO OUTFILE", "INTO DUMPFILE",
        "%27 OR ", "%27 AND "
    }
    for _, p in ipairs(sql_patterns) do
        if string.find(upper, p, 1, true) then return "sql" end
    end

    return nil
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
    -- 0. 静态资源白名单
    if _M.is_static_resource() then return true end

    -- 1. 正常路由白名单
    local uri = ngx.var.request_uri or ""
    local config = _M.load_whitelist_config()
    for _, route in ipairs(config.normal_routes) do
        if string.sub(uri, 1, string.len(route)) == route then return true end
    end

    -- 2. 维护模式
    local waf_mode = ngx.var.waf_mode or ""
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
