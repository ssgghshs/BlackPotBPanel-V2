from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from config.database import get_firewall_db
from middleware.auth import get_current_active_user

import logging

from app.firewall.schemas import (
    FirewallInfoResponse,
    FirewallSetStatusRequest,
    FirewallSetPingRequest,
    FirewallOperationResponse,
    FirewallPortRuleDeleteRequest,
    FirewallIpRuleDeleteRequest,
    PortRuleCreate,
    PortRuleUpdate,
    PortRuleResponse,
    PortRuleList,
    MergedPortRuleItem,
    MergedPortRuleList,
    IpRuleCreate,
    IpRuleUpdate,
    IpRuleResponse,
    IpRuleList,
    MergedIpRuleItem,
    MergedIpRuleList,
    ForwardCreate,
    ForwardUpdate,
    ForwardResponse,
    ForwardList,
    CountryInfo,
    CountryRuleCreate,
    CountryRuleUpdate,
    CountryRuleResponse,
    CountryRuleList,
    CountryRuleDeleteRequest,
    CountryRuleCreateResponse,
    CountryRuleBatchDeleteRequest,
)
from app.firewall.service import FirewallService
from app.firewall.models import FirewallRule, FirewallIpRule, FirewallForward, FirewallCountryRule

router = APIRouter(prefix="/firewall", tags=["firewall"])

logger = logging.getLogger(__name__)


