import os
import subprocess
import hashlib
import time
import asyncio
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, create_engine
from sqlalchemy.orm import Session as SyncSession

from app.crontab import models, schemas
from config.settings import settings

_sync_crontab_engine = create_engine(
    settings.CRONAB_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

DANGEROUS_COMMANDS = [
    "shutdown", "init 0", "init 6", "mkfs", "mke2fs",
    "passwd", "chpasswd", "--stdin", "mkfs.ext",
    "dd if=", "reboot", "halt", "poweroff",
]

logger = logging.getLogger(__name__)


def validate_command(command: str) -> Optional[str]:
    """校验命令是否包含危险指令，通过则返回 None，否则返回错误描述"""
    if not command or not command.strip():
        return "命令不能为空"
    for dangerous in DANGEROUS_COMMANDS:
        pattern = re.compile(rf'\b{re.escape(dangerous)}\b', re.IGNORECASE)
        if pattern.search(command):
            return f"The command contains dangerous instructions and execution is prohibited: {dangerous}"
    return None


def generate_echo() -> str:
    """生成唯一任务标识，用作脚本文件名"""
    raw = f"{time.time()}_crontab_{os.urandom(8).hex()}"
    return hashlib.md5(raw.encode()).hexdigest()


def generate_cron_expression(task) -> str:
    """将友好的周期配置转换为标准 cron 表达式"""
    t = task.task_type
    hour = getattr(task, 'where_hour', 0) or 0
    minute = getattr(task, 'where_minute', 0) or 0
    where1 = getattr(task, 'where1', 0) or 0
    week = getattr(task, 'where_week', 0) or 0

    if t == "day":
        return f"{minute} {hour} * * *"
    elif t == "day-n":
        return f"{minute} {hour} */{where1} * *" if where1 else f"{minute} {hour} * * *"
    elif t == "hour":
        return f"{minute} * * * *"
    elif t == "hour-n":
        return f"{minute} */{where1} * * *" if where1 else f"{minute} * * * *"
    elif t == "minute-n":
        return f"*/{where1} * * * *" if where1 else "* * * * *"
    elif t == "week":
        return f"{minute} {hour} * * {week}"
    elif t == "month":
        return f"{minute} {hour} {where1} * *" if where1 else f"{minute} {hour} 1 * *"
    return f"{minute} {hour} * * *"


def _get_cron_file_path() -> str:
    """获取系统 crontab 文件路径"""
    u_path = "/var/spool/cron/crontabs"
    u_file = os.path.join(u_path, "root")
    c_file = "/var/spool/cron/root"

    if os.path.exists("/usr/bin/apt-get"):
        return u_file
    if os.path.exists("/usr/bin/yum"):
        return c_file
    if os.path.exists(u_path):
        return u_file
    return c_file


def _get_script_path(echo: str) -> str:
    """获取任务脚本文件路径"""
    script_dir = settings.CRONAB_SCRIPT_PATH
    os.makedirs(script_dir, exist_ok=True)
    return os.path.join(script_dir, echo)


def _get_log_path(echo: str) -> str:
    """获取任务日志文件路径"""
    log_dir = settings.CRONAB_LOG_PATH
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"{echo}.log")


def _build_shell_script(command: str) -> str:
    """构建要写入脚本文件的 Shell 内容"""
    lines = [
        "#!/bin/bash",
        'PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin',
        "export PATH",
        f"cd {settings.CRONAB_SCRIPT_PATH}",
        "",
        'echo "----------------------------------------------------------------------------"',
        command,
        'EXIT_CODE=$?',
        'echo "----------------------------------------------------------------------------"',
        "echo \"\u2605[$(date '+%Y-%m-%d %H:%M:%S')] $([ $EXIT_CODE -eq 0 ] && echo Successful || echo Failed)\"",
        'echo "----------------------------------------------------------------------------"',
        'exit $EXIT_CODE',
    ]
    return "\n".join(lines) + "\n"


def _write_script_file(echo: str, command: str) -> str:
    """将任务脚本写入文件，返回脚本路径"""
    script_path = _get_script_path(echo)
    content = _build_shell_script(command)
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(script_path, 0o755)
        logger.info(f"计划任务脚本已写入: {script_path}")
    except Exception as e:
        logger.error(f"写入计划任务脚本失败: {e}")
        raise
    return script_path


