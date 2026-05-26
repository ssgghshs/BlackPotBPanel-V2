
from app.user import models as user_models
from app.host import models as host_models
from app.script import models as script_models
from app.container import models as container_models
from app.firewall import models as firewall_models
from app.database import models as database_models
from middleware.auth import get_password_hash
import logging
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from config.database import (
    engine, Base, AsyncSessionLocal, 
    script_engine, ScriptBase, 
    container_engine, ContainerBase, ContainerAsyncSessionLocal, 
    firewall_engine, FirewallBase, FirewallAsyncSessionLocal,
    waf_engine, WafBase,
    crontab_engine, CrontabTaskBase, CrontabAsyncSessionLocal,
    database_engine, DatabaseBase, DatabaseAsyncSessionLocal
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 艺术字Logo
LOGO = r"""
    __    __           __               __  __        
   / /_  / /___ ______/ /______  ____  / /_/ /_  ____ 
  / __ \/ / __ `/ ___/ //_/ __ \__ \  / __/ __ \/ __ \
 / /_/ / / /_/ / /__/ ,< / /_/ / /_/ / /_/ /_/ / /_/ /
/_.___/_/\__,_/\___/_/|_/ .___/\____/\__/_.___/ .___/
                       /_/                   /_/
"""


async def create_admin_user():
    """创建默认管理员账户"""
    # 手动创建数据库会话
    db = AsyncSessionLocal()
    try:
        # 检查是否已存在admin用户
        from sqlalchemy import select
        result = await db.execute(select(user_models.User).filter(user_models.User.username == "admin"))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            # 创建admin用户，使用较短的密码避免bcrypt限制
            admin_user = user_models.User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin@123"),
                is_active=1,
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            logger.info("Admin user created successfully!")
        else:
            logger.info("Admin user already exists.")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        await db.rollback()
    finally:
        await db.close()


async def create_localhost_host():
    """创建默认本机SSH配置"""
    # 手动创建数据库会话
    db = AsyncSessionLocal()
    try:
        # 检查是否已存在本机SSH配置
        from sqlalchemy import select
        result = await db.execute(select(host_models.Host).filter(host_models.Host.address == "127.0.0.1"))
        localhost_hosts = result.scalars().all()
        
        # 如果不存在本机配置，则创建一个默认的系统创建记录
        if not localhost_hosts:
            localhost_host = host_models.Host(
                comment="本机",
                address="127.0.0.1",
                username="root",
                port=22,
                auth_method="key",
                private_key="",  # 初始为空，前端会要求用户填写
                is_system_created=True  # 标记为系统创建的记录
            )
            db.add(localhost_host)
            await db.commit()
            logger.info("Localhost SSH config created successfully!")
        else:
            logger.info("Localhost SSH config already exists.")
    except Exception as e:
        logger.error(f"Error creating localhost SSH config: {e}")
        await db.rollback()
    finally:
        await db.close()


async def create_local_docker_node():
    """创建默认本机Docker节点"""
    # 手动创建容器数据库会话
    db = ContainerAsyncSessionLocal()
    try:
        # 检查是否已存在本机Docker节点（通过unix_socket类型和本地套接字地址识别）
        from sqlalchemy import select
        result = await db.execute(select(container_models.DockerNode).filter(
            container_models.DockerNode.endpoint_type == "unix_socket",
            container_models.DockerNode.endpoint_url == "unix:///var/run/docker.sock"
        ))
        local_nodes = result.scalars().all()
        
        # 如果不存在本地节点，则创建一个默认的系统创建记录
        if not local_nodes:
            local_docker_node = container_models.DockerNode(
                name="localhost",
                identifier="localhost",
                description="localhost",
                endpoint_type="unix_socket",
                endpoint_url="unix:///var/run/docker.sock",
                compose_path="/opt/blackpotbpanel-v2/server/composeapp/compose-localhost"
            )
            db.add(local_docker_node)
            await db.commit()
            logger.info("Local Docker node created successfully!")
        else:
            logger.info("Local Docker node already exists.")
    except Exception as e:
        logger.error(f"Error creating local Docker node: {e}")
        await db.rollback()
    finally:
        await db.close()


async def generate_bp_ssh_keypair_and_install():
    db = AsyncSessionLocal()
    try:
        os.makedirs(os.path.join("data", "ssh"), exist_ok=True)
        priv_path = os.path.join("data", "ssh", "id_ed25519_bp")
        pub_path = os.path.join("data", "ssh", "id_ed25519_bp.pub")

        private_key_content = None
        public_key_content = None

        if not os.path.exists(priv_path) or not os.path.exists(pub_path):
            key = Ed25519PrivateKey.generate()
            private_key_bytes = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_key = key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
            with open(priv_path, "wb") as f:
                f.write(private_key_bytes)
            with open(pub_path, "wb") as f:
                f.write(public_key_bytes)
            try:
                os.chmod(priv_path, 0o600)
                os.chmod(pub_path, 0o644)
            except Exception:
                pass
            private_key_content = private_key_bytes.decode()
            public_key_content = public_key_bytes.decode()
        else:
            with open(priv_path, "r") as f:
                private_key_content = f.read()
            with open(pub_path, "r") as f:
                public_key_content = f.read()

        try:
            root_ssh_dir = "/root/.ssh"
            os.makedirs(root_ssh_dir, exist_ok=True)
            authorized_path = os.path.join(root_ssh_dir, "authorized_keys")
            existing_auth = ""
            if os.path.exists(authorized_path):
                try:
                    with open(authorized_path, "r") as rf:
                        existing_auth = rf.read()
                except Exception:
                    existing_auth = ""
            if public_key_content:
                to_write = public_key_content if public_key_content.endswith("\n") else public_key_content + "\n"
                if existing_auth.find(public_key_content) == -1:
                    with open(authorized_path, "a") as f:
                        f.write(to_write)
            try:
                os.chmod(root_ssh_dir, 0o700)
                os.chmod(authorized_path, 0o600)
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"写入authorized_keys失败: {str(e)}")

        try:
            from sqlalchemy import select
            result = await db.execute(select(host_models.Host).filter(host_models.Host.address == "127.0.0.1"))
            host = result.scalar_one_or_none()
            if host and private_key_content:
                if not host.private_key or host.private_key.strip() != private_key_content.strip():
                    host.private_key = private_key_content
                    await db.commit()
                    logger.info("The private key content for the local SSH configuration has been updated")
                else:
                    logger.info("The private key content for the local SSH configuration has not changed, skipping update")
            else:
                logger.warning("No local SSH configuration found or private key content is empty")
        except Exception as e:
            logger.error(f"Failed to update the private key content in the database: {str(e)}")
            await db.rollback()
    finally:
        await db.close()


