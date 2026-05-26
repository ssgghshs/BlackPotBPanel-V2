import os
import json
import logging
from typing import List, Optional
from fastapi import HTTPException
from config.settings import settings
from app.waf.schemas import WAFLogEntry, WAFLogListResponse, WAFBotLogEntry, WAFBotLogListResponse, WAFLogCleanResponse, WAFBlackWhiteLogEntry, WAFBlackWhiteLogListResponse, WAFOverviewResponse

logger = logging.getLogger(__name__)


class WAFLogService:
    """WAF日志服务类"""
    
    @staticmethod
    async def get_waf_logs(skip: int = 0, limit: int = 100) -> WAFLogListResponse:
        """获取WAF拦截日志
        
        Args:
            skip: 跳过的日志条数
            limit: 返回的日志条数
            
        Returns:
            WAFLogListResponse: 包含日志列表和总数的响应对象
        """
        try:
            log_path = settings.WAF_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFLogListResponse(
                    logs=[],
                    total=0,
                    message="waf log file not found"
                )
            
            logs = []
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        
                        geoip_data = log_entry.get('geoip', {})
                        geoip_info = {
                            'country_code': geoip_data.get('country_code', 'Unknown'),
                            'city': geoip_data.get('city', 'Unknown'),
                            'country': geoip_data.get('country', 'Unknown'),
                            'latitude': geoip_data.get('latitude'),
                            'longitude': geoip_data.get('longitude'),
                            'location': geoip_data.get('location', 'Unknown, Unknown')
                        }
                        
                        waf_log = WAFLogEntry(
                            attack_type=log_entry.get('attack_type', ''),
                            reason=log_entry.get('reason', ''),
                            action=log_entry.get('action', ''),
                            client_ip=log_entry.get('client_ip', ''),
                            user_agent=log_entry.get('user_agent'),
                            request_uri=log_entry.get('request_uri', ''),
                            request_method=log_entry.get('request_method', ''),
                            application=log_entry.get('application', ''),
                            timestamp=log_entry.get('timestamp', 0.0),
                            datetime=log_entry.get('datetime', ''),
                            geoip=geoip_info
                        )
                        
                        logs.append(waf_log)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析日志行失败: {line}, 错误: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"处理日志条目失败: {line}, 错误: {str(e)}")
                        continue
            
            total = len(logs)
            
            logs.reverse()
            
            paginated_logs = logs[skip:skip + limit]
            
            return WAFLogListResponse(
                logs=paginated_logs,
                total=total,
                message="success get waf logs"
            )
            
        except Exception as e:
            logger.error(f"获取WAF日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"get waf logs failed: {str(e)}"
            )
    
    @staticmethod
    async def get_waf_bot_logs(skip: int = 0, limit: int = 100) -> WAFBotLogListResponse:
        """获取WAF BOT验证日志
        
        Args:
            skip: 跳过的日志条数
            limit: 返回的日志条数
            
        Returns:
            WAFBotLogListResponse: 包含BOT日志列表和总数的响应对象
        """
        try:
            log_path = settings.WAF_BOT_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFBotLogListResponse(
                    logs=[],
                    total=0,
                    message="waf bot log file not found"
                )
            
            logs = []
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        
                        geoip_data = log_entry.get('geoip', {})
                        geoip_info = {
                            'country_code': geoip_data.get('country_code', 'Unknown'),
                            'city': geoip_data.get('city', 'Unknown'),
                            'country': geoip_data.get('country', 'Unknown'),
                            'latitude': geoip_data.get('latitude'),
                            'longitude': geoip_data.get('longitude'),
                            'location': geoip_data.get('location', 'Unknown, Unknown')
                        }
                        
                        bot_log = WAFBotLogEntry(
                            action=log_entry.get('action', ''),
                            client_ip=log_entry.get('client_ip', ''),
                            user_agent=log_entry.get('user_agent'),
                            request_uri=log_entry.get('request_uri', ''),
                            request_method=log_entry.get('request_method', ''),
                            application_url=log_entry.get('application_url', ''),
                            verify_mode=log_entry.get('verify_mode', ''),
                            verification_status=log_entry.get('verification_status', ''),
                            timestamp=log_entry.get('timestamp', 0.0),
                            datetime=log_entry.get('datetime', ''),
                            geoip=geoip_info
                        )
                        
                        logs.append(bot_log)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析BOT日志行失败: {line}, 错误: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"处理BOT日志条目失败: {line}, 错误: {str(e)}")
                        continue
            
            total = len(logs)
            
            logs.reverse()
            
            paginated_logs = logs[skip:skip + limit]
            
            return WAFBotLogListResponse(
                logs=paginated_logs,
                total=total,
                message="success get waf bot logs"
            )
            
        except Exception as e:
            logger.error(f"获取WAF BOT日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"get waf bot logs failed: {str(e)}"
            )
    
    @staticmethod
    async def get_waf_blackwhite_logs(skip: int = 0, limit: int = 100) -> WAFBlackWhiteLogListResponse:
        """获取WAF黑白名单日志
        
        Args:
            skip: 跳过的日志条数
            limit: 返回的日志条数
            
        Returns:
            WAFBlackWhiteLogListResponse: 包含黑白名单日志列表和总数的响应对象
        """
        try:
            log_path = settings.WAF_BLACKWHITE_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFBlackWhiteLogListResponse(
                    logs=[],
                    total=0,
                    message="waf blackwhite log file not found"
                )
            
            logs = []
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        
                        geoip_data = log_entry.get('geoip', {})
                        geoip_info = {
                            'country_code': geoip_data.get('country_code', 'Unknown'),
                            'city': geoip_data.get('city', 'Unknown'),
                            'country': geoip_data.get('country', 'Unknown'),
                            'latitude': geoip_data.get('latitude'),
                            'longitude': geoip_data.get('longitude'),
                            'location': geoip_data.get('location', 'Unknown, Unknown')
                        }
                        
                        blackwhite_log = WAFBlackWhiteLogEntry(
                            action=log_entry.get('action', ''),
                            client_ip=log_entry.get('client_ip', ''),
                            user_agent=log_entry.get('user_agent'),
                            application_url=log_entry.get('application_url', ''),
                            group=log_entry.get('group'),
                            timestamp=log_entry.get('timestamp', 0.0),
                            datetime=log_entry.get('datetime', ''),
                            geoip=geoip_info
                        )
                        
                        logs.append(blackwhite_log)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析黑白名单日志行失败: {line}, 错误: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"处理黑白名单日志条目失败: {line}, 错误: {str(e)}")
                        continue
            
            total = len(logs)
            
            logs.reverse()
            
            paginated_logs = logs[skip:skip + limit]
            
            return WAFBlackWhiteLogListResponse(
                logs=paginated_logs,
                total=total,
                message="success get waf blackwhite logs"
            )
            
        except Exception as e:
            logger.error(f"获取WAF黑白名单日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"get waf blackwhite logs failed: {str(e)}"
            )
    
    @staticmethod
    async def clean_waf_logs(days: Optional[int] = None) -> WAFLogCleanResponse:
        """清理WAF拦截日志
        
        Args:
            days: 保留最近的天数，不指定则清空所有日志
            
        Returns:
            WAFLogCleanResponse: 清理结果响应对象
        """
        try:
            log_path = settings.WAF_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFLogCleanResponse(
                    message="waf log file not found"
                )
            
            if days is None:
                # 清空所有日志
                open(log_path, 'w').close()
                return WAFLogCleanResponse(
                    message="success clean all waf logs"
                )
            else:
                # 保留最近指定天数的日志
                import datetime
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
                cutoff_timestamp = cutoff_time.timestamp()
                
                preserved_logs = []
                
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            if log_entry.get('timestamp', 0.0) >= cutoff_timestamp:
                                preserved_logs.append(line)
                        except json.JSONDecodeError:
                            # 跳过解析失败的行
                            continue
                
                # 写回保留的日志
                with open(log_path, 'w', encoding='utf-8') as f:
                    for log in preserved_logs:
                        f.write(log + '\n')
                
                return WAFLogCleanResponse(
                    message=f"success clean waf logs, preserved logs from last {days} days"
                )
                
        except Exception as e:
            logger.error(f"清理WAF日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"clean waf logs failed: {str(e)}"
            )
    
    @staticmethod
    async def clean_waf_bot_logs(days: Optional[int] = None) -> WAFLogCleanResponse:
        """清理WAF BOT验证日志
        
        Args:
            days: 保留最近的天数，不指定则清空所有日志
            
        Returns:
            WAFLogCleanResponse: 清理结果响应对象
        """
        try:
            log_path = settings.WAF_BOT_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFLogCleanResponse(
                    message="waf bot log file not found"
                )
            
            if days is None:
                # 清空所有日志
                open(log_path, 'w').close()
                return WAFLogCleanResponse(
                    message="success clean all waf bot logs"
                )
            else:
                # 保留最近指定天数的日志
                import datetime
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
                cutoff_timestamp = cutoff_time.timestamp()
                
                preserved_logs = []
                
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            if log_entry.get('timestamp', 0.0) >= cutoff_timestamp:
                                preserved_logs.append(line)
                        except json.JSONDecodeError:
                            # 跳过解析失败的行
                            continue
                
                # 写回保留的日志
                with open(log_path, 'w', encoding='utf-8') as f:
                    for log in preserved_logs:
                        f.write(log + '\n')
                
                return WAFLogCleanResponse(
                    message=f"success clean waf bot logs, preserved logs from last {days} days"
                )
                
        except Exception as e:
            logger.error(f"清理WAF BOT日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"clean waf bot logs failed: {str(e)}"
            )
    
    @staticmethod
    async def clean_waf_blackwhite_logs(days: Optional[int] = None) -> WAFLogCleanResponse:
        """清理WAF黑白名单日志
        
        Args:
            days: 保留最近的天数，不指定则清空所有日志
            
        Returns:
            WAFLogCleanResponse: 清理结果响应对象
        """
        try:
            log_path = settings.WAF_BLACKWHITE_LOG_PATH
            
            if not os.path.exists(log_path):
                return WAFLogCleanResponse(
                    message="waf blackwhite log file not found"
                )
            
            if days is None:
                # 清空所有日志
                open(log_path, 'w').close()
                return WAFLogCleanResponse(
                    message="success clean all waf blackwhite logs"
                )
            else:
                # 保留最近指定天数的日志
                import datetime
                cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days)
                cutoff_timestamp = cutoff_time.timestamp()
                
                preserved_logs = []
                
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            if log_entry.get('timestamp', 0.0) >= cutoff_timestamp:
                                preserved_logs.append(line)
                        except json.JSONDecodeError:
                            # 跳过解析失败的行
                            continue
                
                # 写回保留的日志
                with open(log_path, 'w', encoding='utf-8') as f:
                    for log in preserved_logs:
                        f.write(log + '\n')
                
                return WAFLogCleanResponse(
                    message=f"success clean waf blackwhite logs, preserved logs from last {days} days"
                )
                
        except Exception as e:
            logger.error(f"清理WAF黑白名单日志失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"clean waf blackwhite logs failed: {str(e)}"
            )
    
    @staticmethod
    async def get_waf_overview() -> WAFOverviewResponse:
        """获取WAF基本概况
        
        Returns:
            WAFOverviewResponse: 包含各种日志统计信息的响应对象
        """
        try:
            # 访问日志统计
            access_logs = await WAFLogService._get_access_logs_stats()
            
            # WAF拦截日志统计
            waf_logs = await WAFLogService._get_waf_logs_stats()
            
            # 黑白名单日志统计
            blackwhite_logs = await WAFLogService._get_blackwhite_logs_stats()
            
            # BOT验证日志统计
            bot_logs = await WAFLogService._get_bot_logs_stats()
            
            return WAFOverviewResponse(
                access_logs=access_logs,
                waf_logs=waf_logs,
                blackwhite_logs=blackwhite_logs,
                bot_logs=bot_logs,
                message="success get waf overview"
            )
            
        except Exception as e:
            logger.error(f"获取WAF基本概况失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"get waf overview failed: {str(e)}"
            )
    
    @staticmethod
    async def _get_access_logs_stats() -> dict:
        """获取访问日志统计
        
        Returns:
            dict: 包含请求次数和错误次数的字典
        """
        try:
            import json
            from config.settings import settings
            
            # 读取access.json配置文件
            access_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "access.json")
            access_log_path = ""
            error_log_path = ""
            
            if os.path.exists(access_config_path):
                with open(access_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    access_log_path = config.get('access_log_path', '')
                    error_log_path = config.get('error_log_path', '')
            
            # 统计访问日志请求次数
            request_count = 0
            if access_log_path and os.path.exists(access_log_path):
                with open(access_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.strip():
                            request_count += 1
            
            # 统计错误日志错误次数
            error_count = 0
            if error_log_path and os.path.exists(error_log_path):
                with open(error_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if line.strip():
                            error_count += 1
            
            return {
                "request_count": request_count,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error(f"获取访问日志统计失败: {str(e)}")
            return {
                "request_count": 0,
                "error_count": 0
            }
    
    @staticmethod
    async def _get_waf_logs_stats() -> dict:
        """获取WAF拦截日志统计
        
        Returns:
            dict: 包含拦截次数、攻击IP数、记录次数的字典
        """
        try:
            log_path = settings.WAF_LOG_PATH
            
            if not os.path.exists(log_path):
                return {
                    "block_count": 0,
                    "attack_ip_count": 0,
                    "record_count": 0
                }
            
            block_count = 0
            record_count = 0
            attack_ips = set()
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        action = log_entry.get('action', '')
                        if action == 'blocked':
                            block_count += 1
                        elif action == 'record':
                            record_count += 1
                        
                        client_ip = log_entry.get('client_ip', '')
                        if client_ip:
                            attack_ips.add(client_ip)
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
            
            return {
                "block_count": block_count,
                "attack_ip_count": len(attack_ips),
                "record_count": record_count
            }
            
        except Exception as e:
            logger.error(f"获取WAF拦截日志统计失败: {str(e)}")
            return {
                "block_count": 0,
                "attack_ip_count": 0,
                "record_count": 0
            }
    
    @staticmethod
    async def _get_blackwhite_logs_stats() -> dict:
        """获取黑白名单日志统计
        
        Returns:
            dict: 包含IP黑名单拦截、记录数的字典
        """
        try:
            log_path = settings.WAF_BLACKWHITE_LOG_PATH
            
            if not os.path.exists(log_path):
                return {
                    "block_count": 0,
                    "record_count": 0
                }
            
            block_count = 0
            record_count = 0
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        action = log_entry.get('action', '')
                        if action == 'block':
                            block_count += 1
                        elif action == 'allow':
                            record_count += 1
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
            
            return {
                "block_count": block_count,
                "record_count": record_count
            }
            
        except Exception as e:
            logger.error(f"获取黑白名单日志统计失败: {str(e)}")
            return {
                "block_count": 0,
                "record_count": 0
            }
    
    @staticmethod
    async def _get_bot_logs_stats() -> dict:
        """获取BOT验证日志统计
        
        Returns:
            dict: 包含验证、挑战、失败数量的字典
        """
        try:
            log_path = settings.WAF_BOT_LOG_PATH
            
            if not os.path.exists(log_path):
                return {
                    "verified_count": 0,
                    "challenge_count": 0,
                    "failed_count": 0
                }
            
            verified_count = 0
            challenge_count = 0
            failed_count = 0
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        verification_status = log_entry.get('verification_status', '')
                        if verification_status == 'passed':
                            verified_count += 1
                        elif verification_status == 'triggered':
                            challenge_count += 1
                        elif verification_status == 'failed':
                            failed_count += 1
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
            
            return {
                "verified_count": verified_count,
                "challenge_count": challenge_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"获取BOT验证日志统计失败: {str(e)}")
            return {
                "verified_count": 0,
                "challenge_count": 0,
                "failed_count": 0
            }