def _delete_script_file(echo: str):
    """删除任务脚本文件及相关日志"""
    script_path = _get_script_path(echo)
    log_path = _get_log_path(echo)
    for path in [script_path, log_path]:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"删除文件失败 {path}: {e}")


def _sync_crontab_entry(echo: str, cron_expr: str, action: str = "add"):
    """同步系统 crontab 条目 (add/remove)"""
    cron_file = _get_cron_file_path()
    marker = f"# blackpot_crontab_{echo}"
    cron_line = f"{cron_expr} {_get_script_path(echo)} >> {_get_log_path(echo)} 2>&1"

    try:
        existing = ""
        if os.path.exists(cron_file):
            with open(cron_file, "r", encoding="utf-8") as f:
                existing = f.read()

        lines = existing.splitlines()
        new_lines = []
        skip_next = False
        for line in lines:
            if marker in line:
                skip_next = True
                continue
            if skip_next:
                skip_next = False
                continue
            new_lines.append(line)

        if action == "add":
            new_lines.append(marker)
            new_lines.append(cron_line)

        content = "\n".join(new_lines) + "\n"
        with open(cron_file, "w", encoding="utf-8") as f:
            f.write(content)

        os.chmod(cron_file, 0o600)
        logger.info(f"crontab 条目已{'添加' if action == 'add' else '移除'}: {echo}")
    except Exception as e:
        logger.error(f"同步 crontab 条目失败: {e}")
        raise


