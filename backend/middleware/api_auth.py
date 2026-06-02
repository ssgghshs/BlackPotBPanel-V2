import hashlib
import json
import os
import time
import ipaddress
from fastapi import Request
from fastapi.responses import JSONResponse
from config.settings import settings

API_CONFIG_PATH = settings.API_CONFIG_PATH


def _read_api_config() -> dict:
    """从 api.json 读取 API 接口配置"""
    defaults = {
        "API_KEY": "",
        "API_IP_WHITELIST": "127.0.0.1",
        "API_KEY_VALIDITY_TIME": 0
    }
    path = API_CONFIG_PATH
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k in defaults:
                        if k in data:
                            defaults[k] = data[k]
        except (json.JSONDecodeError, IOError):
            pass
    return defaults


def _write_api_config(config: dict) -> None:
    """写入 API 接口配置到 api.json"""
    path = API_CONFIG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def generate_api_key() -> str:
    """生成 32 位随机 API 密钥"""
    import secrets
    return secrets.token_hex(16)


def _is_valid_timestamp(timestamp_str: str, validity_minutes: int) -> bool:
    """验证时间戳是否在有效期内"""
    try:
        ts = int(timestamp_str)
    except (ValueError, TypeError):
        return False
    now = int(time.time())
    tolerance = 60
    if ts > now + tolerance:
        return False
    if validity_minutes == 0:
        return True
    return (now - ts) <= (validity_minutes * 60 + tolerance)


def _is_valid_token(token: str, api_key: str, timestamp_str: str) -> bool:
    """验证 Token 签名：md5('blackpotbpanel' + api_key + timestamp)"""
    raw = f"blackpotbpanel{api_key}{timestamp_str}"
    expected = hashlib.md5(raw.encode()).hexdigest()
    return token == expected


def _is_ip_in_whitelist(client_ip: str, whitelist_str: str) -> bool:
    """检查客户端 IP 是否在白名单中"""
    if not whitelist_str:
        return False
    parts = [p.strip() for p in whitelist_str.split(",") if p.strip()]
    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in parts:
        try:
            network = ipaddress.ip_network(entry, strict=False)
            if client_addr in network:
                return True
        except ValueError:
            continue
    return False


async def api_auth_middleware(request: Request, call_next):
    """API 接口访问认证中间件

    请求头含 Blackpotbpanel-Token / Blackpotbpanel-Timestamp 时走 API Key 认证，
    否则跳过，交由后续 JWT 认证处理。
    """
    token = request.headers.get("Blackpotbpanel-Token")
    timestamp = request.headers.get("Blackpotbpanel-Timestamp")

    if not token and not timestamp:
        return await call_next(request)

    # 排除用户管理相关接口（登录、注册等），仅允许 JWT Session 访问
    if request.url.path.startswith("/api/v2/users"):
        return await call_next(request)

    if not settings.API_OPEN:
        return JSONResponse(
            status_code=401,
            content={"detail": "API interface is disabled"}
        )

    api_config = _read_api_config()
    api_key = api_config.get("API_KEY", "")
    validity = int(api_config.get("API_KEY_VALIDITY_TIME", 0))
    whitelist = api_config.get("API_IP_WHITELIST", "")

    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "API key not configured"}
        )

    if not _is_valid_timestamp(timestamp, validity):
        return JSONResponse(
            status_code=401,
            content={"detail": "Timestamp invalid or expired"}
        )

    if not _is_valid_token(token, api_key, timestamp):
        return JSONResponse(
            status_code=401,
            content={"detail": "API key signature invalid"}
        )

    client_ip = request.client.host if request.client else "0.0.0.0"
    if not _is_ip_in_whitelist(client_ip, whitelist):
        return JSONResponse(
            status_code=401,
            content={"detail": "Client IP not allowed"}
        )

    request.state.api_authed = True
    return await call_next(request)
