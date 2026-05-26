local _M = {}
local json = require "cjson"

-- 配置 cjson 库，确保输出空值
json.encode_empty_table_as_object(true)

-- WAF日志文件路径
local waf_log_file = "/usr/local/openresty/nginx/logs/waf.log"
-- BOT日志文件路径
local bot_log_file = "/usr/local/openresty/nginx/logs/bot.log"
-- 黑白名单日志文件路径
local blackwhite_log_file = "/usr/local/openresty/nginx/logs/blackwhite.log"

-- GeoIP数据库路径
local geoip_db_path = "/usr/local/openresty/nginx/data/GeoLite2-City.mmdb"
local geoip_db = nil
local geoip_loaded = false

-- 加载GeoIP数据库（延迟加载）
local function load_geoip()
    if geoip_loaded then
        return geoip_db ~= nil
    end
    
    geoip_loaded = true
    
    ngx.log(ngx.INFO, "Loading GeoIP database...")
    
    local ok, maxminddb = pcall(require, "resty.maxminddb")
    if not ok or not maxminddb then
        ngx.log(ngx.WARN, "maxminddb library not found, GeoIP disabled")
        return false
    end
    
    ngx.log(ngx.INFO, "maxminddb module loaded: " .. tostring(type(maxminddb)))
    
    -- 打印模块的所有方法
    local methods = {}
    for k, v in pairs(maxminddb) do
        table.insert(methods, k .. "=" .. tostring(type(v)))
    end
    ngx.log(ngx.INFO, "maxminddb methods: " .. table.concat(methods, ", "))
    
    -- 尝试不同的初始化方式
    local db, err
    
    -- 方式1: 使用 init 函数
    if maxminddb.init then
        ngx.log(ngx.INFO, "Trying maxminddb.init...")
        local init_ok, init_err = pcall(function()
            return maxminddb.init(geoip_db_path)
        end)
        ngx.log(ngx.INFO, "maxminddb.init result: ok=" .. tostring(init_ok) .. ", err=" .. tostring(init_err))
        if init_ok then
            geoip_db = maxminddb
            ngx.log(ngx.INFO, "GeoIP database loaded successfully (init)")
            return true
        end
    end
    
    -- 方式2: 使用 new 函数
    if maxminddb.new then
        ngx.log(ngx.INFO, "Trying maxminddb.new...")
        db, err = maxminddb.new(geoip_db_path)
        ngx.log(ngx.INFO, "maxminddb.new result: db=" .. tostring(db) .. ", err=" .. tostring(err))
    elseif type(maxminddb) == "table" and maxminddb.open then
        -- 方式3: 使用 open 函数
        ngx.log(ngx.INFO, "Trying maxminddb.open...")
        db, err = maxminddb.open(geoip_db_path)
        ngx.log(ngx.INFO, "maxminddb.open result: db=" .. tostring(db) .. ", err=" .. tostring(err))
    else
        -- 方式4: 直接使用模块
        ngx.log(ngx.INFO, "Using maxmindb module directly")
        db = maxminddb
    end
    
    if not db then
        ngx.log(ngx.WARN, "Failed to open GeoIP database: " .. (err or "unknown error"))
        return false
    end
    
    geoip_db = db
    ngx.log(ngx.INFO, "GeoIP database loaded successfully")
    return true
end

