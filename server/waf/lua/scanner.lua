local _M = {}
local json = require "cjson"
local logger = require "logger"

-- 配置缓存
local _config_cache = nil

-- 辅助函数：将数组转换为正则表达式字符串
local function build_regex(arr)
    if not arr or #arr == 0 then return nil end
    local escaped_arr = {}
    for i, v in ipairs(arr) do
        -- 对正则特殊字符进行基础转义，或直接拼接（如果确定配置中是纯文本）
        escaped_arr[i] = v:gsub("[%[%]%(%)%|%*%+%?%.%^%$]", "\\%0")
    end
    return "(?i)" .. table.concat(escaped_arr, "|")
end

-- 辅助函数：仅获取基础 URL（协议://主机[:端口]）
local function get_base_url()
    local scheme = ngx.var.scheme or "http"
    local host = ngx.var.host or ""
    local port = ngx.var.server_port or ""
    local url = scheme .. "://" .. host
    if (scheme == "http" and port ~= "80") or (scheme == "https" and port ~= "443") then
        url = url .. ":" .. port
    end
    return url
end

function _M.load_config()
    -- 如果生产环境配置不频繁变动，可以加缓存逻辑，这里演示实时加载
    local config_path = "/usr/local/openresty/nginx/rules/scanner/config.json"
    local file = io.open(config_path, "r")
    
    local default_config = { enabled = true, action = "block" }

    if not file then return default_config end
    local content = file:read("*all")
    file:close()

    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end

    -- --- 预处理阶段：提升性能的核心 ---
    
    -- 1. 编译 User-Agent 正则 (排除白名单爬虫)
    config.ua_regex = build_regex(config.scanner_user_agents)
    config.crawler_regex = build_regex(config.allowed_crawlers)

    -- 2. 编译 Path 正则（锚定开头，防止 /settings 误匹配 /rest/settings）
    config.path_regex = build_regex(config.scanner_paths)
    if config.path_regex then
        config.path_regex = "(?i)^(?:" .. config.path_regex:sub(4) .. ")"
    end

    -- 3. 将排除路径转为 Hash Set (前缀匹配)
    config.exclude_set = {}
    if config.exclude_paths then
        for _, p in ipairs(config.exclude_paths) do config.exclude_set[p] = true end
    end

    -- 4. 预解析 Scanner Headers 为高效 Table
    config.header_rules = {}
    if config.scanner_headers then
        for _, h in ipairs(config.scanner_headers) do
            local name, value = string.match(h, "([^:]+):%s*(.+)")
            if name and value then
                config.header_rules[string.lower(name)] = value
            end
        end
    end

    return config
end

function _M.check()
    -- 站点开关
    if ngx.var.scanner_enabled == "0" then return true end

    local config = _M.load_config()
    if not config.enabled then return true end

    local uri = ngx.var.uri
    local client_ip = ngx.var.remote_addr
    local base_url = get_base_url()

    -- 1. 排除路径检查 (前缀匹配)
    -- 优化：先尝试直接查找，再尝试前缀匹配
    if config.exclude_set[uri] then return true end
    for path, _ in pairs(config.exclude_set) do
        if string.sub(uri, 1, #path) == path then return true end
    end

    local headers = ngx.req.get_headers()
    local ua = headers["user-agent"]

    -- 2. User-Agent 检查
    if not ua or ua == "" then
        -- 多数扫描器不带 UA
        return _M.log_and_block("Scanner Protection", "Empty User-Agent", config, base_url)
    end

    -- 先查爬虫白名单 (利用 JIT 化的正则)
    if config.crawler_regex then
        local is_crawler, _ = ngx.re.find(ua, config.crawler_regex, "jo")
        if is_crawler then return true end
    end

    -- 再查扫描器黑名单
    if config.ua_regex then
        local is_scanner, _ = ngx.re.find(ua, config.ua_regex, "jo")
        if is_scanner then
            return _M.log_and_block("Scanner Protection", "Suspicious UA: " .. ua, config, base_url)
        end
    end

    -- 3. 危险路径正则匹配
    if config.path_regex then
        local is_bad_path, _ = ngx.re.find(uri, config.path_regex, "jo")
        if is_bad_path then
            return _M.log_and_block("Scanner Protection", "Suspicious Path: " .. uri, config, base_url)
        end
    end

    -- 4. 恶意 Header 特征检查 (O(1) 查找)
    for name, expected_val in pairs(config.header_rules) do
        local actual_val = headers[name]
        if actual_val and string.find(actual_val, expected_val, 1, true) then
            return _M.log_and_block("Scanner Protection", "Suspicious Header: " .. name, config, base_url)
        end
    end

    return true
end

function _M.log_and_block(attack_type, reason, config, base_url)
    local client_ip = ngx.var.remote_addr

    -- 获取 WAF 模式并标准化 action 值
    local waf_mode = ngx.var.waf_mode or config.action or "record"
    -- 标准化 action 值：block -> blocked, record -> record
    local action = waf_mode == "block" and "blocked" or waf_mode

    -- 记录日志
    logger.log_attack(
        "scanner",
        client_ip,
        ngx.var.host,
        ngx.var.request_uri,
        ngx.var.request_method,
        reason,
        {
            action = action,
            application_url = base_url
        }
    )

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"

        local html_path = "/usr/local/openresty/nginx/waf_html/waf_blocked.html"
        local f = io.open(html_path, "r")
        local content = f and f:read("*all") or "<h1>403 Forbidden</h1><p>Scanner access denied.</p>"
        if f then f:close() end

        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", attack_type))
        ngx.exit(403)
        return false
    end
    return true
end

return _M