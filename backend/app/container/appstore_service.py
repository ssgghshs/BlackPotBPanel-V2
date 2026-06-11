import os
import re
import json
import uuid
import asyncio
import logging
import shutil
import zipfile
import tempfile
import subprocess
import docker
from typing import List, Optional, Dict
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from fastapi import HTTPException

from app.container.models import Store, StoreDeploy, DockerNode
from app.container.schemas import (
    StoreCreateRequest,
    StoreUpdateRequest,
    StoreAppItem,
    StoreAppVersionItem,
    StoreEnvItem,
    StoreResponse,
    StoreListResponse,
    StoreSyncRequest,
    StoreSyncResponse,
    StoreDeployRequest,
    StoreDeployResponse,
    PLACEHOLDER_APP_NAME,
    PLACEHOLDER_APP_VERSION,
    PLACEHOLDER_APP_TASK_NAME,
    PLACEHOLDER_CURRENT_DATE,
    STORE_NETWORK_MAP,
)
from app.container.compose_service import DockerComposeService, get_docker_command
from config.database import ContainerAsyncSessionLocal
from config.settings import settings

logger = logging.getLogger(__name__)

# 商店数据存储根目录（来自配置）
STORE_ROOT = settings.APP_CONTAINER_STORE_PATH


class AppStoreService:
    """应用商店服务类"""

    @staticmethod
    def _get_store_path(title: str) -> str:
        """获取商店本地存储路径（使用标题）"""
        return os.path.join(STORE_ROOT, title)

    # ==================== CRUD ====================

    @staticmethod
    async def create_store(
        db: AsyncSession, req: StoreCreateRequest
    ) -> StoreResponse:
        """创建商店源并自动同步"""
        # 检查名称唯一性
        result = await db.execute(
            select(Store).where(Store.name == req.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="商店标识名已存在"
            )
        store = Store(
            title=req.title,
            name=req.name,
            type=req.type,
            url=req.url,
            apps=[],
            total=0,
        )
        db.add(store)
        await db.flush()
        await db.refresh(store)

        # 创建后自动同步
        sync_req = StoreSyncRequest(
            title=req.title,
            name=req.name,
            type=req.type,
            url=req.url,
        )
        await AppStoreService.sync_store(db, sync_req)

        # 重新获取（sync_store 已更新 apps/total）
        await db.refresh(store)
        return AppStoreService._to_response(store)

    @staticmethod
    async def update_store(
        db: AsyncSession, req: StoreUpdateRequest
    ) -> StoreResponse:
        """更新商店源"""
        result = await db.execute(select(Store).where(Store.id == req.id))
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(
                status_code=404, detail="商店源不存在"
            )
        # 如果改名了，检查新名称是否冲突
        if store.name != req.name:
            existing = await db.execute(
                select(Store).where(Store.name == req.name)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=400, detail="商店标识名已存在"
                )
        store.title = req.title
        store.name = req.name
        store.type = req.type
        store.url = req.url
        if req.apps:
            store.apps = [app.model_dump() for app in req.apps]
            store.total = len(req.apps)
        await db.flush()
        await db.refresh(store)

        return AppStoreService._to_response(store)

    @staticmethod
    async def delete_store(db: AsyncSession, store_id: int) -> None:
        """删除商店源及本地数据"""
        result = await db.execute(select(Store).where(Store.id == store_id))
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(status_code=404, detail="商店源不存在")

        # 删除本地存储目录
        store_path = AppStoreService._get_store_path(store.title)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: shutil.rmtree(store_path, ignore_errors=True)
        )

        # 删除数据库记录
        await db.execute(delete(Store).where(Store.id == store_id))
        await db.flush()

    @staticmethod
    async def list_stores(
        db: AsyncSession, title: Optional[str] = None, name: Optional[str] = None
    ) -> StoreListResponse:
        """获取商店源列表"""
        query = select(Store).order_by(Store.id.desc())
        if title:
            query = query.where(Store.title.ilike(f"%{title}%"))
        if name:
            query = query.where(Store.name.ilike(f"%{name}%"))

        result = await db.execute(query)
        stores = result.scalars().all()

        items = [AppStoreService._to_response(s) for s in stores]
        return StoreListResponse(items=items, total=len(items))

    # ==================== 同步 ====================

    @staticmethod
    async def sync_store(
        db: AsyncSession, req: StoreSyncRequest
    ) -> StoreSyncResponse:
        """同步远程商店数据"""
        # 先查找是否已存在该商店
        result = await db.execute(
            select(Store).where(Store.name == req.name)
        )
        store = result.scalar_one_or_none()

        # 取标题作为目录名（新建时用请求中的 title，否则用已保存的 title）
        dir_title = store.title if store else (req.title or req.name)
        store_path = AppStoreService._get_store_path(dir_title)
        os.makedirs(store_path, exist_ok=True)

        loop = asyncio.get_running_loop()

        if req.type == "one_panel":
            apps = await loop.run_in_executor(
                None, AppStoreService._sync_one_panel, store_path, req.url
            )
        elif req.type == "casaos":
            apps = await loop.run_in_executor(
                None, AppStoreService._sync_casaos, store_path, req.url
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的商店类型: {req.type}")

        # 更新数据库记录
        if store:
            store.apps = [app.model_dump() for app in apps]
            store.total = len(apps)
            store.type = req.type
            store.url = req.url
            await db.flush()
        else:
            store = Store(
                title=req.title or req.name,
                name=req.name,
                type=req.type,
                url=req.url,
                apps=[app.model_dump() for app in apps],
                total=len(apps),
            )
            db.add(store)
            await db.flush()

        return StoreSyncResponse(
            name=req.name,
            type=req.type,
            apps=apps,
            total=len(apps),
        )

    # ==================== 内部同步实现 ====================

    @staticmethod
    def _sync_one_panel(store_path: str, git_url: str) -> List[StoreAppItem]:
        """同步 1Panel 商店（git clone，对齐 dpanel 实现）"""
        # 清理旧目录
        shutil.rmtree(store_path, ignore_errors=True)
        os.makedirs(store_path, exist_ok=True)

        # git clone
        import subprocess

        args = ["git", "clone", "--depth", "1"]
        branch = None
        if "#" in git_url:
            git_url, branch = git_url.rsplit("#", 1)
            args.extend(["-b", branch])
        args.extend([git_url, store_path])

        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Git clone 失败: {result.stderr}",
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500, detail="系统未安装 git"
            )

        # 解析 apps 目录
        apps_dir = os.path.join(store_path, "apps")
        apps: List[StoreAppItem] = []
        if os.path.isdir(apps_dir):
            for app_name in os.listdir(apps_dir):
                app_path = os.path.join(apps_dir, app_name)
                if not os.path.isdir(app_path):
                    continue

                data_yml = os.path.join(app_path, "data.yml")
                title = app_name
                description = ""
                desc_zh = ""
                desc_en = ""
                tags = []
                website = ""

                if os.path.exists(data_yml):
                    try:
                        import yaml
                        with open(data_yml, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if data:
                            additional = data.get("additionalProperties", {})
                            title = additional.get("name") or app_name
                            desc_zh = additional.get("shortDescZh", "")
                            desc_en = additional.get("shortDescEn", "")
                            description = desc_zh or desc_en
                            tags = additional.get("tags", [])
                            website = additional.get("website", "")
                    except Exception:
                        pass

                # 扫描版本子目录（每个子目录是一个版本）
                versions: Dict[str, StoreAppVersionItem] = {}
                for entry in os.listdir(app_path):
                    version_path = os.path.join(app_path, entry)
                    if not os.path.isdir(version_path):
                        continue
                    compose_file = os.path.join(version_path, "docker-compose.yml")
                    if not os.path.exists(compose_file):
                        continue
                    resource_path = f"apps/{app_name}/{entry}"

                    # 解析环境变量（formFields）
                    environments: List[StoreEnvItem] = []
                    version_data_yml = os.path.join(version_path, "data.yml")
                    if os.path.exists(version_data_yml):
                        try:
                            import yaml
                            with open(version_data_yml, "r", encoding="utf-8") as f:
                                vdata = yaml.safe_load(f)
                            if vdata:
                                form_fields = vdata.get("additionalProperties", {}).get("formFields", [])
                                if isinstance(form_fields, list):
                                    for field in form_fields:
                                        env_key = field.get("envKey", "")
                                        if not env_key:
                                            continue
                                        env_label_zh = field.get("labelZh", "")
                                        env_label_en = field.get("labelEn", "")
                                        env_default = field.get("default", "")
                                        env_required = field.get("required", "false") == "true"
                                        env_type = field.get("type", "text")
                                        # 类型映射
                                        type_map = {
                                            "text": "text", "number": "number",
                                            "password": "password", "select": "select",
                                        }
                                        mapped_type = type_map.get(env_type, "text")
                                        environments.append(StoreEnvItem(
                                            label=env_label_zh or env_key,
                                            labels={"zh": env_label_zh, "en": env_label_en},
                                            name=env_key,
                                            value=str(env_default) if env_default is not None else "",
                                            required=env_required,
                                            type=mapped_type,
                                        ))
                        except Exception:
                            pass

                    # 检测脚本文件
                    script: Dict[str, str] = {}
                    scripts_dir = os.path.join(version_path, "scripts")
                    if os.path.isdir(scripts_dir):
                        for script_name in ["install.sh", "upgrade.sh", "init.sh", "uninstall.sh"]:
                            if os.path.exists(os.path.join(scripts_dir, script_name)):
                                script[script_name] = f"{resource_path}/scripts/{script_name}"

                    versions[entry] = StoreAppVersionItem(
                        name=entry,
                        compose_file=f"{resource_path}/docker-compose.yml",
                        environment=environments,
                        script=script,
                        default=len(versions) == 0,
                    )

                # 解析 logo
                logo_path = ""
                logo_file = os.path.join(app_path, "logo.png")
                if os.path.exists(logo_file):
                    logo_path = f"image://apps/{app_name}/logo.png"

                # 解析 README
                content = ""
                contents = {}
                readme_file = os.path.join(app_path, "README.md")
                if os.path.exists(readme_file):
                    content = f"markdown-file://apps/{app_name}/README.md"
                    contents["zh"] = content
                readme_en_file = os.path.join(app_path, "README_en.md")
                if os.path.exists(readme_en_file):
                    contents["en"] = f"markdown-file://apps/{app_name}/README_en.md"

                if not isinstance(tags, list):
                    tags = []

                apps.append(
                    StoreAppItem(
                        name=app_name,
                        title=title,
                        description=description,
                        descriptions={"zh": desc_zh, "en": desc_en},
                        logo=logo_path,
                        content=content,
                        contents=contents,
                        tags=tags,
                        website=website,
                        versions=versions,
                    )
                )

        return apps

    @staticmethod
    def _sync_casaos(store_path: str, zip_url: str) -> List[StoreAppItem]:
        """同步 CasaOS 商店（下载 zip）"""
        # 清理旧目录
        shutil.rmtree(store_path, ignore_errors=True)
        os.makedirs(store_path, exist_ok=True)

        # 下载 zip
        try:
            import httpx
            response = httpx.get(zip_url, follow_redirects=True, timeout=300)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"下载商店数据失败: {str(e)}"
            )

        # 解压到临时目录，提取 Apps 目录
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "store.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            # 查找 Apps 目录
            apps_src = os.path.join(tmpdir, "Apps")
            if not os.path.isdir(apps_src):
                # 尝试在解压后的第一级子目录中找
                for entry in os.listdir(tmpdir):
                    candidate = os.path.join(tmpdir, entry, "Apps")
                    if os.path.isdir(candidate):
                        apps_src = candidate
                        break

            if os.path.isdir(apps_src):
                # 复制到 store_path
                for item in os.listdir(apps_src):
                    shutil.copytree(
                        os.path.join(apps_src, item),
                        os.path.join(store_path, item),
                        dirs_exist_ok=True,
                    )

        # 解析应用（对齐 dpanel 实现）
        apps: List[StoreAppItem] = []
        for app_name in os.listdir(store_path):
            app_path = os.path.join(store_path, app_name)
            if not os.path.isdir(app_path):
                continue

            store_item = StoreAppItem(
                name=app_name,
                title=app_name,
                description="",
                descriptions={},
                logo="",
                content="",
                contents={},
                tags=[],
                website="",
                versions={
                    "latest": StoreAppVersionItem(
                        name="latest",
                        compose_file=f"{app_name}/docker-compose.yml",
                        default=True,
                    )
                },
            )

            compose_file = os.path.join(app_path, "docker-compose.yml")
            if os.path.exists(compose_file):
                try:
                    import yaml
                    with open(compose_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data and "x-casaos" in data:
                        casaos = data["x-casaos"]
                        raw_title = casaos.get("title", app_name)
                        if isinstance(raw_title, dict):
                            store_item.title = raw_title.get("en_us", raw_title.get("zh_cn", app_name))
                        else:
                            store_item.title = raw_title

                        # 描述（使用 dpanel 的 key 名称）
                        store_item.descriptions = {
                            "zh": casaos.get("description", {}).get("zh_cn", ""),
                            "en": casaos.get("description", {}).get("en_us", ""),
                        }
                        store_item.description = store_item.descriptions.get("zh") or store_item.descriptions.get("en") or ""

                        # 分类 → tags
                        category = casaos.get("category", "")
                        if category:
                            store_item.tags = [category]

                        # Logo 从 x-casaos.icon 读取（dpanel 方式）
                        icon_url = casaos.get("icon", "")
                        if icon_url:
                            store_item.logo = icon_url

                        # Content 从 x-casaos.tips.before_install 读取（dpanel 方式）
                        tip_zh = casaos.get("tips", {}).get("before_install", {}).get("zh_cn", "")
                        tip_en = casaos.get("tips", {}).get("before_install", {}).get("en_us", "")
                        if tip_zh:
                            store_item.content = "markdown-file://" + tip_zh
                            store_item.contents["zh"] = "markdown://" + tip_zh
                        if tip_en:
                            store_item.contents["en"] = "markdown://" + tip_en
                except Exception:
                    pass

            apps.append(store_item)

        return apps

    # ==================== 版本详情 ====================

    @staticmethod
    async def get_version_detail(
        db: AsyncSession, store_id: int, app_name: str, version_name: str
    ) -> "StoreAppVersionDetailResponse":
        """获取商店应用版本的详情（compose YAML 内容 + 环境变量）"""
        from app.container.schemas import StoreAppVersionDetailResponse, StoreEnvItem

        # 1. 查询商店
        result = await db.execute(select(Store).where(Store.id == store_id))
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(status_code=404, detail="商店源不存在")

        apps = store.apps or []
        # 2. 查找应用
        app_item = None
        for a in apps:
            if isinstance(a, dict) and a.get("name") == app_name:
                app_item = a
                break
        if not app_item:
            raise HTTPException(status_code=404, detail=f"应用 {app_name} 不存在")

        # 3. 查找版本
        versions = app_item.get("versions") or {}
        version_data = versions.get(version_name)
        if not version_data:
            raise HTTPException(status_code=404, detail=f"版本 {version_name} 不存在")

        # 解析 ref：如果该版本只有 ref 引用，则取其指向的版本数据
        resolved = AppStoreService._resolve_version_ref(version_data, versions)
        compose_file_rel = resolved.get("compose_file", "") or ""
        raw_env = resolved.get("environment") or []

        # 4. 读取 compose 文件
        compose_content = ""
        if compose_file_rel:
            if not os.path.isabs(compose_file_rel):
                abs_path = os.path.normpath(
                    os.path.join(STORE_ROOT, store.title, compose_file_rel)
                )
            else:
                abs_path = compose_file_rel
            if os.path.isfile(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        compose_content = f.read()
                except Exception as e:
                    logger.warning(f"读取 compose 文件失败 {abs_path}: {e}")

        # 5. 收集环境变量
        env_items = []
        for env in raw_env:
            if isinstance(env, dict):
                env_items.append(StoreEnvItem(
                    label=env.get("label", ""),
                    labels=env.get("labels", {}),
                    name=env.get("name", ""),
                    value=env.get("value", "") or "",
                    required=env.get("required", False),
                    type=env.get("type", "text"),
                ))
            else:
                env_items.append(StoreEnvItem(
                    name=getattr(env, "name", ""),
                    value=getattr(env, "value", ""),
                ))

        return StoreAppVersionDetailResponse(
            compose_content=compose_content,
            environment=env_items,
        )

    @staticmethod
    def _resolve_version_ref(version_data: dict, versions: dict) -> dict:
        """解析版本数据的 ref 引用，返回完整的版本数据（compose_file / environment / download）

        同步时子版本可能只有 ref 字段指向主版本，需要递归解析。
        """
        if not isinstance(version_data, dict):
            return {}
        ref = version_data.get("ref")
        if not ref:
            return version_data
        # 递归解析直到没有 ref
        referenced = versions.get(ref)
        if not referenced:
            logger.warning(f"版本 ref={ref} 指向的版本不存在")
            return version_data
        if isinstance(referenced, dict) and referenced.get("ref"):
            referenced = AppStoreService._resolve_version_ref(referenced, versions)
            referenced = referenced if isinstance(referenced, dict) else {}
        elif not isinstance(referenced, dict):
            referenced = {}
        # 合并：当前数据 > 引用数据
        result = dict(referenced)
        for k, v in version_data.items():
            if v:
                result[k] = v
        return result

    # ==================== 部署 ====================

    @staticmethod
    async def deploy(
        db: AsyncSession, req: StoreDeployRequest
    ) -> StoreDeployResponse:
        """部署商店应用（异步：创建记录后立即返回，后台执行实际部署）

        1. 校验商店/应用/版本
        2. 创建 StoreDeploy 记录（status=deploying）
        3. 启动后台部署任务
        4. 立即返回
        """
        # 1. 查询商店
        result = await db.execute(select(Store).where(Store.id == req.store_id))
        store = result.scalar_one_or_none()
        if not store:
            raise HTTPException(status_code=404, detail="商店源不存在")
        if not store.apps:
            raise HTTPException(status_code=400, detail="商店源暂无应用数据，请先同步")

        # 确保 task_name 符合 docker compose 项目名规范（小写字母、数字、中划线、下划线）
        req.task_name = re.sub(r"[^a-z0-9_-]", "", req.task_name.lower())
        if not req.task_name or req.task_name[0] in "-_":
            req.task_name = "app-" + req.task_name
        if not req.task_name:
            req.task_name = f"app-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 查找应用
        app_item = None
        for a in store.apps:
            if isinstance(a, dict) and a.get("name") == req.app_name:
                app_item = a
                break
        if not app_item:
            raise HTTPException(status_code=404, detail=f"应用 {req.app_name} 不存在")

        # 查找版本（含 ref 解析）
        raw_versions = app_item.get("versions", {})
        if req.version_name not in raw_versions:
            raise HTTPException(status_code=404, detail=f"版本 {req.version_name} 不存在")
        version_data = raw_versions[req.version_name]
        if isinstance(version_data, dict):
            # 解析 ref 引用
            version_data = AppStoreService._resolve_version_ref(version_data, raw_versions)
            compose_file_rel = version_data.get("compose_file", "")
        else:
            compose_file_rel = getattr(version_data, "compose_file", "")
        if not compose_file_rel:
            raise HTTPException(status_code=400, detail="该版本没有 docker-compose.yml")

        # 2. 确定路径并创建 StoreDeploy 记录
        store_path = AppStoreService._get_store_path(store.title)
        app_rel_dir = os.path.dirname(compose_file_rel)
        source_app_dir = os.path.normpath(os.path.join(store_path, app_rel_dir))

        # 按节点 compose_path 定位部署目录
        if req.node_id > 0:
            node_result = await db.execute(
                select(DockerNode).where(DockerNode.id == req.node_id)
            )
            node = node_result.scalar_one_or_none()
            node_compose_path = node.compose_path if node else None
        else:
            node_compose_path = None
        base_deploy_root = node_compose_path or settings.APP_CONTAINER_STORE_PATH
        target_path = os.path.join(base_deploy_root, req.task_name)
        target_compose_file = os.path.join(target_path, "docker-compose.yml")

        deploy_record = StoreDeploy(
            task_name=req.task_name,
            title=req.app_title,
            store_id=req.store_id,
            store_name=store.name,
            store_type=store.type,
            app_name=req.app_name,
            version_name=req.version_name,
            compose_file=target_compose_file,
            project_path=target_path,
            environment=[{"name": e.name, "value": e.value} for e in req.environment],
            node_id=req.node_id,
            status="deploying",
            message="",
        )
        db.add(deploy_record)
        await db.flush()
        await db.refresh(deploy_record)

        # 生成 operation_id（UUID），日志文件路径指向容器操作的统一日志目录
        operation_id = str(uuid.uuid4())
        deploy_log_dir = os.path.join(settings.TEMP_PATH, "containerlog")
        os.makedirs(deploy_log_dir, exist_ok=True)
        deploy_log_file = os.path.join(deploy_log_dir, f"deploy_{operation_id}.log")

        # 回写 operation_id 到记录
        deploy_record.operation_id = operation_id
        await db.flush()

        # 3. 启动后台部署任务（传入所需数据的副本，避免跨会话引用）
        store_data = {
            "id": store.id,
            "title": store.title,
            "name": store.name,
            "type": store.type,
            "apps": store.apps,
        }
        asyncio.create_task(
            AppStoreService._run_deploy(store_data, req, deploy_record.id, deploy_log_file)
        )

        # 4. 立即返回
        return StoreDeployResponse(
            id=deploy_record.id,
            task_name=deploy_record.task_name,
            title=deploy_record.title,
            store_name=deploy_record.store_name,
            store_type=deploy_record.store_type,
            app_name=deploy_record.app_name,
            version_name=deploy_record.version_name,
            status=deploy_record.status,
            message="",
            created_at=deploy_record.created_at.isoformat() if deploy_record.created_at else "",
            operation_id=operation_id,
        )

    @staticmethod
    async def _run_deploy(
        store_data: dict, req: StoreDeployRequest, deploy_id: int, deploy_log_file: str
    ) -> None:
        """后台部署任务"""
        session = ContainerAsyncSessionLocal()
        log_lines: List[str] = []
        log_file = deploy_log_file

        def add_log(msg: str) -> None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {msg}"
            log_lines.append(line)
            # 实时写入文件
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

        try:
            add_log("部署任务已启动")

            # 获取 docker 节点
            node: Optional[DockerNode] = None
            if req.node_id > 0:
                result = await session.execute(
                    select(DockerNode).where(DockerNode.id == req.node_id)
                )
                node = result.scalar_one_or_none()
            if node is None:
                node = DockerNode(
                    id=0,
                    name="local",
                    endpoint_type="unix_socket",
                    endpoint_url="unix:///var/run/docker.sock",
                )
            add_log(f"Docker 节点: {node.name} (id={node.id})")

            loop = asyncio.get_running_loop()
            store_type = store_data["type"]

            # 查找版本 compose 路径和 formFields
            app_item = None
            for a in store_data.get("apps", []):
                if isinstance(a, dict) and a.get("name") == req.app_name:
                    app_item = a
                    break
            raw_versions = app_item.get("versions", {}) if app_item else {}
            version_data = raw_versions.get(req.version_name, {})
            if isinstance(version_data, dict):
                # 解析 ref 引用
                version_data = AppStoreService._resolve_version_ref(version_data, raw_versions)
                compose_file_rel = version_data.get("compose_file", "") or ""
                form_fields = version_data.get("environment", []) or []
            else:
                compose_file_rel = getattr(version_data, "compose_file", "") or ""
                form_fields = getattr(version_data, "environment", []) or []

            store_path = AppStoreService._get_store_path(store_data["title"])
            app_rel_dir = os.path.dirname(compose_file_rel)
            source_app_dir = os.path.normpath(os.path.join(store_path, app_rel_dir))

            # 兼容旧数据：CasaOS 同步时可能存了 Apps/ 前缀但实际没有
            if not os.path.isdir(source_app_dir) and store_type == "casaos":
                alt_rel_dir = app_rel_dir.replace("Apps/", "", 1) if app_rel_dir.startswith("Apps/") else app_rel_dir
                alt_source = os.path.normpath(os.path.join(store_path, alt_rel_dir))
                if os.path.isdir(alt_source):
                    source_app_dir = alt_source
                    compose_file_rel = os.path.join(alt_rel_dir, "docker-compose.yml")
                    add_log(f"路径修正: {app_rel_dir} → {alt_rel_dir}")
            # 按节点 compose_path 定位部署目录
            node_compose_path = getattr(node, "compose_path", None) or ""
            base_deploy_root = node_compose_path or settings.APP_CONTAINER_STORE_PATH
            target_path = os.path.join(base_deploy_root, req.task_name)
            target_compose_file = os.path.join(target_path, "docker-compose.yml")
            add_log(f"源目录: {source_app_dir}")
            add_log(f"目标目录: {target_path}")

            # 创建私有网络
            if store_type in STORE_NETWORK_MAP:
                network_name = STORE_NETWORK_MAP[store_type]
                try:
                    net_cmd = [get_docker_command(), "network", "create", network_name]
                    add_log(f"创建 Docker 网络: {network_name}")
                    net_result = await loop.run_in_executor(
                        None,
                        lambda: subprocess.run(net_cmd, capture_output=True, text=True, timeout=30),
                    )
                    if net_result.returncode == 0:
                        add_log(f"网络创建成功: {net_result.stdout.strip()}")
                    else:
                        add_log(f"网络创建（可能已存在）: {net_result.stderr.strip()}")
                except Exception as e:
                    add_log(f"网络创建跳过: {e}")

            # 复制文件
            add_log("开始复制应用文件...")
            await loop.run_in_executor(
                None,
                lambda: shutil.copytree(source_app_dir, target_path, dirs_exist_ok=True),
            )
            add_log("文件复制完成")

            # 合并环境变量
            user_env_map = {e.name: e.value for e in req.environment}
            final_env: Dict[str, str] = {}
            for field in form_fields:
                if isinstance(field, dict):
                    f_name = field.get("name", "")
                    f_value = field.get("value", "")
                else:
                    f_name = getattr(field, "name", "")
                    f_value = getattr(field, "value", "")
                if f_name:
                    final_env[f_name] = f_value
            for k, v in user_env_map.items():
                if v:
                    final_env[k] = v
            if store_type == "one_panel":
                final_env.setdefault("CONTAINER_NAME", req.task_name)
            now_str = datetime.now().strftime("%Y%m%d%H%M%S")
            for k, v in final_env.items():
                v = v.replace(PLACEHOLDER_APP_NAME, req.app_name)
                v = v.replace(PLACEHOLDER_APP_VERSION, req.version_name)
                v = v.replace(PLACEHOLDER_APP_TASK_NAME, req.task_name)
                v = v.replace(PLACEHOLDER_CURRENT_DATE, now_str)
                final_env[k] = v
            add_log(f"环境变量: {len(final_env)} 项")

            # 执行 init.sh（仅本地节点）
            if req.node_id == 0:
                init_script = os.path.join(target_path, "scripts", "init.sh")
                if os.path.isfile(init_script):
                    add_log("执行 init.sh ...")
                    try:
                        init_result = await loop.run_in_executor(
                            None,
                            lambda: subprocess.run(
                                ["sh", init_script],
                                cwd=target_path,
                                capture_output=True,
                                text=True,
                                timeout=120,
                            ),
                        )
                        if init_result.stdout:
                            add_log(f"init.sh stdout: {init_result.stdout.strip()}")
                        if init_result.stderr:
                            add_log(f"init.sh stderr: {init_result.stderr.strip()}")
                        add_log(f"init.sh 退出码: {init_result.returncode}")
                    except Exception as e:
                        add_log(f"init.sh 执行失败（非致命）: {e}")
                else:
                    add_log("init.sh 不存在，跳过")

            # docker compose 部署（内部自动先拉取镜像再启动容器）
            add_log("开始 docker compose 部署（拉取镜像 → 启动容器）...")
            deploy_result = await DockerComposeService.compose_deploy(
                node=node,
                compose_file=target_compose_file,
                project_name=req.task_name,
                project_path=target_path,
                env_vars=final_env if final_env else None,
                pull_image=True,
                log_file=log_file,
            )
            add_log(f"部署完成，状态: {deploy_result.get('status', 'unknown')}")

            # 更新部署状态
            new_status = "running" if deploy_result.get("status") == "success" else "error"
            new_message = deploy_result.get("message", "")
            result = await session.execute(
                select(StoreDeploy).where(StoreDeploy.id == deploy_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.status = new_status
                record.message = new_message or ""
                record.log = "\n".join(log_lines)
                await session.commit()

        except Exception as e:
            logger.error(f"后台部署任务失败: {e}")
            add_log(f"部署异常: {e}")
            try:
                result = await session.execute(
                    select(StoreDeploy).where(StoreDeploy.id == deploy_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.status = "error"
                    record.message = str(e)[:500]
                    record.log = "\n".join(log_lines)
                    await session.commit()
            except Exception:
                pass
        finally:
            await session.close()

    @staticmethod
    async def get_deploy_log(
        db: AsyncSession, deploy_id: int
    ) -> str:
        """获取部署日志（优先读实时文件，fallback 到数据库）"""
        # 1. 尝试读统一日志目录下的实时日志文件
        log_file = os.path.join(
            settings.TEMP_PATH, "containerlog", f"deploy_{deploy_id}.log"
        )
        if os.path.isfile(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        # 2. fallback 到数据库
        result = await db.execute(
            select(StoreDeploy).where(StoreDeploy.id == deploy_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="部署记录不存在")
        return record.log or ""

    @staticmethod
    async def get_deploy_status(
        db: AsyncSession, deploy_id: int
    ) -> Optional[StoreDeploy]:
        """获取部署记录（供路由轮询）"""
        result = await db.execute(
            select(StoreDeploy).where(StoreDeploy.id == deploy_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_deploys(
        db: AsyncSession, node_id: Optional[int] = None
    ) -> List[StoreDeployResponse]:
        """获取部署记录列表（含实际容器运行状态，参考 composelist）"""
        query = select(StoreDeploy).order_by(StoreDeploy.id.desc())
        if node_id is not None:
            query = query.where(StoreDeploy.node_id == node_id)

        result = await db.execute(query)
        records = result.scalars().all()

        # 按 node_id 分组，批量检查容器运行状态
        node_containers: Dict[int, Dict[str, bool]] = {}
        for r in records:
            if r.node_id not in node_containers:
                node_containers[r.node_id] = {}

        loop = asyncio.get_running_loop()

        for nid in node_containers:
            # 查找该节点的 task_name 列表
            task_names = [r.task_name for r in records if r.node_id == nid]
            if not task_names:
                continue

            # 获取 Docker 节点对象
            node = None
            if nid > 0:
                node_result = await db.execute(
                    select(DockerNode).where(DockerNode.id == nid)
                )
                node = node_result.scalar_one_or_none()

            # 使用 Docker SDK 批量检查该节点上所有项目的容器状态
            def _check_running(host_node, names):
                """同步函数：连接 Docker 并检查每个 task_name 是否有 running 容器"""
                result_map = {name: False for name in names}
                try:
                    if host_node and hasattr(host_node, 'connection_config'):
                        config = host_node.connection_config
                        if config.get('tls'):
                            from app.container.service import create_docker_client_with_tls
                            client, _ = create_docker_client_with_tls(config)
                        else:
                            client = docker.DockerClient(base_url=config['base_url'])
                    else:
                        # node_id == 0 或无节点 → 本地 unix socket
                        client = docker.DockerClient(base_url='unix:///var/run/docker.sock')

                    # 批量查询所有 running 容器（限制只查一次）
                    all_containers = client.containers.list(filters={'status': 'running'})
                    for c in all_containers:
                        project = c.labels.get('com.docker.compose.project', '')
                        if project in result_map:
                            result_map[project] = True

                    client.close()
                except Exception as e:
                    logger.warning(f"检查容器状态失败 (node={getattr(host_node, 'id', 0)}): {e}")
                return result_map

            try:
                check_result = await loop.run_in_executor(None, _check_running, node, task_names)
                node_containers[nid] = check_result
            except Exception:
                node_containers[nid] = {name: True for name in task_names}

        return [
            StoreDeployResponse(
                id=r.id,
                task_name=r.task_name,
                title=r.title,
                store_name=r.store_name,
                store_type=r.store_type,
                app_name=r.app_name,
                version_name=r.version_name,
                status=r.status,
                message=r.message or "",
                created_at=r.created_at.isoformat() if r.created_at else "",
                operation_id=r.operation_id or f"deploy_{r.id}",
                running=node_containers.get(r.node_id, {}).get(r.task_name, True),
            )
            for r in records
        ]

    @staticmethod
    async def redeploy_deploy(db: AsyncSession, deploy_id: int) -> StoreDeployResponse:
        """重新部署已部署的应用（原地重部署）

        在原有部署记录上直接重新部署，不创建新记录：
        1. 重置记录状态为 deploying，清空 message/log
        2. 从商店源重新复制应用文件
        3. 重新写入环境变量 .env 文件
        4. 执行 docker compose up -d（含拉取新镜像）
        5. 更新记录状态为 running 或 error
        """
        # 1. 加载原有部署记录
        result = await db.execute(
            select(StoreDeploy).where(StoreDeploy.id == deploy_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="部署记录不存在")

        # 2. 重置状态为 deploying
        record.status = "deploying"
        record.message = ""
        await db.flush()

        # 3. 生成 operation_id 和日志文件
        operation_id = str(uuid.uuid4())
        deploy_log_dir = os.path.join(settings.TEMP_PATH, "containerlog")
        os.makedirs(deploy_log_dir, exist_ok=True)
        deploy_log_file = os.path.join(deploy_log_dir, f"deploy_{operation_id}.log")
        record.operation_id = operation_id
        await db.flush()

        # 4. 加载商店数据
        store_result = await db.execute(
            select(Store).where(Store.id == record.store_id)
        )
        store = store_result.scalar_one_or_none()
        if not store or not store.apps:
            raise HTTPException(status_code=400, detail="商店源不存在或无应用数据")

        store_data = {
            "id": store.id,
            "title": store.title,
            "name": store.name,
            "type": store.type,
            "apps": store.apps,
        }

        # 5. 构造最小请求对象供后台任务使用
        class _RedeployRequest:
            def __init__(self, record):
                self.node_id = record.node_id
                self.app_name = record.app_name
                self.version_name = record.version_name
                self.task_name = record.task_name
                self.environment = [
                    type("_Env", (), {"name": e["name"], "value": e["value"]})()
                    for e in (record.environment or [])
                ]

        req = _RedeployRequest(record)

        # 6. 启动后台重部署任务
        asyncio.create_task(
            AppStoreService._run_redeploy(store_data, req, record.id, deploy_log_file, record.project_path, record.compose_file)
        )

        # 7. 立即返回
        return StoreDeployResponse(
            id=record.id,
            task_name=record.task_name,
            title=record.title,
            store_name=record.store_name,
            store_type=record.store_type,
            app_name=record.app_name,
            version_name=record.version_name,
            status="deploying",
            message="",
            created_at=record.created_at.isoformat() if record.created_at else "",
            operation_id=operation_id,
        )

    @staticmethod
    async def _run_redeploy(
        store_data: dict, req, deploy_id: int, deploy_log_file: str,
        target_path: str, target_compose_file: str
    ) -> None:
        """后台重部署任务（原地更新，不新建目录）"""
        session = ContainerAsyncSessionLocal()
        log_lines: List[str] = []
        log_file = deploy_log_file

        def add_log(msg: str) -> None:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {msg}"
            log_lines.append(line)
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass

        try:
            add_log("重部署任务已启动")

            # 获取 docker 节点
            node: Optional[DockerNode] = None
            if req.node_id > 0:
                result = await session.execute(
                    select(DockerNode).where(DockerNode.id == req.node_id)
                )
                node = result.scalar_one_or_none()
            if node is None:
                node = DockerNode(
                    id=0, name="local",
                    endpoint_type="unix_socket",
                    endpoint_url="unix:///var/run/docker.sock",
                )
            add_log(f"Docker 节点: {node.name} (id={node.id})")

            loop = asyncio.get_running_loop()
            store_type = store_data["type"]

            # 查找版本 compose 路径
            app_item = None
            for a in store_data.get("apps", []):
                if isinstance(a, dict) and a.get("name") == req.app_name:
                    app_item = a
                    break
            raw_versions = app_item.get("versions", {}) if app_item else {}
            version_data = raw_versions.get(req.version_name, {})
            if isinstance(version_data, dict):
                version_data = AppStoreService._resolve_version_ref(version_data, raw_versions)
                compose_file_rel = version_data.get("compose_file", "") or ""
                form_fields = version_data.get("environment", []) or []
            else:
                compose_file_rel = getattr(version_data, "compose_file", "") or ""
                form_fields = getattr(version_data, "environment", []) or []

            store_path = AppStoreService._get_store_path(store_data["title"])
            app_rel_dir = os.path.dirname(compose_file_rel)
            source_app_dir = os.path.normpath(os.path.join(store_path, app_rel_dir))

            add_log(f"源目录: {source_app_dir}")
            add_log(f"目标目录: {target_path}")

            # 创建私有网络
            if store_type in STORE_NETWORK_MAP:
                network_name = STORE_NETWORK_MAP[store_type]
                try:
                    net_cmd = [get_docker_command(), "network", "create", network_name]
                    add_log(f"创建 Docker 网络: {network_name}")
                    net_result = await loop.run_in_executor(
                        None,
                        lambda: subprocess.run(net_cmd, capture_output=True, text=True, timeout=30),
                    )
                    if net_result.returncode == 0:
                        add_log(f"网络创建成功: {net_result.stdout.strip()}")
                    else:
                        add_log(f"网络创建（可能已存在）: {net_result.stderr.strip()}")
                except Exception as e:
                    add_log(f"网络创建跳过: {e}")

            # 重新复制文件（覆盖现有文件）
            if os.path.isdir(source_app_dir):
                add_log("开始复制应用文件...")
                await loop.run_in_executor(
                    None,
                    lambda: shutil.copytree(source_app_dir, target_path, dirs_exist_ok=True),
                )
                add_log("文件复制完成")
            else:
                add_log(f"源目录不存在，跳过文件复制: {source_app_dir}")

            # 合并环境变量并写入 .env
            user_env_map = {e.name: e.value for e in req.environment}
            final_env: Dict[str, str] = {}
            for field in form_fields:
                if isinstance(field, dict):
                    f_name = field.get("name", "")
                    f_value = field.get("value", "")
                else:
                    f_name = getattr(field, "name", "")
                    f_value = getattr(field, "value", "")
                if f_name:
                    final_env[f_name] = f_value
            for k, v in user_env_map.items():
                if v:
                    final_env[k] = v
            if store_type == "one_panel":
                final_env.setdefault("CONTAINER_NAME", req.task_name)
            now_str = datetime.now().strftime("%Y%m%d%H%M%S")
            for k, v in final_env.items():
                v = v.replace(PLACEHOLDER_APP_NAME, req.app_name)
                v = v.replace(PLACEHOLDER_APP_VERSION, req.version_name)
                v = v.replace(PLACEHOLDER_APP_TASK_NAME, req.task_name)
                v = v.replace(PLACEHOLDER_CURRENT_DATE, now_str)
                final_env[k] = v
            add_log(f"环境变量: {len(final_env)} 项")

            # 写入 .env 文件
            env_file = os.path.join(target_path, ".env")
            try:
                env_content = "\n".join(f"{k}={v}" for k, v in final_env.items())
                await loop.run_in_executor(
                    None, lambda: open(env_file, "w", encoding="utf-8").write(env_content)
                )
                add_log(f".env 文件已写入: {env_file}")
            except Exception as e:
                add_log(f"写入 .env 文件失败（非致命）: {e}")

            # docker compose 部署
            add_log("开始 docker compose 部署（拉取镜像 → 启动容器）...")
            deploy_result = await DockerComposeService.compose_deploy(
                node=node,
                compose_file=target_compose_file,
                project_name=req.task_name,
                project_path=target_path,
                env_vars=final_env if final_env else None,
                pull_image=True,
                log_file=log_file,
            )
            add_log(f"部署完成，状态: {deploy_result.get('status', 'unknown')}")

            # 更新部署状态
            new_status = "running" if deploy_result.get("status") == "success" else "error"
            new_message = deploy_result.get("message", "")
            result = await session.execute(
                select(StoreDeploy).where(StoreDeploy.id == deploy_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.status = new_status
                record.message = new_message or ""
                record.log = "\n".join(log_lines)
                await session.commit()
                add_log(f"部署状态已更新: {new_status}")

        except Exception as e:
            logger.error(f"后台重部署任务失败: {e}")
            add_log(f"重部署异常: {e}")
            try:
                result = await session.execute(
                    select(StoreDeploy).where(StoreDeploy.id == deploy_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.status = "error"
                    record.message = str(e)[:500]
                    record.log = "\n".join(log_lines)
                    await session.commit()
            except Exception:
                pass
        finally:
            await session.close()

    @staticmethod
    async def destroy_deploy(db: AsyncSession, deploy_id: int) -> None:
        """销毁部署（docker compose down + 删除记录 + 删除文件）"""
        result = await db.execute(
            select(StoreDeploy).where(StoreDeploy.id == deploy_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="部署记录不存在")

        loop = asyncio.get_running_loop()

        # 加载 Docker 节点（用于 -H 参数）
        node: Optional[DockerNode] = None
        if record.node_id > 0:
            node_result = await db.execute(
                select(DockerNode).where(DockerNode.id == record.node_id)
            )
            node = node_result.scalar_one_or_none()

        # 构建基础 docker 命令（含远程节点 -H 参数）
        def _build_docker_cmd(extra_args: List[str]) -> List[str]:
            base = [get_docker_command()]
            if node:
                endpoint_type = getattr(node, 'endpoint_type', '')
                endpoint_url = getattr(node, 'endpoint_url', '')
                if endpoint_type == 'tcp' and endpoint_url:
                    if endpoint_url.startswith('tcp://'):
                        remote_url = endpoint_url
                    elif endpoint_url.startswith('http://') or endpoint_url.startswith('https://'):
                        remote_url = f"tcp://{endpoint_url.split('://')[1]}"
                    else:
                        remote_url = f"tcp://{endpoint_url}"
                    base.extend(['-H', remote_url])
            base.extend(extra_args)
            return base

        # 优先使用 docker compose down 停止并删除容器
        compose_down_ok = False
        try:
            cmd = _build_docker_cmd(
                ["compose", "-p", record.task_name, "-f", record.compose_file, "down", "--remove-orphans"]
            )
            result_down = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, cwd=record.project_path, capture_output=True, text=True, timeout=120),
            )
            if result_down.returncode == 0:
                compose_down_ok = True
            else:
                logger.warning(f"compose down 返回非零: {result_down.stderr}")
        except Exception as e:
            logger.warning(f"compose down 执行异常: {e}")

        # 如果 compose down 失败，fallback 到按项目标签手动停止+删除容器
        if not compose_down_ok:
            logger.info(f"compose down 失败，尝试按标签手动清理容器: {record.task_name}")
            try:
                ps_cmd = _build_docker_cmd(
                    ["ps", "-a", "--filter", f"label=com.docker.compose.project={record.task_name}", "--format", "{{.ID}}"]
                )
                ps_result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(ps_cmd, capture_output=True, text=True, timeout=30),
                )
                if ps_result.returncode == 0 and ps_result.stdout.strip():
                    container_ids = ps_result.stdout.strip().split("\n")
                    stop_cmd = _build_docker_cmd(["stop"] + container_ids)
                    await loop.run_in_executor(
                        None,
                        lambda: subprocess.run(stop_cmd, capture_output=True, text=True, timeout=60),
                    )
                    rm_cmd = _build_docker_cmd(["rm", "-f"] + container_ids)
                    await loop.run_in_executor(
                        None,
                        lambda: subprocess.run(rm_cmd, capture_output=True, text=True, timeout=60),
                    )
                    logger.info(f"已手动清理 {len(container_ids)} 个容器")
            except Exception as e:
                logger.warning(f"手动清理容器失败: {e}")

        # 删除文件
        if record.project_path and os.path.isdir(record.project_path):
            await loop.run_in_executor(
                None, lambda: shutil.rmtree(record.project_path, ignore_errors=True)
            )

        # 删除 DB 记录
        await db.execute(
            delete(StoreDeploy).where(StoreDeploy.id == deploy_id)
        )
        await db.flush()

        # 删除实时日志文件
        op_id = record.operation_id or f"deploy_{record.id}"
        log_file = os.path.join(settings.TEMP_PATH, "containerlog", f"deploy_{op_id}.log")
        if os.path.isfile(log_file):
            try:
                os.remove(log_file)
            except Exception:
                pass

    @staticmethod
    # ==================== 工具方法 ====================

    @staticmethod
    def _to_response(store: Store) -> StoreResponse:
        """将 Store ORM 对象转换为响应模型"""
        apps_raw = store.apps or []
        apps = []
        for a in apps_raw:
            if isinstance(a, dict):
                app_item = StoreAppItem(
                    name=a.get("name", ""),
                    title=a.get("title"),
                    description=a.get("description"),
                    descriptions=a.get("descriptions", {}),
                    logo=a.get("logo"),
                    content=a.get("content"),
                    contents=a.get("contents", {}),
                    tags=a.get("tags", []),
                    website=a.get("website"),
                    versions={},
                )
                # 解析 versions 字典
                raw_versions = a.get("versions", {})
                for v_name, v_data in raw_versions.items():
                    if isinstance(v_data, dict):
                        env_items = [StoreEnvItem(**e) if isinstance(e, dict) else e for e in v_data.get("environment", [])]
                        app_item.versions[v_name] = StoreAppVersionItem(
                            name=v_data.get("name", v_name),
                            compose_file=v_data.get("compose_file"),
                            environment=env_items,
                            script=v_data.get("script", {}),
                            download=v_data.get("download"),
                            default=v_data.get("default", False),
                            ref=v_data.get("ref"),
                        )
                    elif isinstance(v_data, StoreAppVersionItem):
                        app_item.versions[v_name] = v_data
                apps.append(app_item)
            else:
                apps.append(a)
        return StoreResponse(
            id=store.id,
            title=store.title,
            name=store.name,
            type=store.type,
            url=store.url,
            apps=apps,
            total=store.total or len(apps),
            created_at=store.created_at,
            updated_at=store.updated_at,
        )
