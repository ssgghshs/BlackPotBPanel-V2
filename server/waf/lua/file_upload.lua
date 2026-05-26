local _M = {}
local json = require "cjson"
local logger = require "logger"

local function to_set(arr)
    local s = {}
    if arr then
        for _, v in ipairs(arr) do s[string.lower(v)] = true end
    end
    return s
end

local function get_ext(filename)
    if not filename then return nil end
    local ext = string.match(filename, "%.([^%.]+)$")
    return ext and ("." .. string.lower(ext)) or ""
end

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/file_upload/config.json"
    local file = io.open(config_path, "r")

    local default_config = {
        enabled = true,
        action = "block",
        max_file_size = 10485760,
        check_content = true,
        allowed_extensions = {".jpg", ".png", ".gif", ".pdf"},
        forbidden_content = {"<?php", "eval(", "system("},
        exclude_paths = {}
    }

    if not file then return default_config end
    local content = file:read("*all")
    file:close()
    local status, config = pcall(json.decode, content)
    if not status or not config then return default_config end

    config.allowed_ext_set = to_set(config.allowed_extensions)
    config.forbidden_ext_set = to_set(config.forbidden_extensions)
    config.allowed_type_set = to_set(config.allowed_types)
    config.forbidden_type_set = to_set(config.forbidden_types)
    return config
end

function _M.evaluate()
    local config = _M.load_config()
    if not config.enabled then return nil end

    local uri = ngx.var.uri
    if config.exclude_paths then
        for _, path in ipairs(config.exclude_paths) do
            if string.sub(uri, 1, #path) == path then return nil end
        end
    end

    if ngx.var.request_method ~= "POST" then return nil end

    local ct = ngx.var.content_type
    if not ct or not string.find(ct, "multipart/form-data", 1, true) then
        return nil
    end

    ngx.req.read_body()
    local body_data = ngx.req.get_body_data()

    if not body_data then
        local body_file = ngx.req.get_body_file()
        if body_file then
            local f = io.open(body_file, "rb")
            if f then
                body_data = f:read("*all")
                f:close()
            end
        end
    end

    if not body_data then return nil end

    if #body_data > config.max_file_size then
        return { hit = true, reason = "Total payload size exceeds limit", attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
    end

    local boundary = string.match(ct, "boundary=(%S+)")
    if not boundary then return nil end

    if config.check_content then
        for _, pat in ipairs(config.forbidden_content) do
            if string.find(body_data, pat, 1, true) then
                return { hit = true, reason = "Malicious content detected: " .. pat, attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
            end
        end
    end

    local it, err = ngx.re.gmatch(body_data, [[Content-Disposition:.*filename="([^"]+)".*?Content-Type: (%S+)]], "is")
    if not it then return nil end

    while true do
        local res, err = it()
        if not res then break end

        local filename = res[1]
        local file_type = string.lower(res[2] or "")
        local ext = get_ext(filename)

        if config.forbidden_ext_set[ext] then
            return { hit = true, reason = "Forbidden extension: " .. ext, attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
        end
        if next(config.allowed_ext_set) and not config.allowed_ext_set[ext] then
            return { hit = true, reason = "Extension not allowed: " .. ext, attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
        end
        if config.forbidden_type_set[file_type] then
            return { hit = true, reason = "Forbidden MIME type: " .. file_type, attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
        end
        if next(config.allowed_type_set) and not config.allowed_type_set[file_type] then
            return { hit = true, reason = "MIME type not allowed: " .. file_type, attack_type = "file_upload", action = ngx.var.waf_mode or config.action or "block" }
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
    logger.log_attack("file_upload", ngx.var.remote_addr, ngx.var.host, ngx.var.uri,
        ngx.var.request_method, reason, { action = action })

    if waf_mode == "block" then
        ngx.status = 403
        ngx.header.content_type = "text/html; charset=UTF-8"
        local f = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
        local content = f and f:read("*all") or "Blocked by WAF"
        if f then f:close() end
        ngx.say(content:gsub("{{reason}}", reason):gsub("{{attack_type}}", "File Upload"))
        ngx.exit(403)
        return false
    end
    return true
end

return _M
