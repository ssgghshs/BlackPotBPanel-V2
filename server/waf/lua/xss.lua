local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/xss/config.json"
    local default_config = {
        enabled = true,
        action = "record",
        rules = { "<script", "javascript:", "onerror", "onload" }
    }

    local file = io.open(config_path, "r")
    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end
    return config
end

function _M.check_xss_injection(value, rules)
    if not value or type(value) ~= "string" then return false end
    for _, rule in ipairs(rules) do
        local ok, err = ngx.re.find(value, rule, "is")
        if ok then return true end
    end
    return false
end

function _M.evaluate()
    if ngx.var.xss_enabled == "0" then return nil end
    local config = _M.load_config()
    if not config.enabled then return nil end

    -- 1. 检查 URL 参数值 (GET) - 仅检查值，不检查参数名
    local args = ngx.req.get_uri_args()
    if args then
        for _, val in pairs(args) do
            if type(val) == "table" then val = table.concat(val, " ") end
            if _M.check_xss_injection(val, config.rules) then
                return { hit = true, reason = "XSS in URL Args", attack_type = "xss", action = ngx.var.waf_mode or config.action or "record" }
            end
        end
    end

    -- 2. 检查 POST 请求体
    if ngx.var.request_method == "POST" then
        ngx.req.read_body()
        local post_args = ngx.req.get_post_args()
        if post_args then
            for _, val in pairs(post_args) do
                if type(val) == "table" then val = table.concat(val, " ") end
                if _M.check_xss_injection(val, config.rules) then
                    return { hit = true, reason = "XSS in POST Args", attack_type = "xss", action = ngx.var.waf_mode or config.action or "record" }
                end
            end
        end
        local body = ngx.req.get_body_data()
        if body and _M.check_xss_injection(body, config.rules) then
            return { hit = true, reason = "XSS in POST Body", attack_type = "xss", action = ngx.var.waf_mode or config.action or "record" }
        end
    end

    -- 3. 检查 Cookie
    local cookies = ngx.var.http_cookie
    if cookies and _M.check_xss_injection(cookies, config.rules) then
        return { hit = true, reason = "XSS in Cookie", attack_type = "xss", action = ngx.var.waf_mode or config.action or "record" }
    end

    -- 4. 检查常用的 Header 字段
    local headers = { "user-agent", "referer" }
    for _, h in ipairs(headers) do
        local val = ngx.var["http_" .. h:gsub("-", "_")]
        if val and _M.check_xss_injection(val, config.rules) then
            return { hit = true, reason = "XSS in Header: " .. h, attack_type = "xss", action = ngx.var.waf_mode or config.action or "record" }
        end
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
    logger.log_attack("xss", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", "XSS Protection"))
        ngx.exit(403)
        return false
    end
    return true
end

return _M
