local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/ldap_injection/config.json"
    local default_config = {
        enabled = true,
        action = "block",
        rules = {
            "\\)\\s*\\(\\s*[&|!]\\s*\\(",
            "\\b(?:objectClass|uid|cn)\\s*=\\s*\\*",
            "\\x00"
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

function _M.check_injection(value, rules)
    if not value or type(value) ~= "string" or #value < 4 then
        return false
    end

    local unescaped_value = ngx.unescape_uri(value)

    for _, rule in ipairs(rules) do
        local ok, err = ngx.re.find(unescaped_value, rule, "is")
        if ok then return true, rule end
    end
    return false
end

local function check_data(data, rules)
    if not data then return nil end
    for key, val in pairs(data) do
        if type(val) == "table" then
            for _, v in ipairs(val) do
                local matched, rule = _M.check_injection(v, rules)
                if matched then return "Value: " .. tostring(v), rule end
            end
        else
            local matched, rule = _M.check_injection(val, rules)
            if matched then return "Value: " .. tostring(val), rule end
        end
        local matched_key, rule_key = _M.check_injection(key, rules)
        if matched_key then return "Key: " .. tostring(key), rule_key end
    end
    return nil
end

function _M.evaluate()
    local config = _M.load_config()
    if not config.enabled then return nil end

    local rules = config.rules
    local reason, matched_rule

    -- 1. 检查 GET 参数
    reason, matched_rule = check_data(ngx.req.get_uri_args(), rules)
    if reason then
        return { hit = true, reason = reason, attack_type = "ldap_injection", action = ngx.var.waf_mode or config.action or "block" }
    end

    -- 2. 检查 POST 参数
    local method = ngx.var.request_method
    if method == "POST" or method == "PUT" then
        ngx.req.read_body()
        reason, matched_rule = check_data(ngx.req.get_post_args(), rules)
        if reason then
            return { hit = true, reason = reason, attack_type = "ldap_injection", action = ngx.var.waf_mode or config.action or "block" }
        end

        local body = ngx.req.get_body_data()
        if body then
            local matched, rule = _M.check_injection(body, rules)
            if matched then
                return { hit = true, reason = "Body Data", attack_type = "ldap_injection", action = ngx.var.waf_mode or config.action or "block" }
            end
        end
    end

    -- 3. 检查关键 Header (Cookie)
    local cookies = ngx.var.http_cookie
    if cookies then
        local matched, rule = _M.check_injection(cookies, rules)
        if matched then
            return { hit = true, reason = "Cookie", attack_type = "ldap_injection", action = ngx.var.waf_mode or config.action or "block" }
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
    logger.log_attack("ldap_injection", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", "LDAP Protection"))
        ngx.exit(403)
        return false
    end
    return true
end

return _M
