import os
import re
import shutil
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from config.settings import settings
from app.waf.manager_service import WAFManagerService

logger = logging.getLogger(__name__)


class WAFSiteService:
    """WAF站点服务类"""
    
    @staticmethod
    def get_site_logs(site_name: str) -> Dict[str, str]:
        """获取指定站点的日志内容
        
        Args:
            site_name: 站点名称
            
        Returns:
            包含访问日志和错误日志内容的字典
        """
        try:
            # 构建日志文件路径
            log_dir = os.path.join(settings.WAF_SITE_LOG_PATH, site_name)
            access_log_path = os.path.join(log_dir, f"{site_name}_access.log")
            error_log_path = os.path.join(log_dir, f"{site_name}_error.log")
            
            # 读取访问日志
            access_log_content = WAFSiteService._read_log_file(access_log_path)
            
            # 读取错误日志
            error_log_content = WAFSiteService._read_log_file(error_log_path)
            
            return {
                "access_log": access_log_content,
                "error_log": error_log_content,
                "message": "success get site logs"
            }
            
        except Exception as e:
            logger.error(f"Failed to get site logs: {str(e)}")
            return {
                "access_log": "",
                "error_log": "",
                "message": f"error: {str(e)}"
            }
    
    @staticmethod
    def get_site_list() -> Dict[str, any]:
        """Get site list
        
        Returns:
            Dictionary containing site list and response message
        """
        try:
            sites = []
            
            # Iterate through configuration files directory
            if os.path.exists(settings.WAF_SITE_CONF_PATH):
                for conf_file in os.listdir(settings.WAF_SITE_CONF_PATH):
                    if conf_file.endswith('.conf'):
                        site_name = conf_file.replace('.conf', '')
                        site_info = WAFSiteService._parse_site_config(conf_file, site_name)
                        if site_info:
                            sites.append(site_info)
            
            return {
                "sites": sites,
                "message": "success get site list"
            }
            
        except Exception as e:
            logger.error(f"Failed to get site list: {str(e)}")
            return {
                "sites": [],
                "message": f"error: {str(e)}"
            }
    
    @staticmethod
    def _parse_site_config(conf_file: str, site_name: str) -> Dict[str, any]:
        """Parse site configuration file
        
        Args:
            conf_file: Configuration file name
            site_name: Site name
            
        Returns:
            Site information dictionary
        """
        try:
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, conf_file)
            
            # Read configuration file content
            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse site type
            site_type = "Static Site" if "root /usr/local/openresty/nginx/html" in content else "Reverse Proxy"
            
            # Parse WAF mode
            waf_mode_match = re.search(r'waf_mode\s+"([^"]+)"', content)
            waf_mode = waf_mode_match.group(1) if waf_mode_match else "block"
            
            # Parse domain
            server_name_match = re.search(r'server_name\s+([^;]+);', content)
            domain = server_name_match.group(1).strip() if server_name_match else ""
            
            # Parse port
            listen_match = re.search(r'listen\s+(\d+)', content)
            port = listen_match.group(1) if listen_match else "80"
            
            # Parse SSL status
            is_ssl = "ssl" in content.lower()
            
            # Parse SSL certificate name
            ssl_cert_name = None
            if is_ssl:
                ssl_cert_match = re.search(r'ssl_certificate\s+/usr/local/openresty/nginx/ssl/([^/]+)/[^;]+;', content)
                if ssl_cert_match:
                    ssl_cert_name = ssl_cert_match.group(1)
            
            # Parse bot verification
            bot_enabled_match = re.search(r'bot_enabled\s+(\d+)', content)
            bot_verify_enabled_match = re.search(r'bot_verify_enabled\s+(\d+)', content)
            bot_enabled = bot_enabled_match.group(1) if bot_enabled_match else "0"
            bot_verify_enabled = bot_verify_enabled_match.group(1) if bot_verify_enabled_match else "0"
            
            bot_status = "Disabled"
            if bot_enabled == "1":
                if bot_verify_enabled == "0":
                    bot_status = "Silent Verification"
                elif bot_verify_enabled == "1":
                    bot_status = "5s Verification"
                elif bot_verify_enabled == "2":
                    bot_status = "Slide Verification"
            
            # Parse CC protection
            cc_enabled_match = re.search(r'cc_enabled\s+(\d+)', content)
            cc_status = "Enabled" if (cc_enabled_match and cc_enabled_match.group(1) == "1") else "Disabled"
            
            # Parse detailed protection status
            protection_status = {
                "sql_injection": WAFSiteService._parse_protection_status(content, "sql_enabled"),
                "xss": WAFSiteService._parse_protection_status(content, "xss_enabled"),
                "command_injection": WAFSiteService._parse_protection_status(content, "cmd_injection_enabled"),
                "ssrf": WAFSiteService._parse_protection_status(content, "ssrf_enabled"),
                "ldap_injection": WAFSiteService._parse_protection_status(content, "ldap_injection_enabled"),
                "csrf": WAFSiteService._parse_protection_status(content, "csrf_enabled"),
                "file_inclusion": WAFSiteService._parse_protection_status(content, "file_inclusion_enabled"),
                "file_upload": WAFSiteService._parse_protection_status(content, "file_upload_enabled"),
                "scanner": WAFSiteService._parse_protection_status(content, "scanner_enabled")
            }
            
            # Parse upstream server / static root path
            if site_type == "Static Site":
                upstream_server = os.path.join(settings.WAF_SITE_WWW_PATH, site_name)
            else:
                upstream_match = re.search(r'proxy_pass\s+([^;]+);', content)
                upstream_server = upstream_match.group(1).strip() if upstream_match else ""
            
            # Count today's requests
            today_requests = WAFSiteService._count_today_requests(site_name)
            
            # Count today's blocks
            today_blocks = WAFSiteService._count_today_blocks(site_name, domain, port, is_ssl)
            
            return {
                "name": site_name,
                "type": site_type,
                "waf_mode": waf_mode,
                "domain": domain,
                "port": port,
                "is_ssl": is_ssl,
                "ssl_cert_name": ssl_cert_name,
                "bot_status": bot_status,
                "cc_status": cc_status,
                "protection_status": protection_status,
                "upstream_server": upstream_server,
                "today_requests": today_requests,
                "today_blocks": today_blocks
            }
            
        except Exception as e:
            logger.error(f"Failed to parse site configuration: {str(e)}")
            return None
    
    @staticmethod
    def _count_today_requests(site_name: str) -> int:
        """Count today's requests
        
        Args:
            site_name: Site name
            
        Returns:
            Today's requests count
        """
        try:
            log_dir = os.path.join(settings.WAF_SITE_LOG_PATH, site_name)
            access_log_path = os.path.join(log_dir, f"{site_name}_access.log")
            
            if not os.path.exists(access_log_path):
                return 0
            
            today = datetime.now().strftime("%d/%b/%Y")
            count = 0
            
            with open(access_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if today in line:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to count today's requests: {str(e)}")
            return 0
    
    @staticmethod
    def _count_today_blocks(site_name: str, domain: str, port: str, is_ssl: bool) -> int:
        """统计今日拦截数
        
        Args:
            site_name: 站点名称
            domain: 域名
            port: 端口
            is_ssl: 是否SSL
            
        Returns:
            今日拦截数
        """
        try:
            if not os.path.exists(settings.WAF_LOG_PATH):
                return 0
            
            today = datetime.now().strftime("%Y-%m-%d")
            count = 0
            
            # 构建应用标识
            scheme = "https" if is_ssl else "http"
            application = f"{scheme}://{domain}:{port}"
            
            with open(settings.WAF_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if today in line and application in line:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计今日拦截数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _parse_protection_status(content: str, protection_key: str) -> str:
        """Parse protection status
        
        Args:
            content: Configuration file content
            protection_key: Protection key name
            
        Returns:
            Protection status: Enabled/Disabled
        """
        match = re.search(rf'{protection_key}\s+(\d+)', content)
        return "Enabled" if (match and match.group(1) == "1") else "Disabled"
    
    @staticmethod
    def _read_log_file(file_path: str) -> str:
        """读取日志文件内容
        
        Args:
            file_path: 日志文件路径
            
        Returns:
            日志文件内容
        """
        try:
            if not os.path.exists(file_path):
                return "日志文件不存在"
            
            # 读取文件内容，限制大小为10MB
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10 * 1024 * 1024)  # 10MB
            
            return content
            
        except Exception as e:
            logger.error(f"读取日志文件失败: {str(e)}")
            return f"读取日志文件失败: {str(e)}"
    
    @staticmethod
    def clean_site_logs(site_name: str, log_type: str) -> dict:
        """清理指定站点的日志文件
        
        Args:
            site_name: 站点名称
            log_type: 日志类型，access或error
            
        Returns:
            清理结果
        """
        try:
            # 构建日志文件路径
            if log_type == "access":
                log_file = os.path.join(settings.WAF_SITE_LOG_PATH, site_name, f"{site_name}_access.log")
            elif log_type == "error":
                log_file = os.path.join(settings.WAF_SITE_LOG_PATH, site_name, f"{site_name}_error.log")
            else:
                return {"message": "Invalid log type. Must be 'access' or 'error'"}
            
            # 检查文件是否存在
            if not os.path.exists(log_file):
                return {"message": f"Log file not found: {log_file}"}
            
            # 清空日志文件
            with open(log_file, 'w') as f:
                f.write('')
            
            return {"message": f"Successfully cleaned {log_type} log for site {site_name}"}
            
        except Exception as e:
            logger.error(f"清理站点日志失败: {str(e)}")
            return {"message": f"Failed to clean log: {str(e)}"}
    
    @staticmethod
    async def update_site(site_name: str, update_data: Dict[str, any]) -> Dict[str, str]:
        """更新指定站点的配置
        
        Args:
            site_name: 站点名称
            update_data: 更新数据
            
        Returns:
            更新结果
        """
        try:
            # 构建配置文件路径
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            
            # 检查文件是否存在
            if not os.path.exists(conf_path):
                return {"message": f"Site configuration file not found: {conf_path}"}
            
            # 读取配置文件内容
            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 更新WAF模式
            if 'waf_mode' in update_data:
                content = re.sub(r'set \$waf_mode "([^"]+)";', f'set $waf_mode "{update_data["waf_mode"]}";', content)
            
            # 更新BOT验证
            if 'bot_enabled' in update_data:
                content = re.sub(r'set \$bot_enabled (\d+);', f'set $bot_enabled {update_data["bot_enabled"]};', content)
            if 'bot_verify_enabled' in update_data:
                content = re.sub(r'set \$bot_verify_enabled (\d+);', f'set $bot_verify_enabled {update_data["bot_verify_enabled"]};', content)
            
            # 更新域名
            if 'domain' in update_data:
                content = re.sub(r'server_name\s+[^;]+;', f'server_name {update_data["domain"]};', content)
            
            # 更新端口
            if 'port' in update_data:
                # 处理SSL端口
                if 'ssl' in content.lower():
                    content = re.sub(r'listen\s+\d+\s*ssl;', f'listen {update_data["port"]} ssl;', content)
                else:
                    content = re.sub(r'listen\s+\d+;', f'listen {update_data["port"]};', content)
            
            # 更新CC防护
            if 'cc_enabled' in update_data:
                content = re.sub(r'set \$cc_enabled (\d+);', f'set $cc_enabled {update_data["cc_enabled"]};', content)
            
            # 更新上游服务器（仅限反向代理站点）
            if 'upstream_server' in update_data and 'proxy_pass' in content:
                content = re.sub(r'proxy_pass\s+[^;]+;', f'proxy_pass {update_data["upstream_server"]};', content)
            
            # 写回配置文件
            with open(conf_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            
            # 自动重启WAF容器使配置生效
            try:
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"Successfully restarted WAF container after updating site {site_name}")
            except Exception as restart_error:
                logger.error(f"Failed to restart WAF container: {str(restart_error)}")
                # 重启失败不影响配置更新结果
            
            return {"message": f"Successfully updated site {site_name} and restarted WAF container"}
            
        except Exception as e:
            logger.error(f"更新站点配置失败: {str(e)}")
            return {"message": f"Failed to update site: {str(e)}"}
    
    @staticmethod
    async def update_site_ssl(site_name: str, ssl_data: dict) -> dict:
        """更新指定站点的SSL配置"""
        try:
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            
            if not os.path.exists(conf_path):
                return {"message": f"Site configuration file not found: {conf_path}"}
            
            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            enabled = ssl_data.get('enabled', False)
            
            # --- 第一步：清理现有所有 SSL 相关的配置 ---
            # 1. 移除 listen 行的 ssl 标记
            content = re.sub(r'(listen\s+\d+)\s+ssl(?=\s*;)', r'\1', content)
            # 2. 移除 http2 指令
            content = re.sub(r'^\s*http2\s+(on|off);\n?', '', content, flags=re.MULTILINE)
            # 3. 移除 SSL 配置块 (匹配 ssl_ 开头的行以及相关的注释)
            content = re.sub(r'^\s*#\s*SSL\s*(配置|优化).*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*ssl_\w+.*?;.*\n?', '', content, flags=re.MULTILINE)

            # --- 第二步：如果开启 SSL，则注入新配置 ---
            if enabled:
                cert_name = ssl_data.get('cert_name')
                if not cert_name:
                    return {"message": "Error: cert_name is required when SSL is enabled"}

                http2 = ssl_data.get('http2', True)
                protocols = ssl_data.get('ssl_protocols', 'TLSv1.2 TLSv1.3')
                ciphers = ssl_data.get('ssl_ciphers', 'ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384')

                # 修改 listen 行添加 ssl
                content = re.sub(r'(listen\s+\d+)(?=\s*;)', r'\1 ssl', content)

                # 构建 SSL 配置块
                ssl_block = []
                if http2:
                    ssl_block.append("    http2 on;")
                
                ssl_block.append(f"\n    # SSL 配置")
                ssl_block.append(f"    ssl_certificate /usr/local/openresty/nginx/ssl/{cert_name}/{cert_name}.pem;")
                ssl_block.append(f"    ssl_certificate_key /usr/local/openresty/nginx/ssl/{cert_name}/{cert_name}.key;")
                ssl_block.append(f"\n    # SSL 优化")
                ssl_block.append(f"    ssl_protocols {protocols};")
                ssl_block.append(f"    ssl_prefer_server_ciphers on;")
                ssl_block.append(f"    ssl_ciphers {ciphers};")
                ssl_block.append(f"    ssl_session_timeout 1d;")
                ssl_block.append(f"    ssl_session_cache shared:SSL:10m;")
                ssl_block.append(f"    ssl_session_tickets off;")
                
                ssl_config_str = "\n".join(ssl_block)

                # 在 server_name 行后插入
                if "server_name" in content:
                    content = re.sub(r'(server_name\s+[^;]+;)', r'\1\n' + ssl_config_str, content)
                else:
                    # 如果没找到 server_name，在第一个 listen 后插入
                    content = re.sub(r'(listen\s+[^;]+;)', r'\1\n' + ssl_config_str, content)

            # --- 第三步：配置清洗 ---
            # 合并连续空行，确保格式整洁
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

            # --- 第四步：保存与重启 ---
            with open(conf_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            try:
                # 建议先 check 再 restart
                # await WAFManagerService.operate_waf_container('check') 
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"SSL updated and WAF restarted for {site_name}")
            except Exception as e:
                logger.error(f"WAF restart failed: {str(e)}")
                return {"message": f"Config saved but WAF restart failed: {str(e)}"}

            return {"status": "success", "message": f"SSL {'enabled' if enabled else 'disabled'} for {site_name}"}

        except Exception as e:
            logger.error(f"Update SSL failed: {str(e)}")
            return {"message": f"Internal error: {str(e)}"}

    @staticmethod
    async def update_site_protection(site_name: str, protection_data: dict) -> dict:
        """更新指定站点的漏洞防护配置
        
        Args:
            site_name: 站点名称
            protection_data: 漏洞防护配置数据
                - sql_injection: SQL注入防护开关
                - xss: XSS防护开关
                - command_injection: 命令注入防护开关
                - ssrf: SSRF防护开关
                - ldap_injection: LDAP注入防护开关
                - csrf: CSRF防护开关
                - file_inclusion: 文件包含防护开关
                - file_upload: 恶意文件上传防护开关
                - scanner: 扫描器防护开关
            
        Returns:
            更新结果
        """
        try:
            # 构建配置文件路径
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            
            # 检查文件是否存在
            if not os.path.exists(conf_path):
                return {"message": f"Site configuration file not found: {conf_path}"}
            
            # 读取配置文件内容
            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 映射配置字段到配置文件中的变量名
            protection_mapping = {
                'sql_injection': 'sql_enabled',
                'xss': 'xss_enabled',
                'command_injection': 'cmd_injection_enabled',
                'ssrf': 'ssrf_enabled',
                'ldap_injection': 'ldap_injection_enabled',
                'csrf': 'csrf_enabled',
                'file_inclusion': 'file_inclusion_enabled',
                'file_upload': 'file_upload_enabled',
                'scanner': 'scanner_enabled'
            }
            
            # 更新防护配置
            for key, value in protection_data.items():
                if key in protection_mapping:
                    config_key = protection_mapping[key]
                    enabled_value = 1 if value else 0
                    # 替换配置值
                    content = re.sub(
                        rf'set \${config_key} \d+;',
                        f'set ${config_key} {enabled_value};',
                        content
                    )
            
            # 清理多余的空行
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # 写回配置文件
            with open(conf_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            
            # 自动重启WAF容器使配置生效
            try:
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"Successfully restarted WAF container after updating protection config for site {site_name}")
            except Exception as restart_error:
                logger.error(f"Failed to restart WAF container: {str(restart_error)}")
                return {"message": f"Config saved but WAF restart failed: {str(restart_error)}"}
            
            return {"status": "success", "message": f"Successfully updated protection config for site {site_name}"}
            
        except Exception as e:
            logger.error(f"更新站点漏洞防护配置失败: {str(e)}")
            return {"message": f"Internal error: {str(e)}"}
    
    @staticmethod
    def get_site_config(site_name: str) -> dict:
        """获取指定站点的配置文件内容
        
        Args:
            site_name: 站点名称
            
        Returns:
            包含配置文件内容的字典
        """
        try:
            # 构建配置文件路径
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            
            # 检查文件是否存在
            if not os.path.exists(conf_path):
                return {"content": "", "message": f"Site configuration file not found: {conf_path}"}
            
            # 读取配置文件内容
            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return {
                "content": content,
                "message": "success get site config"
            }
            
        except Exception as e:
            logger.error(f"Failed to get site config: {str(e)}")
            return {
                "content": "",
                "message": f"error: {str(e)}"
            }
    
    @staticmethod
    async def update_site_config(site_name: str, content: str) -> dict:
        """修改指定站点的配置文件内容
        
        Args:
            site_name: 站点名称
            content: 新的配置文件内容
            
        Returns:
            更新结果
        """
        try:
            # 构建配置文件路径
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            
            # 检查文件是否存在
            if not os.path.exists(conf_path):
                return {"message": f"Site configuration file not found: {conf_path}"}
            
            # 写回配置文件
            with open(conf_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(content)
            
            # 自动重启WAF容器使配置生效
            try:
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"Successfully restarted WAF container after updating site config for {site_name}")
            except Exception as restart_error:
                logger.error(f"Failed to restart WAF container: {str(restart_error)}")
                return {"message": f"Config saved but WAF restart failed: {str(restart_error)}"}
            
            return {"message": f"Successfully updated site config for {site_name} and restarted WAF container"}
            
        except Exception as e:
            logger.error(f"更新站点配置文件失败: {str(e)}")
            return {"message": f"Failed to update site config: {str(e)}"}

    @staticmethod
    def get_html_pages() -> dict:
        """获取WAF HTML页面列表（包含所有页面的内容）

        Returns:
            HTML页面列表（包含内容）
        """
        try:
            pages = []

            if not os.path.exists(settings.WAF_HTML_PATH):
                return {
                    "pages": [],
                    "message": "HTML目录不存在"
                }

            for file_name in os.listdir(settings.WAF_HTML_PATH):
                if file_name.endswith('.html'):
                    file_path = os.path.join(settings.WAF_HTML_PATH, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception:
                        content = ""
                    pages.append({
                        "name": file_name,
                        "path": file_path,
                        "content": content
                    })

            return {
                "pages": pages,
                "message": "success get HTML pages list with content"
            }

        except Exception as e:
            logger.error(f"获取HTML页面列表失败: {str(e)}")
            return {
                "pages": [],
                "message": f"error: {str(e)}"
            }

    @staticmethod
    async def update_html_page_content(file_name: str, content: str) -> dict:
        """修改指定WAF HTML页面的内容

        Args:
            file_name: HTML文件名
            content: 新的HTML内容

        Returns:
            修改结果
        """
        try:
            file_path = os.path.join(settings.WAF_HTML_PATH, file_name)

            if not os.path.exists(file_path):
                return {
                    "name": file_name,
                    "message": f"HTML file not found: {file_name}"
                }

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "name": file_name,
                "message": f"success updated HTML page: {file_name}"
            }

        except Exception as e:
            logger.error(f"修改HTML页面内容失败: {str(e)}")
            return {
                "name": file_name,
                "message": f"error: {str(e)}"
            }

    @staticmethod
    async def create_site(site_name: str, site_type: str, domain: str, port: str,
                         upstream_server: str = "", is_ssl: bool = False,
                         ssl_cert_name: str = "", index_content: str = "") -> dict:
        """创建新站点

        根据站点类型创建对应的配置文件和相关目录：
        - 静态站点：创建 conf + www目录(含默认index.html) + 日志目录
        - 反向代理站点：创建 conf + 日志目录

        Args:
            site_name: 站点名称
            site_type: 站点类型: Static Site / Reverse Proxy
            domain: 域名
            port: 端口
            upstream_server: 上游服务器地址（仅反向代理站点需要）
            is_ssl: 是否启用SSL
            ssl_cert_name: SSL证书名称（启用SSL时必填）
            index_content: 自定义index.html内容（仅静态站点，不传则使用默认模板）

        Returns:
            创建结果
        """
        try:
            if site_type not in ["Static Site", "Reverse Proxy"]:
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "domain": domain,
                    "port": port,
                    "message": f"Invalid site_type: {site_type}. Must be 'Static Site' or 'Reverse Proxy'"
                }

            if site_type == "Reverse Proxy" and not upstream_server:
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "domain": domain,
                    "port": port,
                    "message": "upstream_server is required for Reverse Proxy sites"
                }

            if is_ssl and not ssl_cert_name:
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "domain": domain,
                    "port": port,
                    "message": "ssl_cert_name is required when is_ssl is True"
                }

            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")
            if os.path.exists(conf_path):
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "domain": domain,
                    "port": port,
                    "message": f"Site already exists: {site_name}"
                }

            waf_protection_settings = (
                '    set $waf_mode "record";\n'
                '    set $cc_enabled 1;\n'
                '    set $sql_enabled 1;\n'
                '    set $xss_enabled 1;\n'
                '    set $ssrf_enabled 1;\n'
                '    set $cmd_injection_enabled 1;\n'
                '    set $ldap_injection_enabled 1;\n'
                '    set $csrf_enabled 1;\n'
                '    set $file_inclusion_enabled 1;\n'
                '    set $file_upload_enabled 1;\n'
                '    set $scanner_enabled 1;\n'
                '    set $bot_enabled 1;\n'
                '    set $bot_verify_enabled 1;\n'
                '    set $waf_type "-";\n'
                '    set $waf_action "-";\n'
            )

            security_headers = (
                '    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n'
                '    add_header X-Content-Type-Options nosniff;\n'
                '    add_header X-Frame-Options SAMEORIGIN;\n'
                '    add_header X-XSS-Protection "1; mode=block";\n'
            )

            log_config = (
                f'    access_log /usr/local/openresty/nginx/logs/access.log main;\n'
                f'    access_log /usr/local/openresty/nginx/sitelogs/{site_name}/{site_name}_access.log main;\n'
                f'    error_log /usr/local/openresty/nginx/sitelogs/{site_name}/{site_name}_error.log warn;\n'
            )

            waf_lua_config = (
                '    access_by_lua_file /usr/local/openresty/nginx/lua/waf.lua;\n'
                '    include /usr/local/openresty/nginx/conf/error_locations.conf;\n'
            )

            if site_type == "Static Site":
                www_dir = os.path.join(settings.WAF_SITE_WWW_PATH, site_name)
                os.makedirs(www_dir, exist_ok=True)
                default_html = os.path.join(www_dir, "index.html")
                if not os.path.exists(default_html):
                    html_content = index_content if index_content else (
                        '<!DOCTYPE html>\n<html>\n<head>\n'
                        f'    <title>{site_name}</title>\n'
                        '</head>\n<body>\n'
                        f'    <center><h1>{site_name}</h1></center>\n'
                        f'    <center>Welcome to {site_name}</center>\n'
                        f'    <hr><center>Blackpotbpanel/2.0</center>\n'
                        '</body>\n</html>\n'
                    )
                    with open(default_html, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f"Created index.html for static site {site_name}")

                ssl_block = ""
                if is_ssl:
                    ssl_block = (
                        f'\n    http2 on;\n'
                        f'    # SSL 配置\n'
                        f'    ssl_certificate /usr/local/openresty/nginx/ssl/{ssl_cert_name}/{ssl_cert_name}.pem;\n'
                        f'    ssl_certificate_key /usr/local/openresty/nginx/ssl/{ssl_cert_name}/{ssl_cert_name}.key;\n'
                        f'    # SSL 优化\n'
                        f'    ssl_protocols TLSv1.2 TLSv1.3;\n'
                        f'    ssl_prefer_server_ciphers on;\n'
                        f'    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;\n'
                        f'    ssl_session_timeout 1d;\n'
                        f'    ssl_session_cache shared:SSL:10m;\n'
                        f'    ssl_session_tickets off;\n'
                    )

                listen_directive = f"listen {port} ssl;" if is_ssl else f"listen {port};"

                conf_content = (
                    f'server {{\n'
                    f'    {listen_directive}\n'
                    f'    server_name {domain};'
                    f'{ssl_block}\n\n'
                    f'{waf_protection_settings}\n'
                    f'{security_headers}\n'
                    f'    root /usr/local/openresty/nginx/html/{site_name};\n'
                    f'    index index.html;\n\n'
                    f'{log_config}\n'
                    f'{waf_lua_config}\n'
                    f'    location / {{\n'
                    f'        try_files $uri $uri/ =404;\n'
                    f'    }}\n\n'
                    f'}}\n'
                )
            else:
                ssl_block = ""
                if is_ssl:
                    ssl_block = (
                        f'\n    http2 on;\n'
                        f'    # SSL 配置\n'
                        f'    ssl_certificate /usr/local/openresty/nginx/ssl/{ssl_cert_name}/{ssl_cert_name}.pem;\n'
                        f'    ssl_certificate_key /usr/local/openresty/nginx/ssl/{ssl_cert_name}/{ssl_cert_name}.key;\n'
                        f'    # SSL 优化\n'
                        f'    ssl_protocols TLSv1.2 TLSv1.3;\n'
                        f'    ssl_prefer_server_ciphers on;\n'
                        f'    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;\n'
                        f'    ssl_session_timeout 1d;\n'
                        f'    ssl_session_cache shared:SSL:10m;\n'
                        f'    ssl_session_tickets off;\n'
                    )

                listen_directive = f"listen {port} ssl;" if is_ssl else f"listen {port};"

                conf_content = (
                    f'server {{\n'
                    f'    {listen_directive}\n'
                    f'    server_name {domain};'
                    f'{ssl_block}\n\n'
                    f'{waf_protection_settings}\n'
                    f'{security_headers}\n'
                    f'{log_config}\n'
                    f'{waf_lua_config}\n'
                    f'    location / {{\n'
                    f'        proxy_pass {upstream_server};\n'
                    f'        proxy_set_header Host $host;\n'
                    f'        proxy_set_header X-Real-IP $remote_addr;\n'
                    f'        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n'
                    f'        proxy_set_header X-Forwarded-Proto $scheme;\n\n'
                    f'        proxy_connect_timeout 30;\n'
                    f'        proxy_send_timeout 60;\n'
                    f'        proxy_read_timeout 60;\n\n'
                    f'        proxy_buffering on;\n'
                    f'        proxy_buffer_size 16k;\n'
                    f'        proxy_buffers 4 16k;\n'
                    f'    }}\n\n'
                    f'}}\n'
                )

            os.makedirs(settings.WAF_SITE_CONF_PATH, exist_ok=True)
            with open(conf_path, 'w', encoding='utf-8') as f:
                f.write(conf_content)
            logger.info(f"Created site config file: {conf_path}")

            log_dir = os.path.join(settings.WAF_SITE_LOG_PATH, site_name)
            os.makedirs(log_dir, exist_ok=True)

            try:
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"Successfully restarted WAF container after creating site {site_name}")
            except Exception as restart_error:
                logger.error(f"Failed to restart WAF container: {str(restart_error)}")
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "domain": domain,
                    "port": port,
                    "message": f"Site created but WAF restart failed: {str(restart_error)}"
                }

            return {
                "site_name": site_name,
                "site_type": site_type,
                "domain": domain,
                "port": port,
                "message": f"Successfully created {site_type} site: {site_name}"
            }

        except Exception as e:
            logger.error(f"创建站点失败: {str(e)}")
            return {
                "site_name": site_name,
                "site_type": site_type,
                "domain": domain,
                "port": port,
                "message": f"Failed to create site: {str(e)}"
            }

    @staticmethod
    async def delete_site(site_name: str) -> dict:
        """删除指定站点

        根据站点类型执行不同的清理操作：
        - 静态站点：删除配置文件 + www目录 + 日志目录
        - 反向代理站点：删除配置文件 + 日志目录

        Args:
            site_name: 站点名称

        Returns:
            删除结果
        """
        try:
            conf_path = os.path.join(settings.WAF_SITE_CONF_PATH, f"{site_name}.conf")

            if not os.path.exists(conf_path):
                return {
                    "site_name": site_name,
                    "site_type": "Unknown",
                    "message": f"Site configuration file not found: {conf_path}"
                }

            with open(conf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            site_type = "Static Site" if "root /usr/local/openresty/nginx/html" in content else "Reverse Proxy"

            os.remove(conf_path)
            logger.info(f"Deleted site config file: {conf_path}")

            if site_type == "Static Site":
                www_path = os.path.join(settings.WAF_SITE_WWW_PATH, site_name)
                if os.path.exists(www_path):
                    shutil.rmtree(www_path)
                    logger.info(f"Deleted static site www directory: {www_path}")

            log_dir = os.path.join(settings.WAF_SITE_LOG_PATH, site_name)
            if os.path.exists(log_dir):
                shutil.rmtree(log_dir)
                logger.info(f"Deleted site log directory: {log_dir}")

            try:
                await WAFManagerService.operate_waf_container('restart')
                logger.info(f"Successfully restarted WAF container after deleting site {site_name}")
            except Exception as restart_error:
                logger.error(f"Failed to restart WAF container: {str(restart_error)}")
                return {
                    "site_name": site_name,
                    "site_type": site_type,
                    "message": f"Site deleted but WAF restart failed: {str(restart_error)}"
                }

            return {
                "site_name": site_name,
                "site_type": site_type,
                "message": f"Successfully deleted {site_type} site: {site_name}"
            }

        except Exception as e:
            logger.error(f"删除站点失败: {str(e)}")
            return {
                "site_name": site_name,
                "site_type": "Unknown",
                "message": f"Failed to delete site: {str(e)}"
            }