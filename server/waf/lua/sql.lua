local _M = {}
local json = require "cjson"
local logger = require "logger"

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/sql/config.json"
    local default_config = {
        enabled = true,
        action = "record",
        -- 核心规则建议在 JSON 中更新，此处为兜底
        rules = {}
    }
    local file = io.open(config_path, "r")
    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end
    return config
end

function _M.check_sql_injection(value, rules)
    if not value or type(value) ~= "string" or #value < 4 then return false end
    local unv = ngx.unescape_uri(value)
    for _, rule in ipairs(rules) do
        local ok, _ = ngx.re.find(unv, rule, "isjo")
        if ok then return true, rule end
    end
    return false
end

-- 仅检查 Value，忽略 Key，减少 50% 误报
local function check_table_data(data, rules)
    if not data then return nil end
    for _, val in pairs(data) do
        if type(val) == "string" then
            local matched, rule = _M.check_sql_injection(val, rules)
            if matched then return val, rule end
        elseif type(val) == "table" then
            for _, v in ipairs(val) do
                if type(v) == "string" then
                    local matched, rule = _M.check_sql_injection(v, rules)
                    if matched then return v, rule end
                end
            end
        end
    end
    return nil
end

function _M.evaluate()
    if ngx.var.sql_enabled == "0" then return nil end
    local config = _M.load_config()
    if not config.enabled then return nil end

    local hit_val = nil
    local hit_rule = nil

    -- 1. 检查 GET/POST
    hit_val, hit_rule = check_table_data(ngx.req.get_uri_args(), config.rules)
    if not hit_val and ngx.var.request_method == "POST" then
        ngx.req.read_body()
        hit_val, hit_rule = check_table_data(ngx.req.get_post_args(), config.rules)
        if not hit_val then
            local body = ngx.req.get_body_data()
            if body then
                local matched, rule = _M.check_sql_injection(body, config.rules)
                if matched then hit_val, hit_rule = "JSON Body", rule end
            end
        end
    end

    -- 2. 检查 Cookie 值
    if not hit_val then
        local cookies = ngx.req.get_headers()["Cookie"]
        if cookies then
            local matched, rule = _M.check_sql_injection(cookies, config.rules)
            if matched then hit_val, hit_rule = "Cookie Content", rule end
        end
    end

    if hit_val then
        return {
            hit = true,
            reason = "SQL Injection matched rule [" .. hit_rule .. "] in: " .. hit_val,
            attack_type = "sql",
            action = ngx.var.waf_mode or config.action or "record",
            hit_rule = hit_rule
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
    logger.log_attack("sql", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", "SQL Injection Protection"))
        ngx.exit(403)
    end
end

return _M
