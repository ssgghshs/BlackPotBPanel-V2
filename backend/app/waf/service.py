import os
import re
import json
import logging
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.waf import models
from app.waf.manager_service import WAFManagerService
from config.settings import settings
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_ssl_cert(pem_content: str) -> Tuple[Optional[str], Optional[str], Optional[datetime]]:
    """
    解析SSL证书内容，提取域名、颁发者和到期时间
    
    Args:
        pem_content: SSL证书PEM格式内容
    
    Returns:
        Tuple[domain, issuer, expiry_date]: 域名、颁发者、到期时间
    """
    try:
        cert = x509.load_pem_x509_certificate(pem_content.encode(), default_backend())
        
        # 获取域名（从Subject的CommonName或Subject Alternative Names）
        domain = None
        try:
            common_name = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            if common_name:
                domain = common_name[0].value
        except Exception:
            pass
        
        # 获取颁发者
        issuer = None
        try:
            issuer_name = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
            if issuer_name:
                issuer = issuer_name[0].value
            else:
                # 如果没有组织名称，尝试使用Common Name
                issuer_cn = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                if issuer_cn:
                    issuer = issuer_cn[0].value
        except Exception:
            pass
        
        # 获取到期时间
        expiry_date = cert.not_valid_after
        
        return domain, issuer, expiry_date
    except Exception as e:
        logger.error(f"解析SSL证书失败: {e}")
        return None, None, None


async def create_ssl_cert(
    db: AsyncSession,
    name: str,
    key: str,
    pem: str
) -> models.SSLCert:
    """
    创建SSL证书
    
    Args:
        db: 数据库会话
        name: SSL证书名称
        key: SSL私钥内容
        pem: SSL证书内容(PEM格式)
    
    Returns:
        models.SSLCert: 创建的SSL证书对象
    
    Raises:
        Exception: 当证书名称已存在或文件操作失败时抛出异常
    """
    try:
        # 检查证书名称是否已存在
        result = await db.execute(
            select(models.SSLCert).where(models.SSLCert.name == name)
        )
        existing_cert = result.scalar_one_or_none()
        
        if existing_cert:
            raise Exception(f"SSL证书名称 '{name}' 已存在")
        
        # 解析SSL证书，获取域名、颁发者和到期时间
        domain, issuer, expiry_date = parse_ssl_cert(pem)
        
        # 创建SSL证书文件夹
        ssl_base_path = settings.WEBSITE_SSL_PATH
        cert_dir = os.path.join(ssl_base_path, name)
        
        # 确保基础路径存在
        if not os.path.exists(ssl_base_path):
            os.makedirs(ssl_base_path, exist_ok=True)
            logger.info(f"创建SSL基础目录: {ssl_base_path}")
        
        # 创建证书目录
        if not os.path.exists(cert_dir):
            os.makedirs(cert_dir, exist_ok=True)
            logger.info(f"创建SSL证书目录: {cert_dir}")
        else:
            raise Exception(f"SSL证书目录 '{name}' 已存在")
        
        # 生成.key文件
        key_file_path = os.path.join(cert_dir, f"{name}.key")
        with open(key_file_path, "w", encoding="utf-8") as f:
            f.write(key)
        logger.info(f"创建SSL私钥文件: {key_file_path}")
        
        # 生成.pem文件
        pem_file_path = os.path.join(cert_dir, f"{name}.pem")
        with open(pem_file_path, "w", encoding="utf-8") as f:
            f.write(pem)
        logger.info(f"创建SSL证书文件: {pem_file_path}")
        
        # 创建数据库记录
        db_cert = models.SSLCert(name=name, domain=domain, issuer=issuer, expiry_date=expiry_date)
        db.add(db_cert)
        await db.commit()
        await db.refresh(db_cert)
        
        logger.info(f"成功创建SSL证书: {name}")
        return db_cert
        
    except Exception as e:
        logger.error(f"创建SSL证书失败: {e}")
        # 如果创建文件失败，清理已创建的文件和目录
        try:
            if os.path.exists(cert_dir):
                key_file = os.path.join(cert_dir, f"{name}.key")
                pem_file = os.path.join(cert_dir, f"{name}.pem")
                if os.path.exists(key_file):
                    os.remove(key_file)
                if os.path.exists(pem_file):
                    os.remove(pem_file)
                os.rmdir(cert_dir)
                logger.info(f"清理失败的SSL证书目录: {cert_dir}")
        except Exception as cleanup_error:
            logger.error(f"清理SSL证书目录失败: {cleanup_error}")
        
        raise Exception(f"创建SSL证书失败: {str(e)}")


