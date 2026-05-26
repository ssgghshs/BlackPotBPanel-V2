from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from app.script.models import Script, ScriptType
from app.script.schemas import ScriptResponse, ScriptCreate, ScriptUpdate, ScriptTypeCreate, ScriptTypeUpdate, ScriptsResponse
import logging

logger = logging.getLogger(__name__)


async def get_scripts(db: AsyncSession, skip: int = 0, limit: int = 100) -> ScriptsResponse:
    """获取脚本列表"""
    # 使用selectinload预加载script_type关系
    result = await db.execute(
        select(Script)
        .options(selectinload(Script.script_type))
        .offset(skip)
        .limit(limit)
    )
    scripts = list(result.scalars().all())
    
    # 获取总数量
    count_result = await db.execute(select(func.count(Script.script_id)))
    total = count_result.scalar_one()
    
    # 转换为响应模型
    script_responses = []
    for script in scripts:
        script_dict = script.to_dict()
        script_responses.append(ScriptResponse(**script_dict))
    
    return ScriptsResponse(
        items=script_responses,
        total=total,
        skip=skip,
        limit=limit
    )


async def get_script_by_id(db: AsyncSession, script_id: int) -> Optional[Script]:
    """根据ID获取脚本"""
    result = await db.execute(
        select(Script)
        .options(selectinload(Script.script_type))
        .where(Script.script_id == script_id)
    )
    return result.scalar_one_or_none()


async def get_script_types(db: AsyncSession) -> List[ScriptType]:
    """获取所有脚本类型"""
    result = await db.execute(select(ScriptType))
    return list(result.scalars().all())


async def get_script_type_by_id(db: AsyncSession, script_type_id: int) -> Optional[ScriptType]:
    """根据ID获取脚本类型"""
    result = await db.execute(select(ScriptType).where(ScriptType.id == script_type_id))
    return result.scalar_one_or_none()


async def create_script(db: AsyncSession, script: ScriptCreate) -> Script:
    """创建新脚本"""
    db_script = Script(
        name=script.name,
        script_type_id=script.script_type_id,
        script_context=script.script_context,
        description=script.description,
        requires_params=script.requires_params,  # 添加参数字段
        params_description=script.params_description  # 添加参数描述字段
    )
    db.add(db_script)
    await db.commit()
    await db.refresh(db_script)
    # 预加载script_type关系以避免序列化时的greenlet错误
    result = await db.execute(
        select(Script)
        .options(selectinload(Script.script_type))
        .where(Script.script_id == db_script.script_id)
    )
    return result.scalar_one_or_none()


async def update_script(db: AsyncSession, script_id: int, script_update: ScriptUpdate) -> Optional[Script]:
    """更新脚本"""
    db_script = await get_script_by_id(db, script_id)
    if not db_script:
        return None
    
    # 更新脚本属性
    update_data = script_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_script, key, value)
    
    await db.commit()
    await db.refresh(db_script)
    # 预加载script_type关系以避免序列化时的greenlet错误
    result = await db.execute(
        select(Script)
        .options(selectinload(Script.script_type))
        .where(Script.script_id == db_script.script_id)
    )
    return result.scalar_one_or_none()


async def delete_script(db: AsyncSession, script_id: int) -> bool:
    """删除脚本"""
    db_script = await get_script_by_id(db, script_id)
    if not db_script:
        return False
    
    await db.delete(db_script)
    await db.commit()
    return True


async def create_script_type(db: AsyncSession, script_type: ScriptTypeCreate) -> ScriptType:
    """创建新脚本类型"""
    db_script_type = ScriptType(
        type_name=script_type.type_name,
        interpreter_path=script_type.interpreter_path,
        description=script_type.description
    )
    db.add(db_script_type)
    await db.commit()
    await db.refresh(db_script_type)
    return db_script_type


async def update_script_type(db: AsyncSession, script_type_id: int, script_type_update: ScriptTypeUpdate) -> Optional[ScriptType]:
    """更新脚本类型"""
    db_script_type = await get_script_type_by_id(db, script_type_id)
    if not db_script_type:
        return None
    
    # 更新脚本类型属性
    update_data = script_type_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_script_type, key, value)
    
    await db.commit()
    await db.refresh(db_script_type)
    return db_script_type


async def delete_script_type(db: AsyncSession, script_type_id: int) -> bool:
    """删除脚本类型"""
    db_script_type = await get_script_type_by_id(db, script_type_id)
    if not db_script_type:
        return False
    
    await db.delete(db_script_type)
    await db.commit()
    return True

