# 1.扫描器与爬虫识别防护测试用例

## 测试URL格式：
# http://your-site.com/page

## 1. 扫描器User-Agent测试
# 测试使用Nmap扫描器的User-Agent
curl -X GET http://your-site.com/ \
  -H "User-Agent: Nmap Scripting Engine"

# 测试使用SQLmap扫描器的User-Agent
curl -X GET http://your-site.com/ \
  -H "User-Agent: sqlmap/1.7.9#stable (http://sqlmap.org)"

# 测试使用Burp Suite的User-Agent
curl -X GET http://your-site.com/ \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 BurpSuite"

## 2. 爬虫User-Agent测试
# 测试使用Googlebot的User-Agent（应该允许）
curl -X GET http://your-site.com/ \
  -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

# 测试使用Bingbot的User-Agent（应该允许）
curl -X GET http://your-site.com/ \
  -H "User-Agent: Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"

# 测试使用AhrefsBot的User-Agent（应该拦截）
curl -X GET http://your-site.com/ \
  -H "User-Agent: Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)"

## 3. 扫描器路径测试
# 测试访问.git目录
curl -X GET http://your-site.com/.git/

# 测试访问备份文件
curl -X GET http://your-site.com/backup.zip

# 测试访问配置文件
curl -X GET http://your-site.com/config.php

# 测试访问管理后台
curl -X GET http://your-site.com/admin/

# 测试访问phpMyAdmin
curl -X GET http://your-site.com/phpmyadmin/

## 4. 扫描器请求头测试
# 测试使用X-Forwarded-For: 127.0.0.1
curl -X GET http://your-site.com/ \
  -H "X-Forwarded-For: 127.0.0.1"

# 测试使用X-Originating-IP: 127.0.0.1
curl -X GET http://your-site.com/ \
  -H "X-Originating-IP: 127.0.0.1"

## 5. 空User-Agent测试
# 测试使用空User-Agent
curl -X GET http://your-site.com/ \
  -H "User-Agent:"

## 6. 常见工具User-Agent测试
# 测试使用curl的User-Agent
curl -X GET http://your-site.com/

# 测试使用wget的User-Agent
wget -qO- http://your-site.com/

## 7. 排除路径测试
# 测试访问排除路径（如/api/）
curl -X GET http://your-site.com/api/ \
  -H "User-Agent: Nmap Scripting Engine"

## 8. 正常浏览器测试
# 测试使用正常浏览器的User-Agent
curl -X GET http://your-site.com/ \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

## 预期结果：
# 1, 2（除Googlebot和Bingbot外）, 3, 4, 5, 6的测试用例应该被扫描器与爬虫识别防护拦截
# 2（Googlebot和Bingbot）, 7, 8的测试用例应该正常通过

## 配置建议：
# 1. 生产环境建议保持默认配置
# 2. 根据业务需求调整allowed_crawlers，添加需要允许的爬虫
# 3. 调整exclude_paths，添加需要允许的路径
# 4. 定期更新scanner_user_agents和scanner_paths，以应对新的扫描器
# 5. 对于API接口，建议添加到exclude_paths，并通过API密钥或其他方式进行保护


# 7.LDAP注入防护测试用例

## 测试URL格式：
# http://your-site.com/page?param=value

## 1. 基本LDAP注入测试
# 测试基本的LDAP注入字符
http://your-site.com/login?username=admin)(&password=password
http://your-site.com/login?username=admin*&password=password
http://your-site.com/login?username=admin%28%29&password=password

## 2. 高级LDAP注入测试
# 测试常见的LDAP注入语句
http://your-site.com/search?filter=(objectClass=*)
http://your-site.com/search?filter=uid=admin
http://your-site.com/search?filter=cn=admin

## 3. 特殊字符编码测试
# 测试URL编码的LDAP注入字符
http://your-site.com/login?username=admin%29%28&password=password
http://your-site.com/login?username=admin%2a&password=password
http://your-site.com/login?username=admin%7c%7c%2a&password=password

## 4. 组合测试
# 测试多种LDAP注入技术的组合
http://your-site.com/login?username=admin)(objectClass=*))(&password=password
http://your-site.com/search?filter=(uid=admin)(objectClass=*)

## 5. POST请求测试
# 测试POST请求中的LDAP注入
# POST数据：username=admin)(&password=password
# POST数据：filter=(objectClass=*)

## 6. 边界测试
# 测试边界情况
http://your-site.com/login?username=admin&password=password
http://your-site.com/search?filter=normal