def generate_ssl_certificate():
    """
    生成自签名SSL证书，存储到指定目录
    """
    try:
        # 创建SSL证书目录
        ssl_dir = os.path.join("data", "ssl")
        os.makedirs(ssl_dir, exist_ok=True)
        
        # 证书文件路径
        cert_path = os.path.join(ssl_dir, "ssl.crt")
        key_path = os.path.join(ssl_dir, "ssl.key")
        
        # 如果证书已存在，跳过生成
        if os.path.exists(cert_path) and os.path.exists(key_path):
            logger.info("SSL certificate already exists, skipping generation.")
            return
        
        logger.info("Generating self-signed SSL certificate...")
        
        # 生成RSA私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # 生成证书签名请求(CSR)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BlackPotBPanel"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        # 生成自签名证书
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 有效期1年
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.DNSName("127.0.0.1")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # 保存私钥
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # 保存证书
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # 设置文件权限
        try:
            os.chmod(key_path, 0o600)  # 私钥权限设置为600
            os.chmod(cert_path, 0o644)  # 证书权限设置为644
        except Exception:
            pass
        
        logger.info(f"Self-signed SSL certificate generated successfully!")
        logger.info(f"Certificate: {cert_path}")
        logger.info(f"Private key: {key_path}")
        
    except Exception as e:
        logger.error(f"Error generating SSL certificate: {e}")


async def init_db():
    """初始化主数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_script_db():
    """初始化脚本数据库"""
    async with script_engine.begin() as conn:
        await conn.run_sync(ScriptBase.metadata.create_all)


async def init_container_db():
    """初始化容器数据库"""
    async with container_engine.begin() as conn:
        await conn.run_sync(ContainerBase.metadata.create_all)


async def init_firewall_db():
    """初始化防火墙数据库"""
    async with firewall_engine.begin() as conn:
        await conn.run_sync(FirewallBase.metadata.create_all)


async def init_waf_db():
    """初始化WAF数据库"""
    async with waf_engine.begin() as conn:
        await conn.run_sync(WafBase.metadata.create_all)
    
async def init_crontab_db():
    """初始化Cronab数据库"""
    async with crontab_engine.begin() as conn:
        await conn.run_sync(CrontabTaskBase.metadata.create_all)

async def init_database_db():
    """初始化数据库数据库"""
    async with database_engine.begin() as conn:
        await conn.run_sync(DatabaseBase.metadata.create_all)


def run_initialization():
    """运行所有初始化操作"""
    # 只在主进程中打印Logo和执行初始化
    if not os.environ.get("UVICORN_RELOAD_WORKER"):
        print(LOGO)
        # 执行所有初始化操作
        import asyncio
        
        # 生成SSL证书
        generate_ssl_certificate()
        
        # 初始化数据库和其他资源
        asyncio.run(init_db())
        asyncio.run(init_script_db())
        asyncio.run(init_container_db())
        asyncio.run(init_firewall_db())
        asyncio.run(init_waf_db())
        asyncio.run(init_crontab_db())
        asyncio.run(init_database_db())
        asyncio.run(create_admin_user())
        asyncio.run(create_localhost_host())
        asyncio.run(create_local_docker_node())
        asyncio.run(generate_bp_ssh_keypair_and_install())