async def _reload_crond():
    """重载 crond 服务使配置生效"""
    try:
        if os.path.exists("/etc/init.d/crond"):
            proc = await asyncio.create_subprocess_exec("/etc/init.d/crond", "reload", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()
        elif os.path.exists("/etc/init.d/cron"):
            proc = await asyncio.create_subprocess_exec("service", "cron", "restart", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()
        else:
            proc = await asyncio.create_subprocess_exec("systemctl", "reload", "crond", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()
        logger.info("crond 服务已重载")
    except Exception as e:
        logger.warning(f"重载 crond 服务失败: {e}")


async def create_task(db: AsyncSession, task_in: schemas.CrontabTaskCreate) -> models.CrontabTask:
    """创建计划任务"""
    err = validate_command(task_in.command)
    if err:
        raise ValueError(err)

    echo = generate_echo()
    cron_expr = generate_cron_expression(task_in)

    db_task = models.CrontabTask(
        name=task_in.name,
        task_type=task_in.task_type,
        command=task_in.command,
        where1=task_in.where1 or 0,
        where_hour=task_in.where_hour or 0,
        where_minute=task_in.where_minute or 0,
        where_week=task_in.where_week or 0,
        status=task_in.status if task_in.status is not None else 1,
        save=task_in.save if task_in.save is not None else 3,
        description=task_in.description,
        echo=echo,
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    _write_script_file(echo, task_in.command)
    if db_task.status == 1:
        _sync_crontab_entry(echo, cron_expr, action="add")
        await _reload_crond()

    logger.info(f"计划任务已创建: {db_task.name} (echo={echo})")
    return db_task


async def update_task(db: AsyncSession, task_id: int, task_in: schemas.CrontabTaskUpdate) -> Optional[models.CrontabTask]:
    """更新计划任务"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return None

    update_data = task_in.dict(exclude_unset=True)
    if not update_data:
        return db_task

    if "command" in update_data:
        err = validate_command(update_data["command"])
        if err:
            raise ValueError(err)

    old_cron_expr = generate_cron_expression(db_task)

    for field, value in update_data.items():
        setattr(db_task, field, value)

    await db.commit()
    await db.refresh(db_task)

    new_cron_expr = generate_cron_expression(db_task)
    _write_script_file(db_task.echo, db_task.command)

    _sync_crontab_entry(db_task.echo, old_cron_expr, action="remove")
    if db_task.status == 1:
        _sync_crontab_entry(db_task.echo, new_cron_expr, action="add")
    await _reload_crond()

    logger.info(f"计划任务已更新: {db_task.name}")
    return db_task


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    """删除计划任务"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return False

    cron_expr = generate_cron_expression(db_task)
    _sync_crontab_entry(db_task.echo, cron_expr, action="remove")
    await _reload_crond()
    _delete_script_file(db_task.echo)

    await db.delete(db_task)
    await db.commit()

    logger.info(f"计划任务已删除: {db_task.name}")
    return True


async def get_task(db: AsyncSession, task_id: int) -> Optional[models.CrontabTask]:
    """获取单个任务"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    return result.scalar_one_or_none()


async def get_tasks(
    db: AsyncSession, skip: int = 0, limit: int = 100, status: Optional[int] = None
) -> Tuple[List[models.CrontabTask], int]:
    """获取任务列表，支持按状态筛选"""
    query = select(models.CrontabTask)
    count_query = select(models.CrontabTask.id)

    if status is not None:
        query = query.filter(models.CrontabTask.status == status)
        count_query = count_query.filter(models.CrontabTask.status == status)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    result = await db.execute(
        query.order_by(desc(models.CrontabTask.created_at)).offset(skip).limit(limit)
    )
    tasks = result.scalars().all()
    return tasks, total


async def toggle_task_status(db: AsyncSession, task_id: int) -> Optional[models.CrontabTask]:
    """切换任务启用/停用状态"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return None

    old_status = db_task.status
    db_task.status = 0 if db_task.status == 1 else 1
    await db.commit()
    await db.refresh(db_task)

    cron_expr = generate_cron_expression(db_task)
    if old_status == 1:
        _sync_crontab_entry(db_task.echo, cron_expr, action="remove")
    if db_task.status == 1:
        _sync_crontab_entry(db_task.echo, cron_expr, action="add")
    await _reload_crond()

    logger.info(f"计划任务状态已切换: {db_task.name} -> {'启用' if db_task.status == 1 else '停用'}")
    return db_task


async def execute_task_now(db: AsyncSession, task_id: int) -> dict:
    """立即执行指定任务"""

    def _sync_execute(tid: int) -> dict:
        sync_session = SyncSession(_sync_crontab_engine)
        try:
            from sqlalchemy import select as sync_select
            result = sync_session.execute(sync_select(models.CrontabTask).filter(models.CrontabTask.id == tid))
            db_task = result.scalar_one_or_none()
            if not db_task:
                raise ValueError("任务不存在")

            cmd_err = validate_command(db_task.command)
            if cmd_err:
                raise ValueError(cmd_err)

            script_path = _get_script_path(db_task.echo)
            log_path = _get_log_path(db_task.echo)
            _write_script_file(db_task.echo, db_task.command)

            started_at = datetime.now()
            try:
                proc = subprocess.run(
                    ["/bin/bash", script_path],
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
                output = proc.stdout + proc.stderr
                success = proc.returncode == 0
            except subprocess.TimeoutExpired:
                output = "任务执行超时（1小时）"
                success = False
            except Exception as e:
                output = f"执行失败: {str(e)}"
                success = False

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{output}\n")

            db_task.last_run_time = started_at
            db_task.last_result = "成功" if success else f"失败: {output[:200]}"
            sync_session.commit()

            return {
                "task_id": tid,
                "name": db_task.name,
                "started_at": started_at,
                "output": output,
                "success": success,
            }
        finally:
            sync_session.close()

    return await asyncio.to_thread(_sync_execute, task_id)


async def get_task_log(db: AsyncSession, task_id: int, lines: int = 100) -> Optional[dict]:
    """获取任务执行日志"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return None

    log_path = _get_log_path(db_task.echo)
    if not os.path.exists(log_path):
        return {"echo": db_task.echo, "content": [], "total_lines": 0}

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = f.readlines()

    total = len(all_lines)
    tail = all_lines[-lines:] if total > lines else all_lines
    tail = [line.rstrip("\n").rstrip("\r") for line in tail]

    return {
        "echo": db_task.echo,
        "content": tail,
        "total_lines": total,
    }


async def clear_task_log(db: AsyncSession, task_id: int) -> bool:
    """清空任务执行日志"""
    result = await db.execute(select(models.CrontabTask).filter(models.CrontabTask.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        return False

    log_path = _get_log_path(db_task.echo)
    if os.path.exists(log_path):
        try:
            open(log_path, "w", encoding="utf-8").close()
            logger.info(f"计划任务日志已清空: {db_task.name}")
        except Exception as e:
            logger.error(f"清空计划任务日志失败: {e}")
            raise
    return True
