local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/cmd/config.json"
    local default_config = {
        enabled = true,
        action = "record",
        -- 核心规则建议在 JSON 中更新，此处为兜底
        rules = {
            "[;\\|&\\x60\\n\\r]\\s*\\b(cat|ls|id|whoami|pwd|curl|wget|bash|sh|php|python|ping|nc|cmd|net)\\b",
            "\\$\\s*\\(",
            "\\b(exec|eval|passthru|system|shell_exec|popen)\\s*\\(",
            "\\x60.*?\\x60"
        }
    }
    local file = io.open(config_path, "r")
    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end
    return config
end

function _M.check_cmd_injection(value, rules)
    if not value or type(value) ~= "string" or #value < 3 then return false end
    local unv = ngx.unescape_uri(value)
    for _, rule in ipairs(rules) do
        local ok, _ = ngx.re.find(unv, rule, "is")
        if ok then return true end
    end
    return false
end

-- 仅检查 Value，忽略 Key，减少 50% 误报
local function check_table_data(data, rules)
    if not data then return nil end
    for _, val in pairs(data) do
        if type(val) == "string" then
            if _M.check_cmd_injection(val, rules) then return val end
        elseif type(val) == "table" then
            for _, v in ipairs(val) do
                if type(v) == "string" and _M.check_cmd_injection(v, rules) then return v end
            end
        end
    end
    return nil
end

function _M.evaluate()
    if ngx.var.cmd_injection_enabled == "0" then return nil end
    local config = _M.load_config()
    if not config.enabled then return nil end

    local hit_val = nil

    -- 1. 检查 GET/POST
    hit_val = check_table_data(ngx.req.get_uri_args(), config.rules)
    if not hit_val and ngx.var.request_method == "POST" then
        ngx.req.read_body()
        hit_val = check_table_data(ngx.req.get_post_args(), config.rules)
        if not hit_val then
            local body = ngx.req.get_body_data()
            if body and _M.check_cmd_injection(body, config.rules) then hit_val = "Body Content" end
        end
    end

    -- 2. 检查 Header (User-Agent 和 Referer)
    if not hit_val then
        local headers = { "user-agent", "referer" }
        for _, h in ipairs(headers) do
            local val = ngx.var["http_" .. h:gsub("-", "_")]
            if val then
                for _, rule in ipairs(config.rules) do
                    if string.find(rule, "b%(") or string.find(rule, "b") then
                        if ngx.re.find(ngx.unescape_uri(val), rule, "is") then
                            hit_val = "Header: " .. h
                            break
                        end
                    end
                end
            end
        end
    end

    if hit_val then
        return {
            hit = true,
            reason = "CMD Injection detected: " .. hit_val,
            attack_type = "cmd_injection",
            action = ngx.var.waf_mode or config.action or "record"
        }
    end
    return nil
end

function _M.check()
    local result = _M.evaluate()
    if result then
        _M.block_request(result.reason, result.action)
        return false
    end
    return true
end

function _M.block_request(reason, waf_mode)
    local action = waf_mode == "block" and "blocked" or waf_mode
    logger.log_attack("cmd_injection", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", "Command Injection Protection"))
        ngx.exit(403)
    end
end

return _M