-- 查询IP地理位置
function _M.get_geoip(ip)
    -- 延迟加载GeoIP数据库
    if not geoip_loaded then
        load_geoip()
    end
    
    if not geoip_db then
        ngx.log(ngx.WARN, "GeoIP database not loaded")
        return {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = 0,
            longitude = 0
        }
    end
    
    ngx.log(ngx.INFO, "Looking up IP: " .. ip .. " (type: " .. type(ip) .. ")")
    
    local ok, res = pcall(function()
        -- 尝试不同的查询方式
        if geoip_db.lookup then
            if type(geoip_db.lookup) == "function" then
                -- 方法1: 只传递 IP 字符串
                ngx.log(ngx.INFO, "Using geoip_db.lookup(ip)")
                return geoip_db.lookup(ip)
            else
                -- 方法2: 模块函数
                ngx.log(ngx.INFO, "Using geoip_db.lookup(ip)")
                return geoip_db.lookup(ip)
            end
        elseif geoip_db.query then
            -- 方法3: query 函数
            ngx.log(ngx.INFO, "Using geoip_db.query(ip)")
            return geoip_db.query(ip)
        elseif geoip_db.search then
            -- 方法4: search 函数
            ngx.log(ngx.INFO, "Using geoip_db.search(ip)")
            return geoip_db.search(ip)
        else
            -- 方法5: 直接使用模块的查询函数
            ngx.log(ngx.INFO, "Using default lookup")
            return geoip_db.lookup(ip)
        end
    end)
    
    if not ok then
        ngx.log(ngx.WARN, "GeoIP lookup failed: " .. tostring(res))
        return {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = 0,
            longitude = 0
        }
    end
    
    if not res then
        ngx.log(ngx.INFO, "GeoIP result is nil (IP not found or private IP)")
        return {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = 0,
            longitude = 0
        }
    end
    
    ngx.log(ngx.INFO, "GeoIP result: " .. tostring(res))
    
    local geo_info = {}
    
    -- 提取国家信息
    if res.country and res.country.names then
        geo_info.country = res.country.names.en or res.country.names.zh or "Unknown"
        geo_info.country_code = res.country.iso_code or "Unknown"
    else
        geo_info.country = "Unknown"
        geo_info.country_code = "Unknown"
    end
    
    -- 提取城市信息
    if res.city and res.city.names then
        geo_info.city = res.city.names.en or res.city.names.zh or "Unknown"
    else
        geo_info.city = "Unknown"
    end
    
    -- 提取地区信息
    if res.subdivisions and res.subdivisions[1] and res.subdivisions[1].names then
        geo_info.region = res.subdivisions[1].names.en or res.subdivisions[1].names.zh or "Unknown"
    else
        geo_info.region = "Unknown"
    end
    
    -- 提取经纬度
    if res.location then
        geo_info.latitude = res.location.latitude or 0
        geo_info.longitude = res.location.longitude or 0
    else
        geo_info.latitude = 0
        geo_info.longitude = 0
    end
    
    -- 构建完整地址
    local location_parts = {}
    if geo_info.country then
        table.insert(location_parts, geo_info.country)
    end
    if geo_info.region and geo_info.region ~= geo_info.country then
        table.insert(location_parts, geo_info.region)
    end
    if geo_info.city and geo_info.city ~= geo_info.region then
        table.insert(location_parts, geo_info.city)
    end
    
    geo_info.location = table.concat(location_parts, ", ")
    
    return geo_info
end

-- JSON 字符串转义（符合 RFC 8259）
local function json_escape(s)
    s = string.gsub(s, "\\", "\\\\")
    s = string.gsub(s, "\"", "\\\"")
    s = string.gsub(s, "\n", "\\n")
    s = string.gsub(s, "\r", "\\r")
    s = string.gsub(s, "\t", "\\t")
    s = string.gsub(s, "\b", "\\b")
    s = string.gsub(s, "\f", "\\f")
    return s
end

-- 构建有序的JSON字符串
local function build_ordered_json(data, order)
    local parts = {}
    
    -- 按指定顺序添加字段
    for _, key in ipairs(order) do
        if data[key] ~= nil then
            local value
            if type(data[key]) == "table" then
                value = json.encode(data[key])
            elseif type(data[key]) == "string" then
                value = "\"" .. json_escape(data[key]) .. "\""
            else
                value = tostring(data[key])
            end
            table.insert(parts, "\"" .. key .. "\": " .. value)
        end
    end
    
    -- 添加剩余的字段（按字母顺序）
    local remaining = {}
    for key in pairs(data) do
        local found = false
        for _, ordered_key in ipairs(order) do
            if key == ordered_key then
                found = true
                break
            end
        end
        if not found then
            table.insert(remaining, key)
        end
    end
    table.sort(remaining)
    
    for _, key in ipairs(remaining) do
        if data[key] ~= nil then
            local value
            if type(data[key]) == "table" then
                value = json.encode(data[key])
            elseif type(data[key]) == "string" then
                value = "\"" .. json_escape(data[key]) .. "\""
            else
                value = tostring(data[key])
            end
            table.insert(parts, "\"" .. key .. "\": " .. value)
        end
    end
    
    return "{" .. table.concat(parts, ", ") .. "}"