async def get_ssl_cert(db: AsyncSession, cert_id: int) -> Optional[models.SSLCert]:
    """
    获取SSL证书
    
    Args:
        db: 数据库会话
        cert_id: SSL证书ID
    
    Returns:
        Optional[models.SSLCert]: SSL证书对象，如果不存在则返回None
    """
    try:
        result = await db.execute(
            select(models.SSLCert).where(models.SSLCert.id == cert_id)
        )
        cert = result.scalar_one_or_none()
        return cert
    except Exception as e:
        logger.error(f"获取SSL证书失败: {e}")
        raise Exception(f"获取SSL证书失败: {str(e)}")


async def get_ssl_cert_by_name(db: AsyncSession, name: str) -> Optional[models.SSLCert]:
    """
    根据名称获取SSL证书
    
    Args:
        db: 数据库会话
        name: SSL证书名称
    
    Returns:
        Optional[models.SSLCert]: SSL证书对象，如果不存在则返回None
    """
    try:
        result = await db.execute(
            select(models.SSLCert).where(models.SSLCert.name == name)
        )
        cert = result.scalar_one_or_none()
        return cert
    except Exception as e:
        logger.error(f"获取SSL证书失败: {e}")
        raise Exception(f"获取SSL证书失败: {str(e)}")


async def get_ssl_certs(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.SSLCert]:
    """
    获取SSL证书列表
    
    Args:
        db: 数据库会话
        skip: 跳过的记录数
        limit: 返回的最大记录数
    
    Returns:
        List[models.SSLCert]: SSL证书列表
    """
    try:
        result = await db.execute(
            select(models.SSLCert).offset(skip).limit(limit)
        )
        certs = result.scalars().all()
        return list(certs)
    except Exception as e:
        logger.error(f"获取SSL证书列表失败: {e}")
        raise Exception(f"获取SSL证书列表失败: {str(e)}")


async def get_ssl_certs_count(db: AsyncSession) -> int:
    """
    获取SSL证书总数
    
    Args:
        db: 数据库会话
    
    Returns:
        int: SSL证书总数
    """
    try:
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(models.SSLCert.id))
        )
        count = result.scalar()
        return count
    except Exception as e:
        logger.error(f"获取SSL证书总数失败: {e}")
        raise Exception(f"获取SSL证书总数失败: {str(e)}")


async def update_ssl_cert(
    db: AsyncSession,
    cert_id: int,
    key: Optional[str] = None,
    pem: Optional[str] = None
) -> Optional[models.SSLCert]:
    """
    更新SSL证书
    
    Args:
        db: 数据库会话
        cert_id: SSL证书ID
        key: SSL私钥内容（可选）
        pem: SSL证书内容（可选）
    
    Returns:
        Optional[models.SSLCert]: 更新后的SSL证书对象，如果不存在则返回None
    
    Raises:
        Exception: 当证书不存在或文件操作失败时抛出异常
    """
    try:
        # 获取证书
        cert = await get_ssl_cert(db, cert_id)
        if not cert:
            raise Exception(f"SSL证书ID {cert_id} 不存在")
        
        # 更新文件
        ssl_base_path = settings.WEBSITE_SSL_PATH
        cert_dir = os.path.join(ssl_base_path, cert.name)
        
        if not os.path.exists(cert_dir):
            raise Exception(f"SSL证书目录 '{cert.name}' 不存在")
        
        # 如果更新了PEM证书，重新解析证书信息
        if pem is not None:
            domain, issuer, expiry_date = parse_ssl_cert(pem)
            cert.domain = domain
            cert.issuer = issuer
            cert.expiry_date = expiry_date
        
        # 更新.key文件
        if key is not None:
            key_file_path = os.path.join(cert_dir, f"{cert.name}.key")
            with open(key_file_path, "w", encoding="utf-8") as f:
                f.write(key)
            logger.info(f"更新SSL私钥文件: {key_file_path}")
        
        # 更新.pem文件
        if pem is not None:
            pem_file_path = os.path.join(cert_dir, f"{cert.name}.pem")
            with open(pem_file_path, "w", encoding="utf-8") as f:
                f.write(pem)
            logger.info(f"更新SSL证书文件: {pem_file_path}")
        
        # 更新数据库记录
        await db.commit()
        await db.refresh(cert)
        
        logger.info(f"成功更新SSL证书: {cert.name}")
        return cert
        
    except Exception as e:
        logger.error(f"更新SSL证书失败: {e}")
        raise Exception(f"更新SSL证书失败: {str(e)}")


