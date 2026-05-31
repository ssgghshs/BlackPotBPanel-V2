local _M = {}
local json = require "cjson"


local function load_json(path)
    local file = io.open(path, "r")
    if not file then return nil end
    local content = file:read("*all")
    file:close()
    local ok, data = pcall(json.decode, content)
    if ok and data then return data end
    return nil
end


function _M.load()
    if ngx.ctx.site_config then
        return ngx.ctx.site_config
    end

    local site_name = ngx.var.site_name
    if not site_name or site_name == "" then
        ngx.ctx.site_config = {}
        return {}
    end

    local config_path = "/usr/local/openresty/nginx/sites/config/" .. site_name .. "_config.json"
    local config = load_json(config_path) or {}

    ngx.ctx.site_config = config
    return config
end


function _M.get(key, default_val)
    local config = _M.load()
    local val = config[key]
    if val == nil then return default_val end
    return val
end


function _M.apply_to_ngx_var()
    local config = _M.load()
    if not next(config) then return end

    ngx.var.waf_mode = config.waf_mode or "record"

    local function bool_to_flag(val, default)
        if val == nil then return default and "1" or "0" end
        return val and "1" or "0"
    end

    ngx.var.cc_enabled = bool_to_flag(config.cc_enabled, true)
    ngx.var.bot_enabled = bool_to_flag(config.bot_enabled, true)
    ngx.var.scanner_enabled = bool_to_flag(config.scanner_enabled, true)
    ngx.var.blackwhite_enabled = bool_to_flag(config.blackwhite_enabled, true)
    ngx.var.sql_enabled = bool_to_flag(config.sql_enabled, true)
    ngx.var.xss_enabled = bool_to_flag(config.xss_enabled, true)
    ngx.var.ssrf_enabled = bool_to_flag(config.ssrf_enabled, true)
    ngx.var.cmd_injection_enabled = bool_to_flag(config.cmd_injection_enabled, true)
    ngx.var.csrf_enabled = bool_to_flag(config.csrf_enabled, true)
    ngx.var.file_inclusion_enabled = bool_to_flag(config.file_inclusion_enabled, true)
    ngx.var.file_upload_enabled = bool_to_flag(config.file_upload_enabled, true)
    ngx.var.ldap_injection_enabled = bool_to_flag(config.ldap_injection_enabled, true)

    if config.bot_verify_enabled ~= nil then
        ngx.var.bot_verify_enabled = tostring(config.bot_verify_enabled)
    else
        ngx.var.bot_verify_enabled = "1"
    end
end

return _M
