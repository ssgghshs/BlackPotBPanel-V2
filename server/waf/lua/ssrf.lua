local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/ssrf/config.json"
    local default_config = {
        enabled = true,
        action = "record",
        rules = {
            "\\b(?:gopher|file|dict|expect|tftp|ldap|jar|netdoc)\\s*:",
            "\\b(127\\.0\\.0\\.1|localhost|0\\.0\\.0\\.0)\\b",
            "\\b10\\.(\\d{1,3}\\.){2}\\d{1,3}\\b",
            "\\b172\\.(1[6-9]|2[0-9]|3[0-1])\\.(\\d{1,3}\\.){2}\\d{1,3}\\b",
            "\\b192\\.168\\.(\\d{1,3}\\.){2}\\d{1,3}\\b",
            "\\b169\\.254\\.(\\d{1,3}\\.){2}\\d{1,3}\\b"
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

function _M.check_ssrf(value, rules)
    if not value or type(value) ~= "string" or #value < 5 then return false end

    local unv = ngx.unescape_uri(value)

    if not ngx.re.find(unv, [[^(?:https?|ftp|dict|file|gopher|//)]], "is") then
        return false
    end

    for _, rule in ipairs(rules) do
        if ngx.re.find(unv, rule, "is") then return true end
    end
    return false
end

local function check_table_data(data, rules)
    if not data then return nil end
    for _, val in pairs(data) do
        if type(val) == "string" and _M.check_ssrf(val, rules) then
            return val
        end
    end
    return nil
end

function _M.evaluate()
    if ngx.var.ssrf_enabled == "0" then return nil end
    local config = _M.load_config()
    if not config.enabled then return nil end

    local hit_val = nil

    hit_val = check_table_data(ngx.req.get_uri_args(), config.rules)

    if not hit_val and ngx.var.request_method == "POST" then
        ngx.req.read_body()
        hit_val = check_table_data(ngx.req.get_post_args(), config.rules)
        if not hit_val then
            local body = ngx.req.get_body_data()
            if body and _M.check_ssrf(body, config.rules) then hit_val = "Body URL" end
        end
    end

    if hit_val then
        return {
            hit = true,
            reason = "SSRF detected: " .. hit_val,
            attack_type = "ssrf",
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
    logger.log_attack("ssrf", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Forbidden"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", "SSRF Protection"))
        ngx.exit(403)
    end
end

return _M
