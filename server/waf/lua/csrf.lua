local _M = {}
local json = require "cjson"
local logger = require "logger"

local function extract_domain(url)
    if not url then return nil end
    local m, err = ngx.re.match(url, [[^https?://([^/:]+)]], "jo")
    if m then return m[1] end
    return nil
end

local function is_domain_allowed(domain, allowed_list)
    if not domain then return false end
    for _, allowed in ipairs(allowed_list) do
        if domain == allowed or (string.sub(allowed, 1, 1) == "." and
           (string.sub(domain, -string.len(allowed)) == allowed)) then
            return true
        end
    end
    return false
end

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/csrf/config.json"
    local default_config = {
        enabled = true,
        action = "block",
        protected_methods = {POST=true, PUT=true, DELETE=true, PATCH=true},
        allowed_referers = {},
        allowed_origins = {},
        check_origin = true,
        check_referer = true,
        require_token = false,
        token_header = "x-csrf-token",
        exclude_paths = {}
    }

    local file = io.open(config_path, "r")
    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end

    local methods = {}
    for _, m in ipairs(config.protected_methods or {}) do
        methods[string.upper(m)] = true
    end
    config.protected_methods = methods
    config.token_header = string.lower(config.token_header or "x-csrf-token")
    return config
end

function _M.evaluate()
    local config = _M.load_config()
    if not config.enabled then return nil end

    local method = ngx.var.request_method
    if not config.protected_methods[method] then return nil end

    local uri = ngx.var.uri
    for _, pattern in ipairs(config.exclude_paths) do
        if ngx.re.find(uri, pattern, "jo") then return nil end
    end

    local current_host = ngx.var.host
    local referer = ngx.var.http_referer
    local origin = ngx.var.http_origin

    -- 1. 优先校验 Origin
    if config.check_origin and origin and origin ~= "null" then
        local origin_domain = extract_domain(origin)
        if origin_domain == current_host or is_domain_allowed(origin_domain, config.allowed_origins) then
            goto check_token
        else
            return { hit = true, reason = "Origin Mismatch: " .. tostring(origin_domain), attack_type = "csrf", action = ngx.var.waf_mode or config.action or "block" }
        end
    end

    -- 2. 校验 Referer
    if config.check_referer then
        if not referer then return nil end

        local ref_domain = extract_domain(referer)
        if ref_domain == current_host or is_domain_allowed(ref_domain, config.allowed_referers) then
            return nil
        else
            return { hit = true, reason = "Referer Mismatch: " .. tostring(ref_domain), attack_type = "csrf", action = ngx.var.waf_mode or config.action or "block" }
        end
    end

    ::check_token::
    if config.require_token then
        local headers = ngx.req.get_headers()
        local token_in_header = headers[config.token_header]
        local token_in_cookie = ngx.var["cookie_csrf_token"]

        if not token_in_header or token_in_header ~= token_in_cookie then
            return { hit = true, reason = "Token mismatch or missing", attack_type = "csrf", action = ngx.var.waf_mode or config.action or "block" }
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
    logger.log_attack("csrf", ngx.var.remote_addr, ngx.var.host, ngx.var.request_uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", "CSRF Protection"))
        ngx.exit(403)
        return false
    end
end

return _M
