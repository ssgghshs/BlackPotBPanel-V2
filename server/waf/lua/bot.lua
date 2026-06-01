local _M = {}
local json = require "cjson"
local logger = require "logger"

local bot_store = ngx.shared.waf_cc
local SECRET = "WAF_SECURE_TOKEN_2024_PASSIVE"
local TEMPLATE_DIR = "/usr/local/openresty/nginx/waf_html/"


local function get_site_specific_key(client_ip)
    local host = ngx.var.host or "unknown"
    local port = ngx.var.server_port or "80"
    return table.concat({client_ip, host, port}, ":")
end


local function get_cookie_name()
    local port = ngx.var.server_port or "80"
    return "waf_verify_" .. port
end


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


local function generate_signed_token(client_ip, exptime)
    local host = ngx.var.host or ""
    local port = ngx.var.server_port or ""
    local sign = ngx.md5(table.concat({client_ip, host, port, exptime, SECRET}, ":"))
    return string.format("%s.%s", sign, exptime)
end


local function verify_token_sign(token, client_ip)
    if not token then return false end
    local sign, exptime = token:match("^(%w+)%.(%d+)$")
    if not sign or not exptime then return false end
    if os.time() > tonumber(exptime) then return false end

    local host = ngx.var.host or ""
    local port = ngx.var.server_port or ""
    local expected_sign = ngx.md5(table.concat({client_ip, host, port, exptime, SECRET}, ":"))
    return sign == expected_sign
end


local function load_template(filename, token, cookie_name)
    local path = TEMPLATE_DIR .. filename
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*all")
    f:close()
    content = content:gsub("{{token}}", token)
    content = content:gsub("{{cookie_name}}", cookie_name)
    return content
end

function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/bot/config.json"
    local file = io.open(config_path, "r")
    local default = { enabled = true, whitelist_enabled = true, whitelist = {} }
    if not file then return default end
    local content = file:read("*all")
    file:close()
    return json.decode(content) or default
end


function _M.check()
    local bot_enabled = ngx.var.bot_enabled or "0"
    if bot_enabled == "0" then return true end

    local config = _M.load_config()
    if not config.enabled then return true end

    local client_ip = ngx.var.remote_addr
    local user_agent = ngx.var.http_user_agent or ""
    local base_url = get_base_url()
    local verify_mode = ngx.var.bot_verify_enabled or "0"

    local site_key = get_site_specific_key(client_ip)
    local cookie_name = get_cookie_name()

    if config.whitelist_enabled then
        local lower_ua = string.lower(user_agent)
        for _, bot in ipairs(config.whitelist or {}) do
            if string.find(lower_ua, string.lower(bot), 1, true) then
                return true
            end
        end
    end

    -- 验证 Cookie（仅校验 HMAC 签名，不依赖 shared dict）
    -- shared dict 作为性能缓存，即使丢失也不应阻断已验证的请求
    local verify_token = ngx.var["cookie_" .. cookie_name]
    if verify_token then
        if verify_token_sign(verify_token, client_ip) then
            local ok_key = "bot_ok:" .. site_key
            local pass_logged = bot_store:get("log_flag:" .. site_key)
            if not pass_logged then
                logger.log_bot_verify(
                    client_ip, ngx.var.host, ngx.var.request_uri, ngx.var.request_method,
                    verify_mode, "passed", "BOT verification passed (Site-Specific)",
                    { application_url = base_url }
                )
                bot_store:set("log_flag:" .. site_key, 1, 60)
            end
            bot_store:set(ok_key, verify_token, 3600)
            return true
        else
            logger.log_bot_verify(
                client_ip, ngx.var.host, ngx.var.request_uri, ngx.var.request_method,
                verify_mode, "failed", "Invalid token for this specific port",
                { application_url = base_url }
            )
        end
    end

    logger.log_bot_verify(
        client_ip, ngx.var.host, ngx.var.request_uri, ngx.var.request_method,
        verify_mode, "triggered", "Issuing site-specific challenge",
        { application_url = base_url }
    )

    return _M.show_inline_challenge(verify_mode, client_ip, site_key, cookie_name)
end

function _M.show_inline_challenge(mode, client_ip, site_key, cookie_name)
    local exptime = os.time() + 3600
    local token = generate_signed_token(client_ip, exptime)

    local ok_key = "bot_ok:" .. site_key
    if not bot_store:get(ok_key) then
        bot_store:set(ok_key, token, 3600)
    end
    bot_store:delete("log_flag:" .. site_key)

    local html_content = ""

    if mode == "0" then
        html_content = [[
        <html>
        <body>
            <script>
                (function(){
                    document.cookie = "]] .. cookie_name .. [[=]] .. token .. [[; path=/; max-age=3600; SameSite=Lax";
                    location.reload(true);
                })();
            </script>
        </body>
        </html>
        ]]
    elseif mode == "1" then
        html_content = load_template("bot_verify.html", token, cookie_name)
    else
        html_content = load_template("slider_verify.html", token, cookie_name)
    end

    if not html_content then
        ngx.status = 500
        ngx.say("System Error: Component missing.")
        ngx.exit(500)
    end

    ngx.status = ngx.HTTP_OK
    ngx.header.content_type = "text/html; charset=UTF-8"
    ngx.header.cache_control = "no-cache, no-store"
    ngx.say(html_content)
    ngx.exit(ngx.HTTP_OK)
    return false
end

return _M