## 预期结果：
# 1-4的测试用例应该被LDAP注入防护拦截
# 5的测试用例应该被LDAP注入防护拦截
# 6的测试用例应该正常通过



# 9.CSRF防护测试用例

## 测试URL格式：
# http://your-site.com/page

## 1. 基本CSRF攻击测试（无Referer）
# 测试没有Referer头的POST请求
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}'

## 2. 非法Referer测试
# 测试来自非法域名的Referer
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "Referer: https://evil.com" \
  -d '{"name":"test"}'

## 3. 非法Origin测试
# 测试来自非法域名的Origin
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "Origin: https://evil.com" \
  -d '{"name":"test"}'

## 4. 合法Referer测试
# 测试来自合法域名的Referer（需要在配置中添加允许的域名）
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "Referer: https://your-site.com" \
  -d '{"name":"test"}'

## 5. 合法Origin测试
# 测试来自合法域名的Origin（需要在配置中添加允许的域名）
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "Origin: https://your-site.com" \
  -d '{"name":"test"}'

## 6. 排除路径测试
# 测试排除路径（如登录接口）
curl -X POST http://your-site.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

## 7. GET请求测试
# 测试GET请求（不应该触发CSRF防护）
curl http://your-site.com/api/users

## 8. CSRF Token测试（如果启用）
# 测试带有CSRF Token的请求
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: valid-token-from-session" \
  -H "Referer: https://your-site.com" \
  -d '{"name":"test"}'

## 9. 无效CSRF Token测试
# 测试带有无效CSRF Token的请求
curl -X POST http://your-site.com/api/users \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: invalid-token" \
  -H "Referer: https://your-site.com" \
  -d '{"name":"test"}'

## 10. PUT请求测试
# 测试PUT请求（应该触发CSRF防护）
curl -X PUT http://your-site.com/api/users/1 \
  -H "Content-Type: application/json" \
  -H "Referer: https://evil.com" \
  -d '{"name":"updated"}'

## 11. DELETE请求测试
# 测试DELETE请求（应该触发CSRF防护）
curl -X DELETE http://your-site.com/api/users/1 \
  -H "Referer: https://evil.com"

## 12. PATCH请求测试
# 测试PATCH请求（应该触发CSRF防护）
curl -X PATCH http://your-site.com/api/users/1 \
  -H "Content-Type: application/json" \
  -H "Referer: https://evil.com" \
  -d '{"name":"patched"}'

## 预期结果：
# 1-3, 9-12的测试用例应该被CSRF防护拦截
# 4-8的测试用例应该正常通过（取决于配置）

## 配置建议：
# 1. 生产环境建议配置allowed_referers和allowed_origins
# 2. 如果API需要跨域访问，可以配置allowed_origins
# 3. 对于敏感操作，可以启用require_token
# 4. 将不需要CSRF防护的路径添加到exclude_paths


# 10.文件包含与路径遍历防护测试用例

## 测试URL格式：
# http://your-site.com/page?param=value

## 1. 路径遍历测试
# 测试基本的路径遍历
http://your-site.com/page?file=../../etc/passwd
http://your-site.com/page?file=../../../etc/shadow
http://your-site.com/page?file=../index.php

## 2. 编码路径遍历测试
# 测试URL编码的路径遍历
http://your-site.com/page?file=%2E%2E%2F%2E%2E%2Fetc%2Fpasswd
http://your-site.com/page?file=%252E%252E%252F%252E%252Fetc%2Fpasswd
http://your-site.com/page?file=..%2F..%2Fetc%2Fpasswd

## 3. 绝对路径测试
# 测试绝对路径
http://your-site.com/page?file=/etc/passwd
http://your-site.com/page?file=C:\windows\win.ini
http://your-site.com/page?file=/var/www/html/index.php

## 4. 文件协议测试
# 测试文件协议
http://your-site.com/page?file=file:///etc/passwd
http://your-site.com/page?file=file://C:/windows/win.ini
http://your-site.com/page?file=phar:///path/to/file.phar

## 5. 其他协议测试
# 测试其他可能的协议
http://your-site.com/page?file=zip:///path/to/file.zip
http://your-site.com/page?file=rar:///path/to/file.rar
http://your-site.com/page?file=tar:///path/to/file.tar
http://your-site.com/page?file=jar:///path/to/file.jar

