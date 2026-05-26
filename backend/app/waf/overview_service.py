import os
import re
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from collections import Counter
from config.settings import settings

logger = logging.getLogger(__name__)


class WAFOverviewService:
    """WAF概览服务类"""
    
    @staticmethod
    def get_waf_qps() -> Dict[str, any]:
        """获取WAF QPS和请求统计 - 实时监控数据
        
        返回最近2分钟的数据，每5秒一个数据点
        
        Returns:
            包含实时监控数据的字典
        """
        try:
            # 生成最近2分钟的时间点（每5秒一个点，共24个点）
            nodes = []
            now = datetime.now()
            
            # 从2分钟前开始，每5秒一个时间点
            for i in range(24, -1, -1):
                time_point = now - timedelta(seconds=i * 5)
                time_str = time_point.strftime("%H:%M:%S")
                
                # 统计这个5秒时间段的请求数
                start_time = time_point - timedelta(seconds=5)
                requests = WAFOverviewService._count_requests_in_range(start_time, time_point)
                
                # 统计这个5秒时间段的拦截数
                blocks = WAFOverviewService._count_blocks_in_range(start_time, time_point)
                
                # 计算QPS（每秒请求数）
                qps = round(requests / 5, 2) if requests > 0 else 0.0
                
                nodes.append({
                    "qps": qps,
                    "requests": requests,
                    "blocks": blocks,
                    "time": time_str
                })
            
            return {
                "data": {
                    "nodes": nodes
                },
                "err": None,
                "msg": "success get waf qps"
            }
            
        except Exception as e:
            logger.error(f"获取WAF QPS失败: {str(e)}")
            return {
                "data": {
                    "nodes": []
                },
                "err": str(e),
                "msg": f"error: {str(e)}"
            }
    
    @staticmethod
    def get_client_stats() -> Dict[str, any]:
        """获取客户端统计和响应状态统计
        
        Returns:
            包含操作系统、浏览器和响应状态码统计的字典
        """
        try:
            if not os.path.exists(settings.WAF_ACCESS_LOG_PATH):
                return {
                    "operating_systems": [],
                    "browsers": [],
                    "status_codes": [],
                    "message": "Access log file not found"
                }
            
            os_count = Counter()
            browser_count = Counter()
            status_count = Counter()
            
            # 读取访问日志文件
            with open(settings.WAF_ACCESS_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # 解析日志行
                    parsed = WAFOverviewService._parse_access_log_line(line)
                    if parsed:
                        # 统计操作系统
                        if parsed['os']:
                            os_count[parsed['os']] += 1
                        
                        # 统计浏览器
                        if parsed['browser']:
                            browser_count[parsed['browser']] += 1
                        
                        # 统计响应状态码
                        if parsed['status_code']:
                            status_count[parsed['status_code']] += 1
            
            # 按数量从多到少排序
            operating_systems = [
                {"name": os, "count": count} 
                for os, count in os_count.most_common()
            ]
            
            browsers = [
                {"name": browser, "count": count} 
                for browser, count in browser_count.most_common()
            ]
            
            status_codes = [
                {"status_code": status, "count": count} 
                for status, count in status_count.most_common()
            ]
            
            return {
                "operating_systems": operating_systems,
                "browsers": browsers,
                "status_codes": status_codes,
                "message": "success get client stats"
            }
            
        except Exception as e:
            logger.error(f"获取客户端统计失败: {str(e)}")
            return {
                "operating_systems": [],
                "browsers": [],
                "status_codes": [],
                "message": f"error: {str(e)}"
            }
    
    @staticmethod
    def _parse_access_log_line(log_line: str) -> Dict[str, str]:
        """解析访问日志行
        
        Args:
            log_line: 日志行
            
        Returns:
            解析出的信息字典，包含os、browser、status_code
        """
        try:
            # 匹配Nginx访问日志格式
            # 示例: 192.168.223.1 - - [01/Apr/2026:15:09:04 +0800] "GET /login HTTP/2.0" 200 458 "https://192.168.223.180:444/login" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36" "-"
            
            # 提取所有引号内的内容
            quoted_strings = re.findall(r'"([^"]*)"', log_line)
            if len(quoted_strings) < 3:
                return {"os": "", "browser": "", "status_code": ""}
            
            # User-Agent 是倒数第二个引号内容 (格式: "请求" "referer" "user_agent" "其他")
            user_agent = quoted_strings[-2] if len(quoted_strings) >= 2 else ""
            
            # 提取状态码
            status_match = re.search(r'"\s+(\d+)\s+\d+', log_line)
            status_code = status_match.group(1) if status_match else ""
            
            # 解析操作系统
            os_name = WAFOverviewService._parse_os(user_agent)
            
            # 解析浏览器
            browser = WAFOverviewService._parse_browser(user_agent)
            
            return {
                "os": os_name,
                "browser": browser,
                "status_code": status_code
            }
            
        except Exception as e:
            logger.error(f"解析访问日志行失败: {str(e)}")
            return {"os": "", "browser": "", "status_code": ""}
    
    @staticmethod
    def _parse_os(user_agent: str) -> str:
        """解析操作系统
        
        Args:
            user_agent: User-Agent字符串
            
        Returns:
            操作系统名称
        """
        user_agent_lower = user_agent.lower()
        
        # Windows
        if 'windows nt 10.0' in user_agent_lower:
            return 'Windows 10/11'
        elif 'windows nt 6.3' in user_agent_lower:
            return 'Windows 8.1'
        elif 'windows nt 6.2' in user_agent_lower:
            return 'Windows 8'
        elif 'windows nt 6.1' in user_agent_lower:
            return 'Windows 7'
        elif 'windows nt 6.0' in user_agent_lower:
            return 'Windows Vista'
        elif 'windows nt 5.1' in user_agent_lower:
            return 'Windows XP'
        elif 'windows' in user_agent_lower:
            return 'Windows'
        
        # macOS
        elif 'mac os x' in user_agent_lower:
            match = re.search(r'mac os x (\d+)[._](\d+)', user_agent_lower)
            if match:
                major, minor = match.groups()
                return f'macOS {major}.{minor}'
            return 'macOS'
        
        # Linux
        elif 'linux' in user_agent_lower:
            if 'ubuntu' in user_agent_lower:
                return 'Ubuntu'
            elif 'fedora' in user_agent_lower:
                return 'Fedora'
            elif 'debian' in user_agent_lower:
                return 'Debian'
            elif 'centos' in user_agent_lower:
                return 'CentOS'
            else:
                return 'Linux'
        
        # Android
        elif 'android' in user_agent_lower:
            match = re.search(r'android (\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Android {version}'
            return 'Android'
        
        # iOS
        elif 'iphone' in user_agent_lower:
            match = re.search(r'iphone os (\d+)_(\d+)', user_agent_lower)
            if match:
                major, minor = match.groups()
                return f'iOS {major}.{minor}'
            return 'iOS'
        elif 'ipad' in user_agent_lower:
            match = re.search(r'ipad.*os (\d+)_(\d+)', user_agent_lower)
            if match:
                major, minor = match.groups()
                return f'iPadOS {major}.{minor}'
            return 'iPadOS'
        
        else:
            return 'Other'
    
    @staticmethod
    def _parse_browser(user_agent: str) -> str:
        """解析浏览器
        
        Args:
            user_agent: User-Agent字符串
            
        Returns:
            浏览器名称
        """
        user_agent_lower = user_agent.lower()
        
        # Chrome
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            match = re.search(r'chrome/(\d+\.\d+\.\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Chrome {version}'
            return 'Chrome'
        
        # Edge
        elif 'edg' in user_agent_lower:
            match = re.search(r'edg/(\d+\.\d+\.\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Edge {version}'
            return 'Edge'
        
        # Firefox
        elif 'firefox' in user_agent_lower:
            match = re.search(r'firefox/(\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Firefox {version}'
            return 'Firefox'
        
        # Safari
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            match = re.search(r'version/(\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Safari {version}'
            return 'Safari'
        
        # Opera
        elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
            match = re.search(r'(?:opera|opr)/(\d+\.\d+)', user_agent_lower)
            if match:
                version = match.group(1)
                return f'Opera {version}'
            return 'Opera'
        
        # IE
        elif 'msie' in user_agent_lower or 'trident' in user_agent_lower:
            return 'Internet Explorer'
        
        else:
            return 'Other'
    
    @staticmethod
    def _count_requests_in_range(start_time: datetime, end_time: datetime) -> int:
        """统计指定时间范围内的请求数
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指定时间范围内的请求数
        """
        try:
            if not os.path.exists(settings.WAF_ACCESS_LOG_PATH):
                return 0
            
            count = 0
            
            # 读取访问日志文件
            with open(settings.WAF_ACCESS_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                # 从文件末尾开始读取，提高效率
                f.seek(0, os.SEEK_END)
                position = f.tell()
                line = ''
                
                # 倒序读取文件
                while position > 0:
                    position -= 1
                    f.seek(position)
                    char = f.read(1)
                    if char == '\n':
                        if line:
                            # 解析日志行，提取时间
                            log_time = WAFOverviewService._parse_log_time(line)
                            if log_time:
                                # 将带时区的时间转换为不带时区的时间进行比较
                                log_time_naive = log_time.replace(tzinfo=None)
                                if start_time <= log_time_naive <= end_time:
                                    count += 1
                                elif log_time_naive < start_time:
                                    # 已经超出时间范围，停止读取
                                    break
                            line = ''
                    else:
                        line = char + line
                
                # 处理最后一行
                if line:
                    log_time = WAFOverviewService._parse_log_time(line)
                    if log_time:
                        log_time_naive = log_time.replace(tzinfo=None)
                        if start_time <= log_time_naive <= end_time:
                            count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计时间范围内请求数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _count_blocks_in_range(start_time: datetime, end_time: datetime) -> int:
        """统计指定时间范围内的拦截数
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指定时间范围内的拦截数
        """
        try:
            if not os.path.exists(settings.WAF_LOG_PATH):
                return 0
            
            count = 0
            
            # 读取WAF日志文件
            with open(settings.WAF_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                # 从文件末尾开始读取，提高效率
                f.seek(0, os.SEEK_END)
                position = f.tell()
                line = ''
                
                # 倒序读取文件
                while position > 0:
                    position -= 1
                    f.seek(position)
                    char = f.read(1)
                    if char == '\n':
                        if line:
                            # 解析日志行，提取时间
                            log_time = WAFOverviewService._parse_waf_log_time(line)
                            if log_time:
                                if start_time <= log_time <= end_time:
                                    count += 1
                                elif log_time < start_time:
                                    # 已经超出时间范围，停止读取
                                    break
                            line = ''
                    else:
                        line = char + line
                
                # 处理最后一行
                if line:
                    log_time = WAFOverviewService._parse_waf_log_time(line)
                    if log_time and start_time <= log_time <= end_time:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计时间范围内拦截数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _count_recent_requests(seconds: int) -> int:
        """统计最近指定秒数的请求数
        
        Args:
            seconds: 统计的时间范围（秒）
            
        Returns:
            最近指定秒数的请求数
        """
        try:
            if not os.path.exists(settings.WAF_ACCESS_LOG_PATH):
                return 0
            
            # 计算时间范围（使用带时区的时间）
            now = datetime.now()
            start_time = now - timedelta(seconds=seconds)
            
            count = 0
            
            # 读取访问日志文件
            with open(settings.WAF_ACCESS_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                # 从文件末尾开始读取，提高效率
                f.seek(0, os.SEEK_END)
                position = f.tell()
                line = ''
                
                # 倒序读取文件
                while position > 0:
                    position -= 1
                    f.seek(position)
                    char = f.read(1)
                    if char == '\n':
                        if line:
                            # 解析日志行，提取时间
                            log_time = WAFOverviewService._parse_log_time(line)
                            if log_time:
                                # 将带时区的时间转换为不带时区的时间进行比较
                                log_time_naive = log_time.replace(tzinfo=None)
                                if log_time_naive >= start_time:
                                    count += 1
                                elif log_time_naive < start_time:
                                    # 已经超出时间范围，停止读取
                                    break
                            line = ''
                    else:
                        line = char + line
                
                # 处理最后一行
                if line:
                    log_time = WAFOverviewService._parse_log_time(line)
                    if log_time:
                        log_time_naive = log_time.replace(tzinfo=None)
                        if log_time_naive >= start_time:
                            count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计最近请求数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _count_total_requests() -> int:
        """统计总访问请求数
        
        Returns:
            总访问请求数
        """
        try:
            if not os.path.exists(settings.WAF_ACCESS_LOG_PATH):
                return 0
            
            count = 0
            
            # 读取访问日志文件，统计行数
            with open(settings.WAF_ACCESS_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计总访问请求数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _count_total_blocks() -> int:
        """统计总拦截请求数
        
        Returns:
            总拦截请求数
        """
        try:
            if not os.path.exists(settings.WAF_LOG_PATH):
                return 0
            
            count = 0
            
            # 读取WAF日志文件，统计拦截记录
            with open(settings.WAF_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计总拦截请求数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _count_recent_blocks(seconds: int) -> int:
        """统计最近指定秒数的拦截数
        
        Args:
            seconds: 统计的时间范围（秒）
            
        Returns:
            最近指定秒数的拦截数
        """
        try:
            if not os.path.exists(settings.WAF_LOG_PATH):
                return 0
            
            # 计算时间范围
            now = datetime.now()
            start_time = now - timedelta(seconds=seconds)
            
            count = 0
            
            # 读取WAF日志文件
            with open(settings.WAF_LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                # 从文件末尾开始读取，提高效率
                f.seek(0, os.SEEK_END)
                position = f.tell()
                line = ''
                
                # 倒序读取文件
                while position > 0:
                    position -= 1
                    f.seek(position)
                    char = f.read(1)
                    if char == '\n':
                        if line:
                            # 解析日志行，提取时间
                            log_time = WAFOverviewService._parse_waf_log_time(line)
                            if log_time:
                                if log_time >= start_time:
                                    count += 1
                                elif log_time < start_time:
                                    # 已经超出时间范围，停止读取
                                    break
                            line = ''
                    else:
                        line = char + line
                
                # 处理最后一行
                if line:
                    log_time = WAFOverviewService._parse_waf_log_time(line)
                    if log_time and log_time >= start_time:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计最近拦截数失败: {str(e)}")
            return 0
    
    @staticmethod
    def _parse_waf_log_time(log_line: str) -> datetime:
        """解析WAF日志行中的时间

        Args:
            log_line: 日志行

        Returns:
            解析出的时间对象，如果解析失败则返回None
        """
        try:
            line = log_line.strip()
            if not line or not line.startswith('{'):
                return None
            import json
            log_data = json.loads(line)
            if 'timestamp' in log_data:
                return datetime.fromtimestamp(log_data['timestamp'])
            return None
        except Exception as e:
            logger.error(f"解析WAF日志时间失败: {str(e)}")
            return None
    
    @staticmethod
    def _parse_log_time(log_line: str) -> datetime:
        """解析日志行中的时间

        Args:
            log_line: 日志行

        Returns:
            解析出的时间对象，如果解析失败则返回None
        """
        try:
            # 匹配Nginx访问日志的时间格式：[04/Apr/2026:12:34:56 +0000]
            match = re.search(r'\[(\d+/\w+/\d+:\d+:\d+:\d+\s+[+-]\d+)\]', log_line)
            if match:
                time_str = match.group(1)
                # 解析时间字符串
                log_time = datetime.strptime(time_str, '%d/%b/%Y:%H:%M:%S %z')
                return log_time
            return None
        except Exception as e:
            logger.error(f"解析日志时间失败: {str(e)}")
            return None

    @staticmethod
    def get_location_stats() -> Dict[str, any]:
        """获取访问/拦截日志的地点统计

        Returns:
            包含地点统计的字典
        """
        try:
            from collections import Counter
            from app.waf.schemas import LocationStatItem

            waf_location_counter = Counter()
            access_location_counter = Counter()

            waf_log_path = settings.WAF_LOG_PATH
            access_log_path = settings.WAF_ACCESS_LOG_PATH


            # 解析WAF日志获取地点统计
            if os.path.exists(waf_log_path):
                with open(waf_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if not line.strip() or not line.startswith('{'):
                            continue
                        try:
                            import json
                            log_data = json.loads(line.strip())
                            geoip = log_data.get('geoip', {})
                            country_name = geoip.get('country', 'Unknown')
                            waf_location_counter[country_name] += 1
                        except json.JSONDecodeError:
                            continue
            else:
                logger.warning(f"WAF日志文件不存在: {waf_log_path}")

            # 解析访问日志获取地点统计（需要GeoIP解析）
            if os.path.exists(access_log_path):
                # 尝试导入GeoIP库
                try:
                    import geoip2.database
                    import geoip2.models
                    geoip_reader = None
                    geoip_paths = [
                        './data/GeoLite2-City.mmdb',
                        '/opt/blackpotbpanel-v2/server/waf/geoip/GeoLite2-City.mmdb',
                        '/usr/share/GeoIP/GeoLite2-City.mmdb'
                    ]
                    for path in geoip_paths:
                        if os.path.exists(path):
                            geoip_reader = geoip2.database.Reader(path)
                            break

                    if geoip_reader:
                        with open(access_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if not line.strip():
                                    continue
                                # 提取IP地址
                                ip_match = re.match(r'^([\d.]+)', line)
                                if ip_match:
                                    ip = ip_match.group(1)
                                    try:
                                        response = geoip_reader.city(ip)
                                        country_name = response.country.name or 'Unknown'
                                        access_location_counter[country_name] += 1
                                    except Exception:
                                        access_location_counter['Unknown'] += 1
                        geoip_reader.close()
                    else:
                        # 如果没有GeoIP数据库，返回空统计
                        logger.warning("GeoIP database not found, access logs location stats will be empty")
                except ImportError:
                    logger.warning("geoip2 library not installed, access logs location stats will be empty")
            else:
                logger.warning(f"访问日志文件不存在: {access_log_path}")

            # 转换为响应格式
            waf_logs = [
                LocationStatItem(location=location, count=count)
                for location, count in waf_location_counter.most_common()
            ]
            access_logs = [
                LocationStatItem(location=location, count=count)
                for location, count in access_location_counter.most_common()
            ]

            return {
                "waf_logs": waf_logs,
                "access_logs": access_logs,
                "message": "success get location stats"
            }

        except Exception as e:
            logger.error(f"获取地点统计失败: {str(e)}")
            return {
                "waf_logs": [],
                "access_logs": [],
                "message": f"error: {str(e)}"
            }