@router.get("/info", response_model=FirewallInfoResponse, summary="获取防火墙统计信息")
async def get_firewall_info(
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """获取防火墙统计信息，包括端口规则数、IP规则数、转发规则数、禁Ping状态等"""
    return await FirewallService.get_firewall_info(db)


@router.post("/status/set", response_model=FirewallOperationResponse, summary="设置防火墙状态")
async def set_firewall_status(
    req: FirewallSetStatusRequest,
    current_user = Depends(get_current_active_user),
):
    """启动、停止、重启或重载防火墙

    - **status**: start - 启动, stop - 停止, restart - 重启, reload - 重载
    """
    try:
        return await FirewallService.set_status(req.status)
    except Exception as e:
        logger.error(f"设置防火墙状态失败: {str(e)}")
        return FirewallOperationResponse(success=False, message=f"操作失败: {str(e)}")


@router.post("/ping/set", response_model=FirewallOperationResponse, summary="设置禁Ping")
async def set_ping(
    req: FirewallSetPingRequest,
    current_user = Depends(get_current_active_user),
):
    """设置是否禁Ping

    - **status**: 0 - 允许Ping, 1 - 禁止Ping
    """
    return await FirewallService.set_ping(req.status)


@router.get("/port_rules/list", response_model=MergedPortRuleList, summary="获取端口规则列表")
async def get_port_rules(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    query: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """获取端口放行规则列表（合并系统防火墙+数据库），支持分页和搜索

    返回的每条规则包含:
    - **id**: 数据库ID，0表示仅存在于系统防火墙中
    - **stype**: 0-系统原生规则, 1-面板托管规则
    - **status**: -1无法检测, 0未监听, 2监听中
    """
    items, total = await FirewallService.get_port_rules(db, skip=skip, limit=limit, query=query)
    return MergedPortRuleList(items=items, total=total, skip=skip, limit=limit)


@router.post("/port_rules/create", response_model=PortRuleResponse, summary="创建端口规则")
async def create_port_rule(
    rule_data: PortRuleCreate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """添加端口放行规则（同时写入系统防火墙和数据库）

    - **port**: 端口号或端口范围，如 80 或 39000-40000
    - **protocol**: 协议，tcp/udp/tcp/udp
    - **strategy**: 策略，accept/drop/reject
    - **address**: 源地址，默认 all
    - **chain**: 链，INPUT/OUTPUT
    - **brief**: 备注说明（可选）
    """
    rule = await FirewallService.create_port_rule(db, rule_data)
    return PortRuleResponse(
        id=rule.id,
        port=rule.port,
        protocol=rule.protocol,
        strategy=rule.strategy,
        address=rule.address,
        chain=rule.chain,
        brief=rule.brief,
        addtime=rule.addtime,
    )


@router.post("/port_rules/delete", response_model=FirewallOperationResponse, summary="删除端口规则")
async def delete_port_rule(
    req: FirewallPortRuleDeleteRequest,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """删除指定的端口放行规则

    支持删除面板托管规则（id>0）和系统原生规则（id=0）
    """
    try:
        await FirewallService.delete_port_rule(db, req.id, req.port, req.protocol, req.chain)
        return FirewallOperationResponse(success=True, message="端口规则删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除端口规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除端口规则失败: {str(e)}")


@router.post("/port_rules/{rule_id}/update", response_model=PortRuleResponse, summary="修改端口规则")
async def update_port_rule(
    rule_id: int,
    rule_data: PortRuleUpdate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """修改端口放行规则（同时更新系统防火墙和数据库）

    只传需要修改的字段，未传字段保持不变
    """
    rule = await FirewallService.update_port_rule(db, rule_id, rule_data)
    return PortRuleResponse(
        id=rule.id,
        port=rule.port,
        protocol=rule.protocol,
        strategy=rule.strategy,
        address=rule.address,
        chain=rule.chain,
        brief=rule.brief,
        addtime=rule.addtime,
    )


@router.get("/ip_rules/list", response_model=MergedIpRuleList, summary="获取IP规则列表")
async def get_ip_rules(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    query: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """获取IP规则列表（合并系统防火墙+数据库），支持分页和搜索

    返回的每条规则包含:
    - **id**: 数据库ID，0表示仅存在于系统防火墙中
    - **stype**: 0-系统原生规则, 1-面板托管规则
    """
    items, total = await FirewallService.get_ip_rules(db, skip=skip, limit=limit, query=query)
    return MergedIpRuleList(items=items, total=total, skip=skip, limit=limit)


@router.post("/ip_rules/create", response_model=IpRuleResponse, summary="创建IP规则")
async def create_ip_rule(
    rule_data: IpRuleCreate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """添加IP规则（同时写入系统防火墙和数据库）

    - **address**: IP地址或CIDR，如 192.168.1.100 或 10.0.0.0/24
    - **strategy**: 策略，drop/accept/reject
    - **chain**: 链，INPUT/OUTPUT
    - **brief**: 备注说明（可选）
    """
    rule = await FirewallService.create_ip_rule(db, rule_data)
    return IpRuleResponse(
        id=rule.id,
        address=rule.address,
        strategy=rule.strategy,
        chain=rule.chain,
        brief=rule.brief,
        addtime=rule.addtime,
    )


@router.post("/ip_rules/delete", response_model=FirewallOperationResponse, summary="删除IP规则")
async def delete_ip_rule(
    req: FirewallIpRuleDeleteRequest,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """删除指定的IP规则

    支持删除面板托管规则（id>0）和系统原生规则（id=0）
    """
    try:
        await FirewallService.delete_ip_rule(db, req.id, req.address, req.strategy)
        return FirewallOperationResponse(success=True, message="IP规则删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除IP规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除IP规则失败: {str(e)}")


@router.post("/ip_rules/{rule_id}/update", response_model=IpRuleResponse, summary="修改IP规则")
async def update_ip_rule(
    rule_id: int,
    rule_data: IpRuleUpdate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """修改IP规则（同时更新系统防火墙和数据库）

    只传需要修改的字段，未传字段保持不变
    """
    rule = await FirewallService.update_ip_rule(db, rule_id, rule_data)
    return IpRuleResponse(
        id=rule.id,
        address=rule.address,
        strategy=rule.strategy,
        chain=rule.chain,
        brief=rule.brief,
        addtime=rule.addtime,
    )


@router.get("/forwards/list", response_model=ForwardList, summary="获取端口转发规则列表")
async def get_forwards(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """获取端口转发规则列表，支持分页"""
    forwards, total = await FirewallService.get_forwards(db, skip=skip, limit=limit)
    items = [
        ForwardResponse(
            id=f.id,
            S_Address=f.S_Address,
            S_Port=f.S_Port,
            T_Address=f.T_Address,
            T_Port=f.T_Port,
            Protocol=f.Protocol,
            brief=f.brief,
            addtime=f.addtime.strftime("%Y-%m-%d %H:%M:%S") if f.addtime else "--",
        )
        for f in forwards
    ]
    return ForwardList(items=items, total=total, skip=skip, limit=limit)


@router.post("/forwards/create", response_model=ForwardResponse, summary="创建端口转发规则")
async def create_forward(
    forward_data: ForwardCreate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """添加端口转发规则

    - **S_Address**: 源地址，默认 0.0.0.0
    - **S_Port**: 源端口
    - **T_Address**: 目标地址
    - **T_Port**: 目标端口
    - **Protocol**: 协议，tcp/udp
    - **brief**: 备注说明（可选）
    """
    forward = await FirewallService.create_forward(db, forward_data)
    return ForwardResponse(
        id=forward.id,
        S_Address=forward.S_Address,
        S_Port=forward.S_Port,
        T_Address=forward.T_Address,
        T_Port=forward.T_Port,
        Protocol=forward.Protocol,
        brief=forward.brief,
        addtime=forward.addtime.strftime("%Y-%m-%d %H:%M:%S") if forward.addtime else "--",
    )


@router.post("/forwards/{forward_id}/delete", response_model=FirewallOperationResponse, summary="删除端口转发规则")
async def delete_forward(
    forward_id: int,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """删除指定的端口转发规则"""
    try:
        await FirewallService.delete_forward(db, forward_id)
        return FirewallOperationResponse(success=True, message="端口转发规则删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除端口转发规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除端口转发规则失败: {str(e)}")


@router.post("/forwards/{forward_id}/update", response_model=ForwardResponse, summary="修改端口转发规则")
async def update_forward(
    forward_id: int,
    forward_data: ForwardUpdate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """修改端口转发规则

    只传需要修改的字段，未传字段保持不变
    """
    forward = await FirewallService.update_forward(db, forward_id, forward_data)
    return ForwardResponse(
        id=forward.id,
        S_Address=forward.S_Address,
        S_Port=forward.S_Port,
        T_Address=forward.T_Address,
        T_Port=forward.T_Port,
        Protocol=forward.Protocol,
        brief=forward.brief,
        addtime=forward.addtime.strftime("%Y-%m-%d %H:%M:%S") if forward.addtime else "--",
    )


# ==================== 地区规则 ====================


@router.get("/country_rules/countries", response_model=List[CountryInfo], summary="获取可用国家列表")
async def get_countries(
    current_user = Depends(get_current_active_user),
):
    """从 GeoIP 数据库获取所有可用的国家/地区列表

    返回国家代码和中文名称，可用于创建地区规则时的下拉选择
    """
    return await FirewallService.get_available_countries()


@router.get("/country_rules/list", response_model=CountryRuleList, summary="获取地区规则列表")
async def get_country_rules(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    query: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """获取地区规则列表，支持分页和搜索"""
    rules, total = await FirewallService.get_country_rules(db, skip=skip, limit=limit, query=query)
    items = [
        CountryRuleResponse(
            id=r.id,
            country_code=r.country_code,
            country_name=r.country_name,
            strategy=r.strategy,
            ports=r.ports or "",
            brief=r.brief,
            addtime=r.addtime.strftime("%Y-%m-%d %H:%M:%S") if r.addtime else "--",
        )
        for r in rules
    ]
    return CountryRuleList(items=items, total=total, skip=skip, limit=limit)


@router.post("/country_rules/create", response_model=CountryRuleCreateResponse, summary="创建地区规则")
async def create_country_rule(
    rule_data: CountryRuleCreate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """创建地区规则

    根据选定的国家/地区，自动将该地区的所有 IP 段加入 ipset，
    并添加 iptables 规则实现地区级别的访问控制。

    - **country_codes**: 国家代码列表，如 ["US", "GB"]
    - **strategy**: accept - 放行, drop - 禁止
    - **ports**: 端口，空表示所有端口，多个用逗号分隔
    - **brief**: 备注说明（可选）
    """
    created_rules = await FirewallService.create_country_rule(db, rule_data)
    return CountryRuleCreateResponse(
        success=True,
        message=f"已创建 {len(created_rules)} 条地区规则",
        data=[
            CountryRuleResponse(
                id=r.id,
                country_code=r.country_code,
                country_name=r.country_name,
                strategy=r.strategy,
                ports=r.ports or "",
                brief=r.brief,
                addtime=r.addtime.strftime("%Y-%m-%d %H:%M:%S") if r.addtime else "--",
            )
            for r in created_rules
        ],
    )


@router.post("/country_rules/delete", response_model=FirewallOperationResponse, summary="删除地区规则")
async def delete_country_rule(
    req: CountryRuleDeleteRequest,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """删除指定的地区规则

    从数据库和系统防火墙（ipset + iptables）中删除规则
    """
    try:
        await FirewallService.delete_country_rule(db, req.id, req.country_code, req.strategy, req.ports)
        return FirewallOperationResponse(success=True, message="地区规则删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除地区规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除地区规则失败: {str(e)}")


@router.post("/country_rules/batch_delete", response_model=FirewallOperationResponse, summary="批量删除地区规则")
async def batch_delete_country_rules(
    req: CountryRuleBatchDeleteRequest,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """批量删除地区规则

    从数据库和系统防火墙（ipset + iptables）中批量删除规则
    """
    try:
        deleted = await FirewallService.batch_delete_country_rules(db, req.items)
        return FirewallOperationResponse(success=True, message=f"已删除 {deleted} 条地区规则")
    except Exception as e:
        logger.error(f"批量删除地区规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量删除地区规则失败: {str(e)}")


@router.post("/country_rules/{rule_id}/update", response_model=CountryRuleResponse, summary="修改地区规则")
async def update_country_rule(
    rule_id: int,
    rule_data: CountryRuleUpdate,
    db: AsyncSession = Depends(get_firewall_db),
    current_user = Depends(get_current_active_user),
):
    """修改地区规则

    只传需要修改的字段，未传字段保持不变。
    当策略或端口变化时，会自动更新 iptables 规则。
    """
    rule = await FirewallService.update_country_rule(db, rule_id, rule_data)
    return CountryRuleResponse(
        id=rule.id,
        country_code=rule.country_code,
        country_name=rule.country_name,
        strategy=rule.strategy,
        ports=rule.ports or "",
        brief=rule.brief,
        addtime=rule.addtime.strftime("%Y-%m-%d %H:%M:%S") if rule.addtime else "--",
    )