end

-- 写入WAF日志
function _M.log(data)
    -- 添加时间戳
    data.timestamp = ngx.now()
    data.datetime = os.date("%Y-%m-%d %H:%M:%S", ngx.time())
    
    -- 强制添加geoip字段
    data.geoip = data.geoip or {}
    if data.client_ip then
        local geo_info = _M.get_geoip(data.client_ip)
        if geo_info then
            data.geoip = geo_info
        end
    else
        -- 即使没有client_ip，也要添加geoip字段
        data.geoip = {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = "",
            longitude = ""
        }
    end
    
    -- 定义统一的字段顺序
    local field_order = {
        "application_url",
        "request_method",
        "action",
        "client_ip",
        "user_agent",
        "request_uri",     
        "verify_mode",
        "verification_status",
        "timestamp",
        "datetime",
        "geoip"
    }
    
    -- 构建有序的JSON字符串
    local log_line = build_ordered_json(data, field_order)
    
    -- 写入日志文件
    local file, err = io.open(waf_log_file, "a")
    if not file then
        ngx.log(ngx.ERR, "Failed to open WAF log file: " .. (err or "unknown error"))
        ngx.log(ngx.WARN, "[WAF] " .. log_line)
        return false
    end
    
    file:write(log_line .. "\n")
    file:close()
    
    ngx.log(ngx.INFO, "[WAF] " .. log_line)
    
    return true
end

-- 记录攻击日志（统一格式）
function _M.log_attack(attack_type, client_ip, host, request_uri, request_method, reason, extra)
    -- 构建完整的应用 URL
    local scheme = ngx.var.scheme or "http"
    local server_port = ngx.var.server_port or "80"
    local application_url = scheme .. "://" .. host
    if (scheme == "http" and server_port ~= "80") or (scheme == "https" and server_port ~= "443") then
        application_url = application_url .. ":" .. server_port
    end
    
    local log_data = {
        attack_type = attack_type,
        reason = reason,
        client_ip = client_ip,
        user_agent = ngx.var.http_user_agent or "",
        request_uri = request_uri,
        request_method = request_method,
        application = application_url,
        action = extra and extra.action or "blocked"
    }
    
    -- 合并额外字段（排除已存在的字段）
    if extra then
        for k, v in pairs(extra) do
            if k ~= "action" and k ~= "user_agent" then
                log_data[k] = v
            end
        end
    end
    
    -- 如果是bot攻击，使用专门的日志文件
    if attack_type == "bot" then
        return _M.log_bot(log_data)
    end
    
    return _M.log(log_data)
end

-- 记录BOT验证日志（专门格式）
function _M.log_bot_verify(client_ip, host, request_uri, request_method, verify_mode, status, message, extra)
    local log_data = {
        client_ip = client_ip,
        user_agent = ngx.var.http_user_agent or "",
        request_uri = request_uri,
        request_method = request_method,
        verify_mode = verify_mode,  -- 0=无感验证, 1=5秒页面验证, 2=滑动验证
        verification_status = status,  -- "triggered", "passed", "failed"
        action = status == "passed" and "verified" or "challenge"
    }
    
    -- 添加应用URL字段
    if extra and extra.application_url then
        log_data.application_url = extra.application_url
    else
        -- 尝试构建应用URL
        local scheme = ngx.var.scheme or "http"
        local server_port = ngx.var.server_port or "80"
        local full_url = scheme .. "://" .. host
        if (scheme == "http" and server_port ~= "80") or (scheme == "https" and server_port ~= "443") then
            full_url = full_url .. ":" .. server_port
        end
        log_data.application_url = full_url
    end
    
    -- 合并额外字段
    if extra then
        for k, v in pairs(extra) do
            if k ~= "action" and k ~= "user_agent" then
                log_data[k] = v
            end
        end
    end
    
    return _M.log_bot(log_data)