async def delete_ssl_cert(db: AsyncSession, cert_id: int) -> bool:
    """
    删除SSL证书
    
    Args:
        db: 数据库会话
        cert_id: SSL证书ID
    
    Returns:
        bool: 是否删除成功
    
    Raises:
        Exception: 当证书不存在或文件操作失败时抛出异常
    """
    try:
        # 获取证书
        cert = await get_ssl_cert(db, cert_id)
        if not cert:
            raise Exception(f"SSL证书ID {cert_id} 不存在")
        
        # 删除文件和目录
        ssl_base_path = settings.WEBSITE_SSL_PATH
        cert_dir = os.path.join(ssl_base_path, cert.name)
        
        if os.path.exists(cert_dir):
            key_file = os.path.join(cert_dir, f"{cert.name}.key")
            pem_file = os.path.join(cert_dir, f"{cert.name}.pem")
            
            # 删除文件
            if os.path.exists(key_file):
                os.remove(key_file)
                logger.info(f"删除SSL私钥文件: {key_file}")
            
            if os.path.exists(pem_file):
                os.remove(pem_file)
                logger.info(f"删除SSL证书文件: {pem_file}")
            
            # 删除目录
            os.rmdir(cert_dir)
            logger.info(f"删除SSL证书目录: {cert_dir}")
        
        # 删除数据库记录
        await db.delete(cert)
        await db.commit()
        
        logger.info(f"成功删除SSL证书: {cert.name}")
        return True
        
    except Exception as e:
        logger.error(f"删除SSL证书失败: {e}")
        raise Exception(f"删除SSL证书失败: {str(e)}")


async def get_ssl_cert_detail(db: AsyncSession, cert_id: int) -> Optional[dict]:
    """
    获取SSL证书详情（包含key和pem内容）
    
    Args:
        db: 数据库会话
        cert_id: SSL证书ID
    
    Returns:
        Optional[dict]: 包含证书信息和文件内容的字典，如果不存在则返回None
    """
    try:
        # 获取证书
        cert = await get_ssl_cert(db, cert_id)
        if not cert:
            return None
        
        # 读取key和pem文件内容
        ssl_base_path = settings.WEBSITE_SSL_PATH
        cert_dir = os.path.join(ssl_base_path, cert.name)
        
        key_content = None
        pem_content = None
        
        if os.path.exists(cert_dir):
            key_file_path = os.path.join(cert_dir, f"{cert.name}.key")
            pem_file_path = os.path.join(cert_dir, f"{cert.name}.pem")
            
            if os.path.exists(key_file_path):
                with open(key_file_path, "r", encoding="utf-8") as f:
                    key_content = f.read()
            
            if os.path.exists(pem_file_path):
                with open(pem_file_path, "r", encoding="utf-8") as f:
                    pem_content = f.read()
        
        return {
            "id": cert.id,
            "name": cert.name,
            "domain": cert.domain,
            "issuer": cert.issuer,
            "expiry_date": cert.expiry_date,
            "key": key_content,
            "pem": pem_content,
            "created_at": cert.created_at,
            "updated_at": cert.updated_at
        }
    except Exception as e:
        logger.error(f"获取SSL证书详情失败: {e}")
        raise Exception(f"获取SSL证书详情失败: {str(e)}")


