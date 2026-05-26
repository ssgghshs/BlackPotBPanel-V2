local _M = {}
local json = require "cjson"
local logger = require "logger"
local bit = require "bit"

-- 加载配置文件
function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/blackwhite/config.json"
    local file = io.open(config_path, "r")
    if not file then
        return {
            enabled = true,
            white_list = {},
            black_list = {}
        }
    end
    
    local content = file:read("*all")
    file:close()
    
    local config, err = json.decode(content)
    if not config then
        ngx.log(ngx.ERR, "Failed to parse blackwhite config: " .. (err or "unknown error"))
        return {
            enabled = true,
            white_list = {},
            black_list = {}
        }
    end
    
    -- 确保基础配置项存在
    if config.enabled == nil then config.enabled = true end
    if not config.white_list then config.white_list = {} end
    if not config.black_list then config.black_list = {} end
    
    return config
end

-- 核心检查逻辑
function _M.check()
    -- 1. 检查站点变量开关 (优先于全局配置)
    local blackwhite_enabled = ngx.var.blackwhite_enabled
    if blackwhite_enabled == "0" then
        return true  -- 显式关闭则跳过
    end
    
    local config = _M.load_config()
    if not config.enabled then
        return true -- 全局配置关闭则跳过
    end
    
    local client_ip = ngx.var.remote_addr
    
    -- 2. 检查白名单
    local in_white, white_group = _M.is_in_list(client_ip, config.white_list)
    if in_white then
        local group_info = white_group and (" (Group: " .. white_group .. ")") or ""
        ngx.log(ngx.INFO, "IP " .. client_ip .. " allowed by white list" .. group_info)
        
        logger.log_blackwhite(
            client_ip,
            ngx.var.host,
            ngx.var.request_uri,
            ngx.var.request_method,
            "allow",
            "IP in white list" .. group_info,
            {
                user_agent = ngx.var.http_user_agent,
                group = white_group
            }
        )
        return true
    end
    
    -- 3. 检查黑名单
    local in_black, black_group = _M.is_in_list(client_ip, config.black_list)
    if in_black then
        local group_info = black_group and (" (Group: " .. black_group .. ")") or ""
        ngx.log(ngx.INFO, "IP " .. client_ip .. " blocked by black list" .. group_info)
        
        -- 设置 WAF 变量供日志模块使用
        ngx.var.waf_type = "blacklist"
        ngx.var.waf_action = "block"
        
        logger.log_blackwhite(
            client_ip,
            ngx.var.host,
            ngx.var.request_uri,
            ngx.var.request_method,
            "block",
            "IP in black list" .. group_info,
            {
                user_agent = ngx.var.http_user_agent,
                group = black_group
            }
        )
        
        -- 返回拦截页面
        _M.show_block_page(group_info)
        return false
    end
    
    return true
end

-- 判断 IP 是否在列表（组）中
function _M.is_in_list(ip, list)
    if not list or #list == 0 then
        return false, nil
    end
    
    for _, group in ipairs(list) do
        -- A. 处理新的分组格式 { "name": "xxx", "enabled": true, "ips": [...] }
        if type(group) == "table" and group.ips then
            
            -- 【新增判断】：只有当 enabled 不为 false 时才检查该组内容
            if group.enabled ~= false then 
                for _, entry in ipairs(group.ips) do
                    if entry == ip then
                        return true, group.name
                    end
                    
                    -- 检查 CIDR 格式
                    if string.find(entry, "/") then
                        if _M.is_ip_in_cidr(ip, entry) then
                            return true, group.name
                        end
                    end
                end
            end
            
        -- B. 处理旧的简单字符串格式 "1.1.1.1" (向后兼容)
        elseif type(group) == "string" then
            if group == ip then
                return true, "default"
            end
            if string.find(group, "/") then
                if _M.is_ip_in_cidr(ip, group) then
                    return true, "default"
                end
            end
        end
    end
    
    return false, nil
end

-- CIDR 匹配算法
function _M.is_ip_in_cidr(ip, cidr)
    local ip_parts = {}
    for part in string.gmatch(ip, "(%d+)") do
        table.insert(ip_parts, tonumber(part))
    end
    
    local cidr_ip, cidr_prefix = string.match(cidr, "([^/]+)/(%d+)")
    if not cidr_ip or not cidr_prefix then return false end
    
    local cidr_parts = {}
    for part in string.gmatch(cidr_ip, "(%d+)") do
        table.insert(cidr_parts, tonumber(part))
    end
    
    local prefix = tonumber(cidr_prefix)
    -- 计算掩码
    local mask = bit.lshift(bit.bnot(0), 32 - prefix)
    
    -- 将 IP 转换为 32 位整数
    local function ip_to_int(parts)
        return bit.bor(
            bit.lshift(parts[1], 24),
            bit.lshift(parts[2], 16),
            bit.lshift(parts[3], 8),
            parts[4]
        )
    end
    
    local ip_num = ip_to_int(ip_parts)
    local cidr_num = ip_to_int(cidr_parts)
    
    return bit.band(ip_num, mask) == bit.band(cidr_num, mask)
end

-- 显示拦截页面
function _M.show_block_page(group_name)
    local html_path = "/usr/local/openresty/nginx/waf_html/waf_blocked.html"
    local f = io.open(html_path, "r")
    local content
    
    if f then
        content = f:read("*all")
        f:close()
        content = string.gsub(content, "{{reason}}", "Your IP is in our blacklist" .. (group_name or ""))
        content = string.gsub(content, "{{attack_type}}", "Blacklist Protection")
    else
        -- 默认兜底页面
        content = "<html><body style='text-align:center;padding-top:100px;font-family:sans-serif;'>" ..
                  "<h1 style='color:red;'>403 Forbidden</h1>" ..
                  "<p>Access Denied: Your IP address is blacklisted.</p>" ..
                  "</body></html>"
    end
    
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header.content_type = "text/html; charset=UTF-8"
    ngx.say(content)
    ngx.exit(ngx.HTTP_FORBIDDEN)
end

return _M