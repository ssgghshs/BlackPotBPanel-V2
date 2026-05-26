import logging
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from datetime import datetime

from app.waf.models import ThreatIntelConfig
from app.waf.rules_service import WAFRulesService

logger = logging.getLogger(__name__)


class ThreatIntelService:

    @staticmethod
    async def get_config(db: AsyncSession) -> dict:
        """获取 AbuseIPDB 配置

        永远只操作 id=1 的记录（全局单例模式）
        """
        result = await db.execute(
            select(ThreatIntelConfig).where(ThreatIntelConfig.id == 1)
        )
        config = result.scalar_one_or_none()

        if not config:
            config = ThreatIntelConfig(id=1, api_key="", enabled=False)
            db.add(config)
            await db.commit()
            await db.refresh(config)

        return {
            "id": config.id,
            "api_key": config.api_key,
            "enabled": config.enabled,
            "last_sync_time": config.last_sync_time,
            "synced_ip_count": config.synced_ip_count,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    @staticmethod
    async def update_config(db: AsyncSession, api_key: str, enabled: Optional[bool]) -> dict:
        """更新 AbuseIPDB API Key 和启用状态"""
        result = await db.execute(
            select(ThreatIntelConfig).where(ThreatIntelConfig.id == 1)
        )
        config = result.scalar_one_or_none()

        if not config:
            config = ThreatIntelConfig(id=1)
            db.add(config)

        config.api_key = api_key
        if enabled is not None:
            config.enabled = enabled

        await db.commit()
        await db.refresh(config)

        return {
            "id": config.id,
            "api_key": config.api_key,
            "enabled": config.enabled,
            "last_sync_time": config.last_sync_time,
            "synced_ip_count": config.synced_ip_count,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    @staticmethod
    async def get_active_api_key(db: AsyncSession) -> Optional[str]:
        """内部使用：获取当前生效的 API Key"""
        result = await db.execute(
            select(ThreatIntelConfig).where(
                ThreatIntelConfig.id == 1,
                ThreatIntelConfig.enabled == True,
                ThreatIntelConfig.api_key != ""
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            return None
        return config.api_key

    @staticmethod
    async def test_api_key(api_key: str) -> dict:
        """测试 AbuseIPDB API Key 是否可用"""
        return await ThreatIntelService._test_abuseipdb(api_key)

    @staticmethod
    async def sync_blacklist(db: AsyncSession) -> dict:
        """同步 AbuseIPDB 黑名单到 WAF

        拉取恶意 IP 列表并写入 Intelligence Blacklist Ips 组
        """
        config_result = await db.execute(
            select(ThreatIntelConfig).where(ThreatIntelConfig.id == 1)
        )
        config = config_result.scalar_one_or_none()

        if not config or not config.enabled or not config.api_key:
            return {
                "success": False,
                "total_fetched": 0,
                "added_count": 0,
                "message": "AbuseIPDB 未启用或 API Key 未配置",
                "last_sync_time": None,
            }

        result = await ThreatIntelService._sync_abuseipdb(config.api_key)

        now = datetime.now()

        if result["success"]:
            added_ips = result.get("added_ips", [])
            if added_ips:
                await ThreatIntelService._update_blacklist_group(added_ips)

            config.last_sync_time = now
            config.synced_ip_count = len(added_ips)
            await db.commit()

            result["last_sync_time"] = now
        else:
            config.last_sync_time = now
            config.synced_ip_count = 0
            await db.commit()
            result["last_sync_time"] = now

        return result

    @staticmethod
    async def analyze_ip(db: AsyncSession, ip: str) -> dict:
        """分析指定 IP 的 AbuseIPDB 信誉"""
        config_result = await db.execute(
            select(ThreatIntelConfig).where(ThreatIntelConfig.id == 1)
        )
        config = config_result.scalar_one_or_none()

        if not config or not config.enabled or not config.api_key:
            return {
                "success": False,
                "ip": ip,
                "data": None,
                "message": "AbuseIPDB 未启用或 API Key 未配置",
            }

        result = await ThreatIntelService._analyze_ip_abuseipdb(config.api_key, ip)

        return {
            "success": result["success"],
            "ip": ip,
            "data": result.get("data"),
            "message": result["message"],
        }

    @staticmethod
    async def _sync_abuseipdb(api_key: str) -> dict:
        """从 AbuseIPDB 同步黑名单"""
        url = "https://api.abuseipdb.com/api/v2/blacklist"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params={
                    "confidenceMinimum": 90,
                    "limit": 10000,
                }, headers={
                    "Key": api_key,
                    "Accept": "application/json",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    ips = [item["ipAddress"] for item in data.get("data", []) if item.get("ipAddress")]
                    return {
                        "success": True,
                        "total_fetched": len(ips),
                        "added_count": len(ips),
                        "added_ips": ips,
                        "message": f"成功从 AbuseIPDB 获取 {len(ips)} 个恶意 IP",
                    }
                elif resp.status_code in (401, 403):
                    return {
                        "success": False,
                        "total_fetched": 0,
                        "added_count": 0,
                        "added_ips": [],
                        "message": "API Key 无效，鉴权失败",
                    }
                else:
                    return {
                        "success": False,
                        "total_fetched": 0,
                        "added_count": 0,
                        "added_ips": [],
                        "message": f"请求失败，HTTP 状态码: {resp.status_code}",
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "total_fetched": 0,
                "added_count": 0,
                "added_ips": [],
                "message": "请求超时，请检查网络连接",
            }
        except Exception as e:
            logger.error(f"同步 AbuseIPDB 黑名单失败: {str(e)}")
            return {
                "success": False,
                "total_fetched": 0,
                "added_count": 0,
                "added_ips": [],
                "message": f"同步异常: {str(e)}",
            }

    @staticmethod
    async def _update_blacklist_group(ips: list) -> None:
        """将 IP 列表写入 WAF 的 Intelligence Blacklist Ips 组"""
        try:
            result = WAFRulesService.update_blackwhite_group(
                "black", "Intelligence Blacklist Ips",
                {"ips": ips, "enabled": True, "description": "AbuseIPDB 同步的恶意 IP"}
            )
            if result.message != "success get blackwhite list":
                logger.warning(f"更新黑名单组返回异常: {result.message}")
        except Exception as e:
            logger.error(f"更新 Intelligence Blacklist Ips 失败: {str(e)}")
            raise

    @staticmethod
    async def _analyze_ip_abuseipdb(api_key: str, ip: str) -> dict:
        """查询 AbuseIPDB IP 信誉详情"""
        url = "https://api.abuseipdb.com/api/v2/check"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params={
                    "ipAddress": ip,
                    "maxAgeInDays": 365,
                }, headers={
                    "Key": api_key,
                    "Accept": "application/json",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "data": data.get("data"),
                        "message": "查询成功",
                    }
                elif resp.status_code in (401, 403):
                    return {
                        "success": False,
                        "data": None,
                        "message": "API Key 无效，鉴权失败",
                    }
                else:
                    error_detail = ""
                    try:
                        error_data = resp.json()
                        errors = error_data.get("errors", [])
                        if errors:
                            error_detail = errors[0].get("detail", "")
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "data": None,
                        "message": f"请求失败: {error_detail}" if error_detail else f"HTTP 状态码: {resp.status_code}",
                    }
        except httpx.TimeoutException:
            return {
                "success": False,
                "data": None,
                "message": "请求超时，请检查网络连接",
            }
        except Exception as e:
            logger.error(f"AbuseIPDB IP 查询失败: {str(e)}")
            return {
                "success": False,
                "data": None,
                "message": f"查询异常: {str(e)}",
            }

    @staticmethod
    async def _test_abuseipdb(api_key: str) -> dict:
        """测试 AbuseIPDB API Key"""
        test_url = "https://api.abuseipdb.com/api/v2/check"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(test_url, params={
                    "ipAddress": "8.8.8.8",
                    "maxAgeInDays": 30
                }, headers={
                    "Key": api_key,
                    "Accept": "application/json"
                })
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data:
                        return {"success": True, "message": "AbuseIPDB API Key 验证成功"}
                    errors = data.get("errors", [])
                    if errors:
                        detail = errors[0].get("detail", "")
                        return {"success": False, "message": f"API 返回错误: {detail}"}
                    return {"success": False, "message": "API 返回格式异常"}
                elif resp.status_code in (401, 403):
                    return {"success": False, "message": "API Key 无效，鉴权失败"}
                else:
                    return {"success": False, "message": f"请求失败，HTTP 状态码: {resp.status_code}"}
        except httpx.TimeoutException:
            return {"success": False, "message": "请求超时，请检查网络连接"}
        except Exception as e:
            logger.error(f"测试 AbuseIPDB API 失败: {str(e)}")
            return {"success": False, "message": f"测试请求异常: {str(e)}"}