async def get_big_screen_config() -> dict:
    """
    获取大屏配置

    Returns:
        dict: 包含大屏配置的字典

    Raises:
        Exception: 当配置文件不存在或解析失败时抛出异常
    """
    try:
        screen_path = settings.SCREEN_PATH

        if not os.path.exists(screen_path):
            default_config = {
                "title": "攻击监控大屏",
                "theme": "#0a1929",
                "screen": True
            }
            os.makedirs(os.path.dirname(screen_path), exist_ok=True)
            with open(screen_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info(f"创建默认大屏配置文件: {screen_path}")
            return default_config

        with open(screen_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        logger.error(f"解析大屏配置文件失败: {e}")
        raise Exception(f"解析大屏配置文件失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取大屏配置失败: {e}")
        raise Exception(f"获取大屏配置失败: {str(e)}")


async def update_big_screen_config(update_data: dict) -> dict:
    """
    更新大屏配置

    Args:
        update_data: 要更新的配置数据

    Returns:
        dict: 更新后的大屏配置

    Raises:
        Exception: 当配置文件写入失败时抛出异常
    """
    try:
        screen_path = settings.SCREEN_PATH

        config = await get_big_screen_config()

        if update_data.get('title') is not None:
            config['title'] = update_data['title']
        if update_data.get('theme') is not None:
            config['theme'] = update_data['theme']
        if update_data.get('screen') is not None:
            config['screen'] = update_data['screen']

        os.makedirs(os.path.dirname(screen_path), exist_ok=True)
        with open(screen_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"更新大屏配置文件: {screen_path}")

        return config
    except Exception as e:
        logger.error(f"更新大屏配置失败: {e}")
        raise Exception(f"更新大屏配置失败: {str(e)}")


def _parse_int(conf_text: str, key: str) -> int:
    m = re.search(rf'{key}\s+(\d+);', conf_text)
    return int(m.group(1)) if m else 0


def _parse_size(conf_text: str, key: str) -> str:
    m = re.search(rf'{key}\s+(\d+[kmg]?);', conf_text)
    return m.group(1) if m else ''


def _parse_bool_on(conf_text: str, key: str) -> bool:
    m = re.search(rf'{key}\s+(on|off);', conf_text)
    return m.group(1) == 'on' if m else False


def _parse_str_val(conf_text: str, key: str) -> str:
    m = re.search(rf'{key}\s+(.+);', conf_text)
    v = m.group(1).strip() if m else ''
    if v.startswith('"') and v.endswith('"'):
        v = v[1:-1]
    return v


def get_global_config() -> dict:
    """get global nginx configuration

    reads nginx.conf and extracts configurable values.
    """
    conf_path = settings.WAF_NGINX_CONF_PATH

    if not os.path.exists(conf_path):
        return {"message": "Config file not found"}

    with open(conf_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "worker_connections": _parse_int(content, 'worker_connections'),
        "keepalive_timeout": _parse_int(content, 'keepalive_timeout'),
        "client_max_body_size": _parse_size(content, 'client_max_body_size'),
        "client_body_timeout": _parse_int(content, 'client_body_timeout'),
        "client_header_timeout": _parse_int(content, 'client_header_timeout'),
        "send_timeout": _parse_int(content, 'send_timeout'),
        "gzip_enabled": _parse_bool_on(content, 'gzip'),
        "gzip_comp_level": _parse_int(content, 'gzip_comp_level'),
        "gzip_min_length": _parse_size(content, 'gzip_min_length'),
        "gzip_vary": _parse_bool_on(content, 'gzip_vary'),
        "gzip_disable": _parse_str_val(content, 'gzip_disable'),
        "sendfile": _parse_bool_on(content, 'sendfile'),
        "tcp_nopush": _parse_bool_on(content, 'tcp_nopush'),
        "tcp_nodelay": _parse_bool_on(content, 'tcp_nodelay'),
        "multi_accept": _parse_bool_on(content, 'multi_accept'),
        "proxy_intercept_errors": _parse_bool_on(content, 'proxy_intercept_errors'),
        "lua_code_cache": _parse_bool_on(content, 'lua_code_cache'),
        "message": "success get global config"
    }


async def update_global_config(update_data: dict) -> dict:
    """update global nginx configuration

    reads nginx.conf, replaces specific directives, and writes back.
    automatically restarts WAF container to apply changes.
    """
    conf_path = settings.WAF_NGINX_CONF_PATH

    if not os.path.exists(conf_path):
        return {"message": "Config file not found"}

    with open(conf_path, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = []

    if 'worker_connections' in update_data:
        replacements.append(
            (rf'worker_connections\s+\d+;', f'worker_connections  {update_data["worker_connections"]};'))
    if 'keepalive_timeout' in update_data:
        replacements.append(
            (rf'keepalive_timeout\s+\d+;', f'keepalive_timeout  {update_data["keepalive_timeout"]};'))
    if 'client_max_body_size' in update_data:
        replacements.append(
            (rf'client_max_body_size\s+\d+[kmg]?;', f'client_max_body_size  {update_data["client_max_body_size"]};'))
    if 'client_body_timeout' in update_data:
        replacements.append(
            (rf'client_body_timeout\s+\d+;', f'client_body_timeout  {update_data["client_body_timeout"]};'))
    if 'client_header_timeout' in update_data:
        replacements.append(
            (rf'client_header_timeout\s+\d+;', f'client_header_timeout  {update_data["client_header_timeout"]};'))
    if 'send_timeout' in update_data:
        replacements.append(
            (rf'send_timeout\s+\d+;', f'send_timeout  {update_data["send_timeout"]};'))
    if 'gzip_enabled' in update_data:
        val = 'on' if update_data['gzip_enabled'] else 'off'
        replacements.append((rf'gzip\s+(on|off);', f'gzip  {val};'))
    if 'gzip_comp_level' in update_data:
        replacements.append(
            (rf'gzip_comp_level\s+\d+;', f'gzip_comp_level  {update_data["gzip_comp_level"]};'))
    if 'gzip_min_length' in update_data:
        replacements.append(
            (rf'gzip_min_length\s+\d+[kmg]?;', f'gzip_min_length  {update_data["gzip_min_length"]};'))
    if 'gzip_vary' in update_data:
        val = 'on' if update_data['gzip_vary'] else 'off'
        replacements.append((rf'gzip_vary\s+(on|off);', f'gzip_vary  {val};'))
    if 'gzip_disable' in update_data:
        val = update_data['gzip_disable']
        if val and not (val.startswith('"') and val.endswith('"')):
            val = f'"{val}"'
        replacements.append(
            (rf'gzip_disable\s+[^;]+;', f'gzip_disable {val};'))
    if 'sendfile' in update_data:
        val = 'on' if update_data['sendfile'] else 'off'
        replacements.append((rf'sendfile\s+(on|off);', f'sendfile        {val};'))
    if 'tcp_nopush' in update_data:
        val = 'on' if update_data['tcp_nopush'] else 'off'
        replacements.append((rf'tcp_nopush\s+(on|off);', f'tcp_nopush      {val};'))
    if 'tcp_nodelay' in update_data:
        val = 'on' if update_data['tcp_nodelay'] else 'off'
        replacements.append((rf'tcp_nodelay\s+(on|off);', f'tcp_nodelay     {val};'))
    if 'multi_accept' in update_data:
        val = 'on' if update_data['multi_accept'] else 'off'
        replacements.append((rf'multi_accept\s+(on|off);', f'multi_accept {val};'))
    if 'proxy_intercept_errors' in update_data:
        val = 'on' if update_data['proxy_intercept_errors'] else 'off'
        replacements.append(
            (rf'proxy_intercept_errors\s+(on|off);', f'proxy_intercept_errors {val};'))
    if 'lua_code_cache' in update_data:
        val = 'on' if update_data['lua_code_cache'] else 'off'
        replacements.append(
            (rf'lua_code_cache\s+(on|off);', f'lua_code_cache {val};'))

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, count=1)

    with open(conf_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"更新nginx全局配置: {conf_path}")

    try:
        await WAFManagerService.operate_waf_container('restart')
        logger.info("Successfully restarted WAF container after updating nginx global config")
    except Exception as restart_error:
        logger.error(f"Failed to restart WAF container: {str(restart_error)}")

    return get_global_config()
