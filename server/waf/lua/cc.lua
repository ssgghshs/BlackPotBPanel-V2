local _M = {}
local cc_store = ngx.shared.waf_cc
local json = require "cjson"
local logger = require "logger"



function _M.check()
    -- 检查站点是否启用CC防护 (默认为开启)
    local cc_enabled = ngx.var.cc_enabled
    if cc_enabled == nil then
        cc_enabled = "1"  -- 默认开启
    end
    
    if cc_enabled == "0" then
        ngx.log(ngx.INFO, "CC protection disabled for site: " .. ngx.var.host)
        return true  -- 跳过检查
    end
    
    local config = _M.load_config()
    
    if not config.enabled then
        return true
    end
    
    local client_ip = ngx.var.remote_addr
    local now = ngx.time()
    local key = "cc:" .. client_ip
    
    -- 获取当前请求计数
    local count, err = cc_store:get(key)
    if not count then
        count = 0
    end
    
    -- 检查是否超过限制
    if count >= config.max_requests then
        -- 记录拦截
        ngx.var.waf_type = "cc"
        ngx.var.waf_action = "block"
        
        -- 优先使用统一防护模式，其次使用模块配置
        local action = ngx.var.waf_mode or config.action or "record"
        
        if action == "block" then
            -- 写入WAF日志（统一格式）
            logger.log_attack(
                "cc",
                client_ip,
                ngx.var.host,
                ngx.var.request_uri,
                ngx.var.request_method,
                "Request frequency exceeded limit",
                {
                    action = "blocked",
                    user_agent = ngx.var.http_user_agent,
                    count = count,
                    limit = config.max_requests,
                    time_window = config.time_window
                }
            )
            
            -- 读取自定义拦截页面
            local html_file = io.open("/usr/local/openresty/nginx/waf_html/waf_blocked.html", "r")
            local html_content
            
            if html_file then
                html_content = html_file:read("*all")
                html_file:close()
                -- 替换拦截原因占位符
                html_content = string.gsub(html_content, "{{reason}}", "Request frequency exceeded limit")
                html_content = string.gsub(html_content, "{{attack_type}}", "CC Attack Protection")
            else
                -- 如果文件不存在，使用默认页面
                html_content = [[
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>403 Forbidden</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }
        .container {
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #e03131; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>403 Forbidden</h1>
        <p>You have been blocked due to excessive requests.</p>
    </div>
</body>
</html>
            ]]
            end
            
            -- 返回 403 错误
            ngx.status = ngx.HTTP_FORBIDDEN
            ngx.header.content_type = "text/html"
            ngx.say(html_content)
            ngx.exit(ngx.HTTP_FORBIDDEN)
        elseif action == "record" then
            -- 记录模式：只记录日志，不拦截
            logger.log_attack(
                "cc",
                client_ip,
                ngx.var.host,
                ngx.var.request_uri,
                ngx.var.request_method,
                "Request frequency exceeded limit",
                {
                    user_agent = ngx.var.http_user_agent,
                    action = "record",
                    count = count,
                    limit = config.max_requests,
                    time_window = config.time_window
                }
            )
            -- 允许请求继续
            return true
        end
        
        return false
    end
    
    -- 更新计数
    count = count + 1
    cc_store:set(key, count, config.time_window)
    
    return true
end


function _M.load_config()
    local config_path = "/usr/local/openresty/nginx/rules/cc/config.json"
    local file = io.open(config_path, "r")
    if not file then
        return {
            enabled = true,
            action = "record",  -- 默认动作: block 或 record
            max_requests = 100,
            time_window = 60,
            block_duration = 300
        }
    end
    
    local content = file:read("*all")
    file:close()
    
    local config, err = json.decode(content)
    if not config then
        return {
            enabled = true,
            action = "record",  -- 默认动作: block 或 record
            max_requests = 100,
            time_window = 60,
            block_duration = 300
        }
    end
    
    -- 确保action存在
    if not config.action then
        config.action = "block"
    end
    
    return config
end

return _M
