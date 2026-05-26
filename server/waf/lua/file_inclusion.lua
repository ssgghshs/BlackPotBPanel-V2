local _M = {}
local json = require "cjson"
local logger = require "logger"

local function check_data(data, rules, callback)
    if not data then return false end
    for k, v in pairs(data) do
        if type(v) == "table" then
            if check_data(v, rules, callback) then return true end
        elseif type(v) == "string" then
            if callback(v, rules, k) then return true end
        end
    end
    return false
end

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/file_inclusion/config.json"
    local file = io.open(config_path, "r")
    local default_config = {
        enabled = true,
        action = "block",
        rules = {},
        exclude_paths = {}
    }

    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end
    return config
end

function _M.check_value(value, rules, source)
    if not value or type(value) ~= "string" or #value < 3 then return false end

    local val = ngx.unescape_uri(value)
    if string.find(val, "%%") then val = ngx.unescape_uri(val) end

    for _, rule in ipairs(rules) do
        local ok, _ = ngx.re.find(val, rule, "isjo")
        if ok then
            _M.last_reason = "Source: " .. (source or "unknown") .. " | Matched: " .. rule
            return true
        end
    end
    return false
end

function _M.evaluate()
    local config = _M.load_config()
    if not config.enabled then return nil end

    local uri = ngx.var.uri

    -- 1. 检查排除路径
    for _, path in ipairs(config.exclude_paths) do
        if ngx.re.find(uri, path, "isjo") then return nil end
    end

    local rules = config.rules

    -- 2. 检查 GET 参数
    local args = ngx.req.get_uri_args()
    if check_data(args, rules, _M.check_value) then
        return { hit = true, reason = _M.last_reason, attack_type = "file_inclusion", action = ngx.var.waf_mode or config.action or "block" }
    end

    -- 3. 检查 POST 请求
    local method = ngx.var.request_method
    if method == "POST" or method == "PUT" or method == "PATCH" then
        ngx.req.read_body()
        local post_args = ngx.req.get_post_args()
        if check_data(post_args, rules, _M.check_value) then
            return { hit = true, reason = _M.last_reason, attack_type = "file_inclusion", action = ngx.var.waf_mode or config.action or "block" }
        end

        local body = ngx.req.get_body_data()
        if body and _M.check_value(body, rules, "POST_BODY") then
            return { hit = true, reason = _M.last_reason, attack_type = "file_inclusion", action = ngx.var.waf_mode or config.action or "block" }
        end
    end

    -- 4. 检查 URI 路径本身 (路径遍历)
    local decoded_uri = ngx.unescape_uri(ngx.var.request_uri)
    local path_rules = { "\\.\\.\\/", "\\.\\.\\\\" }
    for _, p_rule in ipairs(path_rules) do
        if ngx.re.find(decoded_uri, p_rule, "isjo") then
            return { hit = true, reason = "URI: " .. decoded_uri, attack_type = "file_inclusion", action = ngx.var.waf_mode or config.action or "block" }
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
    logger.log_attack("file_inclusion", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", "File Inclusion Protection"))
        ngx.exit(403)
        return false
    end
end

return _M