## 6. 敏感文件测试
# 测试访问敏感文件
http://your-site.com/page?file=/etc/passwd
http://your-site.com/page?file=/etc/shadow
http://your-site.com/page?file=/etc/group
http://your-site.com/page?file=/proc/self/environ
http://your-site.com/page?file=/proc/cmdline
http://your-site.com/page?file=windows/win.ini
http://your-site.com/page?file=windows/system32/win.ini

## 7. 边界测试
# 测试边界情况
http://your-site.com/page?file=normal.txt
http://your-site.com/page?file=images/logo.png
http://your-site.com/page?file=css/style.css

## 8. POST请求测试
# 测试POST请求中的文件包含
# POST数据：file=../../etc/passwd
# POST数据：file=file:///etc/passwd

## 9. 排除路径测试
# 测试排除路径（如上传接口）
http://your-site.com/api/upload?file=../../etc/passwd
http://your-site.com/api/files?file=../../../etc/shadow

## 10. 组合测试
# 测试多种技术的组合
http://your-site.com/page?file=..%2F..%2F%2Fetc%2Fpasswd
http://your-site.com/page?file=file:///../etc/passwd

## 预期结果：
# 1-6, 10的测试用例应该被文件包含与路径遍历防护拦截
# 7, 9的测试用例应该正常通过
# 8的测试用例应该被文件包含与路径遍历防护拦截

## 配置建议：
# 1. 生产环境建议保持默认配置
# 2. 将需要允许文件操作的路径添加到exclude_paths
# 3. 对于文件上传接口，确保进行严格的文件类型和路径检查


# 恶意文件上传防护测试用例

## 测试方法：
# 使用curl命令发送文件上传请求

## 1. 上传PHP文件测试
# 测试上传PHP文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.php" \
  -H "Content-Type: multipart/form-data"

## 2. 上传JavaScript文件测试
# 测试上传JavaScript文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.js" \
  -H "Content-Type: multipart/form-data"

## 3. 上传可执行文件测试
# 测试上传可执行文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.exe" \
  -H "Content-Type: multipart/form-data"

## 4. 上传ASP文件测试
# 测试上传ASP文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.asp" \
  -H "Content-Type: multipart/form-data"

## 5. 上传JSP文件测试
# 测试上传JSP文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.jsp" \
  -H "Content-Type: multipart/form-data"

## 6. 上传Shell脚本测试
# 测试上传Shell脚本
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.sh" \
  -H "Content-Type: multipart/form-data"

## 7. 上传Python脚本测试
# 测试上传Python脚本
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.py" \
  -H "Content-Type: multipart/form-data"

## 8. 上传包含恶意代码的图片测试
# 测试上传包含PHP代码的图片
curl -X POST http://your-site.com/api/upload \
  -F "file=@malicious.jpg" \
  -H "Content-Type: multipart/form-data"

## 9. 上传大文件测试
# 测试上传超过大小限制的文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@large_file.zip" \
  -H "Content-Type: multipart/form-data"

## 10. 上传合法文件测试
# 测试上传合法的图片文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@legitimate.jpg" \
  -H "Content-Type: multipart/form-data"

## 11. 上传合法PDF文件测试
# 测试上传合法的PDF文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@document.pdf" \
  -H "Content-Type: multipart/form-data"

## 12. 上传合法文本文件测试
# 测试上传合法的文本文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@text.txt" \
  -H "Content-Type: multipart/form-data"

## 13. 上传合法Office文件测试
# 测试上传合法的Office文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@document.docx" \
  -H "Content-Type: multipart/form-data"

## 14. 上传文件扩展名欺骗测试
# 测试上传文件名包含多个扩展名的文件
curl -X POST http://your-site.com/api/upload \
  -F "file=@image.jpg.php" \
  -H "Content-Type: multipart/form-data"

## 15. MIME类型欺骗测试
# 测试上传PHP文件但设置错误的MIME类型
curl -X POST http://your-site.com/api/upload \
  -F "file=@test.php;type=image/jpeg" \
  -H "Content-Type: multipart/form-data"

## 预期结果：
# 1-9, 14-15的测试用例应该被恶意文件上传防护拦截
# 10-13的测试用例应该正常通过

## 配置建议：
# 1. 生产环境建议保持默认配置
# 2. 根据业务需求调整allowed_types和allowed_extensions
# 3. 调整max_file_size以适应业务需求
# 4. 对于需要允许上传脚本文件的路径，添加到exclude_paths
# 5. 生产环境建议启用check_content以检测文件内容中的恶意代码