end

-- 写入BOT日志
function _M.log_bot(data)
    -- 添加时间戳
    data.timestamp = ngx.now()
    data.datetime = os.date("%Y-%m-%d %H:%M:%S", ngx.time())
    
    -- 强制添加geoip字段
    data.geoip = data.geoip or {}
    if data.client_ip then
        local geo_info = _M.get_geoip(data.client_ip)
        if geo_info then
            data.geoip = geo_info
        end
    else
        -- 即使没有client_ip，也要添加geoip字段
        data.geoip = {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = 0,
            longitude = 0
        }
    end
    
    -- 定义统一的字段顺序
    local field_order = {
        "action",
        "client_ip",
        "user_agent",
        "request_uri",
        "request_method",
        "application_url",
        "verify_mode",
        "verification_status",
        "timestamp",
        "datetime",
        "geoip"
    }
    
    -- 构建有序的JSON字符串
    local log_line = build_ordered_json(data, field_order)
    
    -- 写入日志文件
    local file, err = io.open(bot_log_file, "a")
    if not file then
        ngx.log(ngx.ERR, "Failed to open BOT log file: " .. (err or "unknown error"))
        ngx.log(ngx.WARN, "[BOT] " .. log_line)
        return false
    end
    
    file:write(log_line .. "\n")
    file:close()
    
    ngx.log(ngx.INFO, "[BOT] " .. log_line)
    
    return true
end

-- 记录黑白名单日志（专门格式）
function _M.log_blackwhite(client_ip, host, request_uri, request_method, action, reason, extra)
    -- 构建完整的应用 URL
    local scheme = ngx.var.scheme or "http"
    local server_port = ngx.var.server_port or "80"
    local application_url = scheme .. "://" .. host
    if (scheme == "http" and server_port ~= "80") or (scheme == "https" and server_port ~= "443") then
        application_url = application_url .. ":" .. server_port
    end
    
    local log_data = {
        client_ip = client_ip,
        user_agent = ngx.var.http_user_agent or "",
        request_uri = request_uri,
        request_method = request_method,
        application_url = application_url,
        action = action,  -- "allow" or "block"
        reason = reason
    }
    
    -- 合并额外字段
    if extra then
        for k, v in pairs(extra) do
            if k ~= "action" and k ~= "user_agent" then
                log_data[k] = v
            end
        end
    end
    
    return _M.log_blackwhite_log(log_data)
end

-- 写入黑白名单日志
function _M.log_blackwhite_log(data)
    -- 添加时间戳
    data.timestamp = ngx.now()
    data.datetime = os.date("%Y-%m-%d %H:%M:%S", ngx.time())
    
    -- 强制添加geoip字段
    data.geoip = data.geoip or {}
    if data.client_ip then
        local geo_info = _M.get_geoip(data.client_ip)
        if geo_info then
            data.geoip = geo_info
        end
    else
        -- 即使没有client_ip，也要添加geoip字段
        data.geoip = {
            country_code = "Unknown",
            city = "Unknown",
            country = "Unknown",
            location = "Unknown, Unknown",
            latitude = 0,
            longitude = 0
        }
    end
    
    -- 定义统一的字段顺序
    local field_order = {
        "action",
        "client_ip",
        "user_agent",
        "request_uri",
        "request_method",
        "application_url",
        "reason",
        "timestamp",
        "datetime",
        "geoip"
    }
    
    -- 构建有序的JSON字符串
    local log_line = build_ordered_json(data, field_order)
    
    -- 写入日志文件
    local file, err = io.open(blackwhite_log_file, "a")
    if not file then
        ngx.log(ngx.ERR, "Failed to open blackwhite log file: " .. (err or "unknown error"))
        ngx.log(ngx.WARN, "[BLACKWHITE] " .. log_line)
        return false
    end
    
    file:write(log_line .. "\n")
    file:close()
    
    ngx.log(ngx.INFO, "[BLACKWHITE] " .. log_line)
    
    return true
end

return _M
