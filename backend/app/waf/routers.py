from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from middleware.auth import get_current_active_user
from config.database import get_waf_db
from app.user.schemas import RoleEnum
from app.waf import schemas, service
from app.waf.manager_service import WAFManagerService
from app.waf.log_service import WAFLogService
from app.waf.rules_service import WAFRulesService
from app.waf.site_service import WAFSiteService
from app.waf.overview_service import WAFOverviewService
from app.waf.intelligence_service import ThreatIntelService

router = APIRouter(prefix="/waf", tags=["waf"])

logger = logging.getLogger(__name__)



@router.post("/ssl-certs/create", response_model=schemas.SSLCertResponse, status_code=status.HTTP_201_CREATED)
async def create_ssl_cert(
    ssl_data: schemas.SSLCertCreate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_waf_db)
):
    """创建SSL证书"""
    try:
        # 创建SSL证书
        cert = await service.create_ssl_cert(
            db=db,
            name=ssl_data.name,
            key=ssl_data.key,
            pem=ssl_data.pem
        )

        return schemas.SSLCertResponse(
            id=cert.id,
            name=cert.name,
            created_at=cert.created_at,
            updated_at=cert.updated_at,
            message="success create ssl cert"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建SSL证书失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"create ssl cert failed: {str(e)}"
        )


@router.get("/ssl-certs/list", response_model=schemas.SSLCertListResponse)
async def get_ssl_certs(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_waf_db)
):
    """获取SSL证书列表"""
    try:
        # 获取SSL证书列表
        certs = await service.get_ssl_certs(db=db, skip=skip, limit=limit)
        total = await service.get_ssl_certs_count(db=db)

        return schemas.SSLCertListResponse(
            certs=certs,
            total=total,
            message="success get ssl certs list"
        )
    except Exception as e:
        logger.error(f"获取SSL证书列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"get ssl certs list failed: {str(e)}"
        )


@router.get("/ssl-certs/{cert_id}/detail", response_model=schemas.SSLCertDetailResponse)
async def get_ssl_cert_detail(
    cert_id: int,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_waf_db)
):
    """获取SSL证书详情（包含key和pem内容）"""
    try:
        # 获取SSL证书详情
        cert_detail = await service.get_ssl_cert_detail(db=db, cert_id=cert_id)
        
        if not cert_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSL证书ID {cert_id} 不存在"
            )

        return schemas.SSLCertDetailResponse(
            id=cert_detail["id"],
            name=cert_detail["name"],
            domain=cert_detail["domain"],
            issuer=cert_detail["issuer"],
            expiry_date=cert_detail["expiry_date"],
            key=cert_detail["key"],
            pem=cert_detail["pem"],
            created_at=cert_detail["created_at"],
            updated_at=cert_detail["updated_at"],
            message="success get ssl cert detail"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SSL证书详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"get ssl cert detail failed: {str(e)}"
        )


@router.post("/ssl-certs/{cert_id}/update", response_model=schemas.SSLCertResponse)
async def update_ssl_cert(
    cert_id: int,
    ssl_data: schemas.SSLCertUpdate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_waf_db)
):
    """更新SSL证书"""
    try:
        # 更新SSL证书
        cert = await service.update_ssl_cert(
            db=db,
            cert_id=cert_id,
            key=ssl_data.key,
            pem=ssl_data.pem
        )

        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSL证书ID {cert_id} 不存在"
            )

        return schemas.SSLCertResponse(
            id=cert.id,
            name=cert.name,
            created_at=cert.created_at,
            updated_at=cert.updated_at,
            message="success update ssl cert"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新SSL证书失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"update ssl cert failed: {str(e)}"
        )


@router.post("/ssl-certs/{cert_id}/delete", response_model=schemas.SSLCertDeleteResponse)
async def delete_ssl_cert(
    cert_id: int,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_waf_db)
):
    """删除SSL证书"""
    try:
        # 删除SSL证书
        success = await service.delete_ssl_cert(db=db, cert_id=cert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSL证书ID {cert_id} 不存在"
            )

        return schemas.SSLCertDeleteResponse(
            message="success delete ssl cert"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除SSL证书失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"delete ssl cert failed: {str(e)}"
        )


@router.get("/waf/status", response_model=schemas.WAFContainerStatus, summary="获取WAF容器状态")
async def get_waf_container_status(
    current_user = Depends(get_current_active_user)
):
    """获取WAF容器状态
    
    - 返回容器状态: running, stopped, paused, restarting, dead
    """
    return await WAFManagerService.get_waf_container_status()


@router.post("/waf/operate", response_model=schemas.WAFContainerActionResponse, summary="操作WAF容器")
async def operate_waf_container(
    action_data: schemas.WAFContainerAction,
    current_user = Depends(get_current_active_user)
):
    """操作WAF容器（启动/停止/重启）
    
    - action: 操作类型，支持 'start' 或 'stop'
    """
    return await WAFManagerService.operate_waf_container(action_data.action)


@router.get("/waf/exists", response_model=schemas.WAFContainerExistsResponse, summary="检测WAF容器是否存在")
async def check_waf_container_exists(
    current_user = Depends(get_current_active_user)
):
    """检测WAF容器是否存在（是否安装）

    - exists: 容器是否存在
    - container_name: 容器名称
    - 用于判断WAF是否已安装部署
    """
    return await WAFManagerService.check_container_exists()


@router.get("/logs/list", response_model=schemas.WAFLogListResponse, summary="获取WAF拦截日志")
async def get_waf_logs(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """获取WAF拦截日志
    
    - skip: 跳过的日志条数
    - limit: 返回的日志条数
    """
    return await WAFLogService.get_waf_logs(skip=skip, limit=limit)


@router.get("/logs/bot/list", response_model=schemas.WAFBotLogListResponse, summary="获取WAF BOT验证日志")
async def get_waf_bot_logs(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """获取WAF BOT验证日志
    
    - skip: 跳过的日志条数
    - limit: 返回的日志条数
    """
    return await WAFLogService.get_waf_bot_logs(skip=skip, limit=limit)


@router.get("/logs/blackwhite/list", response_model=schemas.WAFBlackWhiteLogListResponse, summary="获取WAF黑白名单日志")
async def get_waf_blackwhite_logs(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """获取WAF黑白名单日志
    
    - skip: 跳过的日志条数
    - limit: 返回的日志条数
    """
    return await WAFLogService.get_waf_blackwhite_logs(skip=skip, limit=limit)


@router.post("/logs/clean", response_model=schemas.WAFLogCleanResponse, summary="清理WAF拦截日志")
async def clean_waf_logs(
    clean_request: schemas.WAFLogCleanRequest,
    current_user = Depends(get_current_active_user)
):
    """清理WAF拦截日志
    
    - days: 保留最近的天数，不指定则清空所有日志
    """
    return await WAFLogService.clean_waf_logs(days=clean_request.days)


@router.post("/logs/bot/clean", response_model=schemas.WAFLogCleanResponse, summary="清理WAF BOT验证日志")
async def clean_waf_bot_logs(
    clean_request: schemas.WAFLogCleanRequest,
    current_user = Depends(get_current_active_user)
):
    """清理WAF BOT验证日志
    
    - days: 保留最近的天数，不指定则清空所有日志
    """
    return await WAFLogService.clean_waf_bot_logs(days=clean_request.days)


@router.post("/logs/blackwhite/clean", response_model=schemas.WAFLogCleanResponse, summary="清理WAF黑白名单日志")
async def clean_waf_blackwhite_logs(
    clean_request: schemas.WAFLogCleanRequest,
    current_user = Depends(get_current_active_user)
):
    """清理WAF黑白名单日志
    
    - days: 保留最近的天数，不指定则清空所有日志
    """
    return await WAFLogService.clean_waf_blackwhite_logs(days=clean_request.days)


@router.get("/overview", response_model=schemas.WAFOverviewResponse, summary="获取WAF基本概况")
async def get_waf_overview(
    current_user = Depends(get_current_active_user)
):
    """获取WAF基本概况
    
    返回WAF的基本统计信息，包括：
    - 访问日志：请求次数、错误次数
    - WAF拦截日志：拦截次数、攻击IP数、记录次数
    - 黑白名单日志：IP黑名单拦截数、记录数
    - BOT验证日志：验证通过数、挑战数、失败数
    """
    return await WAFLogService.get_waf_overview()


@router.get("/qps", response_model=schemas.WAFQPSResponse, summary="获取WAF QPS和请求统计")
async def get_waf_qps(
    current_user = Depends(get_current_active_user)
):
    """获取WAF QPS和请求统计 - 实时监控数据
    
    返回最近2分钟的实时监控数据，每5秒一个数据点，包括：
    - data.nodes: 监控数据节点数组
      - qps: QPS值（每秒请求数）
      - requests: 该时间段的请求数
      - blocks: 该时间段的拦截数
      - time: 时间点 (HH:MM:SS)
    - err: 错误信息（如果有）
    - msg: 响应消息
    """
    return WAFOverviewService.get_waf_qps()


@router.get("/client-stats", response_model=schemas.WAFClientStatsResponse, summary="获取客户端统计和响应状态统计")
async def get_client_stats(
    current_user = Depends(get_current_active_user)
):
    """获取客户端统计和响应状态统计
    
    返回WAF的客户端和响应状态统计信息，包括：
    - operating_systems: 操作系统统计（按请求数从多到少排序）
    - browsers: 浏览器统计（按请求数从多到少排序）
    - status_codes: HTTP状态码统计（按请求数从多到少排序）
    """
    return WAFOverviewService.get_client_stats()


@router.get("/rules/ipblackwhite/list", response_model=schemas.WAFBlackWhiteListResponse, summary="获取IP黑白名单列表")
async def get_blackwhite_list(
    current_user = Depends(get_current_active_user)
):
    """获取IP黑白名单列表
    
    从配置文件中读取IP黑白名单配置，包括白名单和黑名单的详细信息
    """
    return WAFRulesService.get_blackwhite_list()


@router.post("/rules/ipblackwhite/{list_type}/{group_name}/update", response_model=schemas.WAFBlackWhiteListResponse, summary="编辑指定IP组")
async def update_blackwhite_group(
    list_type: str,
    group_name: str,
    update_data: schemas.WAFBlackWhiteGroupUpdate,
    current_user = Depends(get_current_active_user)
):
    """编辑指定IP组
    
    Args:
        list_type: 列表类型，'white' 或 'black'
        group_name: 组名称
        update_data: 更新数据
        
    Returns:
        更新后的黑白名单配置
    """
    # 验证list_type参数
    if list_type not in ['white', 'black']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list_type. Must be 'white' or 'black'"
        )
    
    # 转换更新数据为字典
    update_dict = update_data.dict(exclude_unset=True)
    
    return WAFRulesService.update_blackwhite_group(list_type, group_name, update_dict)


@router.post("/rules/ipblackwhite/{list_type}/{group_name}/delete", response_model=schemas.WAFBlackWhiteListResponse, summary="删除指定IP组")
async def delete_blackwhite_group(
    list_type: str,
    group_name: str,
    current_user = Depends(get_current_active_user)
):
    """删除指定IP组
    
    Args:
        list_type: 列表类型，'white' 或 'black'
        group_name: 组名称
        
    Returns:
        删除后的黑白名单配置
    """
    # 验证list_type参数
    if list_type not in ['white', 'black']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list_type. Must be 'white' or 'black'"
        )
    
    return WAFRulesService.delete_blackwhite_group(list_type, group_name)


@router.post("/rules/ipblackwhite/{list_type}/add", response_model=schemas.WAFBlackWhiteListResponse, summary="添加IP组")
async def add_blackwhite_group(
    list_type: str,
    group_data: schemas.WAFBlackWhiteGroupCreate,
    current_user = Depends(get_current_active_user)
):
    """添加IP组
    
    Args:
        list_type: 列表类型，'white' 或 'black'
        group_data: 组数据
        
    Returns:
        添加后的黑白名单配置
    """
    # 验证list_type参数
    if list_type not in ['white', 'black']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list_type. Must be 'white' or 'black'"
        )
    
    # 转换组数据为字典
    group_dict = group_data.dict()
    
    return WAFRulesService.add_blackwhite_group(list_type, group_dict)


@router.post("/rules/ipblackwhite/block", response_model=schemas.WAFBlackWhiteListResponse, summary="拉黑IP")
async def block_ip(
    block_request: schemas.WAFIPBlockRequest,
    current_user = Depends(get_current_active_user)
):
    """拉黑IP到Blocked IPs组
    
    Args:
        block_request: 包含要拉黑的IP地址
        
    Returns:
        更新后的黑白名单配置
    """
    return WAFRulesService.block_ip(block_request.ip)


@router.get("/rules/urlwhitelist/list", response_model=schemas.WAFURLWhiteListResponse, summary="获取URL白名单列表")
async def get_url_white_list(
    current_user = Depends(get_current_active_user)
):
    """获取URL白名单列表
    
    从配置文件中读取URL白名单配置，包括正常路由、静态资源路径和静态资源扩展名
    """
    return WAFRulesService.get_url_white_list()


@router.get("/rules/protection", response_model=schemas.WAFProtectionRuleResponse, summary="获取防护规则配置")
async def get_protection_rules(
    current_user = Depends(get_current_active_user)
):
    """获取防护规则配置

    读取 WAF_RULES_PATH 下所有防护规则的 config.json，
    返回每条规则的 rule_key、rule_name、enabled 和完整 config 内容。

    规则类型包括：bot、cc、cmd、csrf、file_inclusion、file_upload、
    ldap_injection、scanner、sql、ssrf、xss
    """
    return WAFRulesService.get_protection_rules()


@router.post("/rules/protection/{rule_key}/update", response_model=schemas.WAFProtectionRuleUpdateResponse, summary="更新指定防护规则配置")
async def update_protection_rule(
    rule_key: str,
    update_data: schemas.WAFProtectionRuleUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """更新指定防护规则配置

    读取 WAF_RULES_PATH/{rule_key}/config.json，
    将请求中的 config 字段合并写入原配置文件，仅允许更新该规则类型定义的字段。

    规则类型包括：bot、cc、cmd、csrf、file_inclusion、file_upload、
    ldap_injection、scanner、sql、ssrf、xss
    """
    valid_keys = {'bot', 'cc', 'cmd', 'csrf', 'file_inclusion', 'file_upload',
                  'ldap_injection', 'scanner', 'sql', 'ssrf', 'xss'}
    if rule_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule_key: {rule_key}. Must be one of {valid_keys}"
        )
    return WAFRulesService.update_protection_rule(rule_key, update_data.config)


@router.post("/rules/urlwhitelist/update", response_model=schemas.WAFURLWhiteListResponse, summary="更新URL白名单")
async def update_url_white_list(
    update_data: schemas.WAFURLWhiteListUpdate,
    current_user = Depends(get_current_active_user)
):
    """更新URL白名单
    
    从配置文件中更新URL白名单配置，包括正常路由、静态资源路径和静态资源扩展名
    """
    # 转换更新数据为字典
    update_dict = update_data.dict(exclude_unset=True)
    
    return WAFRulesService.update_url_white_list(update_dict)


@router.get("/sites/{site_name}/logs", response_model=schemas.WAFSiteLogResponse, summary="获取指定站点日志内容")
async def get_site_logs(
    site_name: str,
    current_user = Depends(get_current_active_user)
):
    """获取指定站点的日志内容
    
    - site_name: 站点名称
    - 返回站点的访问日志和错误日志原文内容
    """
    return WAFSiteService.get_site_logs(site_name)


@router.post("/sites/{site_name}/logs/clear", response_model=schemas.WAFSiteLogCleanResponse, summary="清理指定站点日志")
async def clean_site_logs(
    site_name: str,
    clean_request: schemas.WAFSiteLogCleanRequest,
    current_user = Depends(get_current_active_user)
):
    """清理指定站点的日志
    
    - site_name: 站点名称
    - log_type: 日志类型，access或error
    """
    return WAFSiteService.clean_site_logs(site_name, clean_request.log_type)


@router.get("/sites/list", response_model=schemas.WAFSiteListResponse, summary="获取站点列表")
async def get_site_list(
    current_user = Depends(get_current_active_user)
):
    """获取站点列表
    
    返回所有站点的详细信息，包括：
    - 站点名称
    - 站点类型（静态站点/反向代理）
    - 防护模式（block=拦截, record=记录, Maintenance=维护）
    - 域名
    - 端口
    - 是否SSL
    - 人机验证状态
    - CC防护状态
    - 其他防护状态
    - 上游服务器（反向代理专有）
    - 今日请求数
    - 今日拦截数
    """
    return WAFSiteService.get_site_list()


@router.post("/sites/{site_name}/basic/update", response_model=schemas.WAFSiteLogCleanResponse, summary="更新指定站点配置")
async def update_site(
    site_name: str,
    update_data: schemas.WAFSiteUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """更新指定站点的配置
    
    - site_name: 站点名称
    - waf_mode: WAF模式: block=拦截, record=记录, Maintenance=维护
    - bot_enabled: BOT验证开关: 1=开启, 0=关闭
    - bot_verify_enabled: BOT验证模式: 0=无感, 1=5秒, 2=滑动
    - domain: 域名
    - port: 端口
    - cc_enabled: CC防护开关: 1=开启, 0=关闭
    - upstream_server: 上游服务器（仅限反向代理站点）
    """
    # 转换更新数据为字典
    update_dict = update_data.dict(exclude_unset=True)
    
    return await WAFSiteService.update_site(site_name, update_dict)


@router.post("/sites/{site_name}/ssl/update", response_model=schemas.WAFSiteSSLUpdateResponse, summary="更新指定站点SSL配置")
async def update_site_ssl(
    site_name: str,
    ssl_data: schemas.WAFSiteSSLUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """更新指定站点的SSL配置
    
    - site_name: 站点名称
    - enabled: SSL开关: true=开启, false=关闭
    - cert_name: SSL证书名称（开启SSL时必填）
    - http2: HTTP/2开关: true=开启, false=关闭（默认开启）
    - ssl_protocols: SSL协议版本（默认: TLSv1.2 TLSv1.3）
    - ssl_ciphers: SSL加密套件（使用默认值）
    """
    # 验证：开启SSL时必须提供证书名称
    if ssl_data.enabled and not ssl_data.cert_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate name is required when enabling SSL"
        )
    
    ssl_dict = ssl_data.dict(exclude_unset=True)
    
    return await WAFSiteService.update_site_ssl(site_name, ssl_dict)


@router.post("/sites/{site_name}/protection/update", response_model=schemas.WAFSiteLogCleanResponse, summary="更新指定站点漏洞防护配置")
async def update_site_protection(
    site_name: str,
    protection_data: schemas.WAFSiteProtectionUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """更新指定站点的漏洞防护配置
    
    - site_name: 站点名称
    - sql_injection: SQL注入防护开关: true=开启, false=关闭
    - xss: XSS防护开关: true=开启, false=关闭
    - command_injection: 命令注入防护开关: true=开启, false=关闭
    - ssrf: SSRF防护开关: true=开启, false=关闭
    - ldap_injection: LDAP注入防护开关: true=开启, false=关闭
    - csrf: CSRF防护开关: true=开启, false=关闭
    - file_inclusion: 文件包含防护开关: true=开启, false=关闭
    - file_upload: 恶意文件上传防护开关: true=开启, false=关闭
    - scanner: 扫描器防护开关: true=开启, false=关闭
    """
    protection_dict = protection_data.dict(exclude_unset=True)
    return await WAFSiteService.update_site_protection(site_name, protection_dict)


@router.get("/sites/{site_name}/config", response_model=schemas.WAFSiteConfigResponse, summary="获取指定站点配置文件内容")
async def get_site_config(
    site_name: str,
    current_user = Depends(get_current_active_user)
):
    """获取指定站点的配置文件内容
    
    - site_name: 站点名称
    - 返回站点的配置文件原文内容
    """
    return WAFSiteService.get_site_config(site_name)


@router.post("/sites/{site_name}/config/update", response_model=schemas.WAFSiteLogCleanResponse, summary="修改指定站点配置文件内容")
async def update_site_config(
    site_name: str,
    config_data: schemas.WAFSiteConfigUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """修改指定站点的配置文件内容

    - site_name: 站点名称
    - content: 新的配置文件内容
    """
    return await WAFSiteService.update_site_config(site_name, config_data.content)


@router.post("/sites/create", response_model=schemas.WAFSiteCreateResponse, summary="创建新站点")
async def create_site(
    site_data: schemas.WAFSiteCreateRequest,
    current_user = Depends(get_current_active_user)
):
    """创建新站点

    根据站点类型创建对应的配置文件和相关目录：
    - 静态站点：创建 conf + www目录(含默认index.html) + 日志目录
    - 反向代理站点：创建 conf + 日志目录

    - site_name: 站点名称，用于标识站点
    - site_type: 站点类型: Static Site / Reverse Proxy
    - domain: 域名
    - port: 端口
    - upstream_server: 上游服务器地址（仅反向代理站点需要）
    """
    return await WAFSiteService.create_site(
        site_name=site_data.site_name,
        site_type=site_data.site_type,
        domain=site_data.domain,
        port=site_data.port,
        upstream_server=site_data.upstream_server or "",
        is_ssl=site_data.is_ssl,
        ssl_cert_name=site_data.ssl_cert_name or "",
        index_content=site_data.index_content or ""
    )


@router.post("/sites/{site_name}/delete", response_model=schemas.WAFSiteDeleteResponse, summary="删除指定站点")
async def delete_site(
    site_name: str,
    current_user = Depends(get_current_active_user)
):
    """删除指定站点

    根据站点类型执行不同的清理操作：
    - 静态站点：删除配置文件 + www目录 + 日志目录
    - 反向代理站点：删除配置文件 + 日志目录

    - site_name: 站点名称
    """
    return await WAFSiteService.delete_site(site_name)


@router.get("/html-pages/list", response_model=schemas.WAFHtmlPageListResponse, summary="获取WAF HTML页面列表（包含内容）")
async def get_html_pages(
    current_user = Depends(get_current_active_user)
):
    """获取WAF HTML页面列表（包含所有页面的内容）

    返回所有WAF HTML页面的文件名、路径和内容信息
    """
    return WAFSiteService.get_html_pages()


@router.post("/html-pages/{file_name}/update", response_model=schemas.WAFHtmlPageUpdateResponse, summary="修改指定WAF HTML页面内容")
async def update_html_page_content(
    file_name: str,
    update_data: schemas.WAFHtmlPageUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """修改指定WAF HTML页面内容

    - file_name: HTML文件名
    - content: 新的HTML文件内容
    """
    return await WAFSiteService.update_html_page_content(file_name, update_data.content)


@router.get("/bigscreen/config", response_model=schemas.BigScreenConfigResponse, summary="获取大屏配置")
async def get_big_screen_config(
    current_user = Depends(get_current_active_user)
):
    """获取大屏配置

    返回大屏配置信息，包括：
    - title: 大屏名称
    - theme: 主题色
    - screen: 大屏开关状态
    """
    try:
        config = await service.get_big_screen_config()
        return schemas.BigScreenConfigResponse(
            title=config.get('title', '攻击监控大屏'),
            theme=config.get('theme', '#0a1929'),
            screen=config.get('screen', True),
            message="success"
        )
    except Exception as e:
        logger.error(f"获取大屏配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取大屏配置失败: {str(e)}"
        )


@router.post("/bigscreen/config/update", response_model=schemas.BigScreenConfigResponse, summary="更新大屏配置")
async def update_big_screen_config(
    update_data: schemas.BigScreenConfigUpdate,
    current_user = Depends(get_current_active_user)
):
    """更新大屏配置

    - title: 大屏名称（可选）
    - theme: 主题色（可选）
    - screen: 大屏开关（可选）
    """
    try:
        update_dict = update_data.dict(exclude_unset=True)
        config = await service.update_big_screen_config(update_dict)
        return schemas.BigScreenConfigResponse(
            title=config.get('title', '攻击监控大屏'),
            theme=config.get('theme', '#0a1929'),
            screen=config.get('screen', True),
            message="success"
        )
    except Exception as e:
        logger.error(f"更新大屏配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新大屏配置失败: {str(e)}"
        )


@router.get("/location/stats", response_model=schemas.LocationStatsResponse, summary="获取访问/拦截日志的地点统计")
async def get_location_stats(
    current_user = Depends(get_current_active_user)
):
    """获取访问/拦截日志的地点统计

    返回数据格式:
    {
        "waf_logs": [{"location": "俄罗斯", "count": 1}, ...],
        "access_logs": [{"location": "中国", "count": 100}, ...],
        "message": "success get location stats"
    }
    """
    return WAFOverviewService.get_location_stats()


@router.get("/nginx/config", response_model=schemas.WAFGlobalConfigResponse, summary="获取全局nginx配置")
async def get_global_config(
    current_user = Depends(get_current_active_user)
):
    """获取全局nginx配置

    读取 nginx.conf 并解析出可配置的参数，包括：
    连接调优、超时设置、上传限制、Gzip压缩、TCP优化、错误拦截、Lua缓存等
    """
    return service.get_global_config()


@router.post("/nginx/config/update", response_model=schemas.WAFGlobalConfigResponse, summary="更新全局nginx配置")
async def update_global_config(
    update_data: schemas.WAFGlobalConfigUpdateRequest,
    current_user = Depends(get_current_active_user)
):
    """更新全局nginx配置

    将传入的参数写入 nginx.conf 对应的指令行并自动重启 WAF 容器使配置生效。
    """
    try:
        update_dict = update_data.dict(exclude_unset=True)
        return await service.update_global_config(update_dict)
    except Exception as e:
        logger.error(f"更新nginx全局配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新nginx全局配置失败: {str(e)}"
        )


@router.get("/threat-intel/config", response_model=schemas.ThreatIntelConfigResponse, summary="获取AbuseIPDB配置")
async def get_threat_intel_config(
    db: AsyncSession = Depends(get_waf_db),
    current_user = Depends(get_current_active_user)
):
    """获取 AbuseIPDB 配置

    返回 API 密钥、启用状态、同步状态
    """
    data = await ThreatIntelService.get_config(db)
    return schemas.ThreatIntelConfigResponse(
        id=data["id"],
        api_key=data["api_key"],
        enabled=data["enabled"],
        last_sync_time=data["last_sync_time"],
        synced_ip_count=data["synced_ip_count"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        message="success"
    )


@router.post("/threat-intel/config/update", response_model=schemas.ThreatIntelConfigResponse, summary="更新AbuseIPDB配置")
async def update_threat_intel_config(
    update_data: schemas.ThreatIntelConfigUpdateRequest,
    db: AsyncSession = Depends(get_waf_db),
    current_user = Depends(get_current_active_user)
):
    """更新 AbuseIPDB API Key 和启用状态
    """
    try:
        data = await ThreatIntelService.update_config(
            db, update_data.api_key, update_data.enabled
        )
        return schemas.ThreatIntelConfigResponse(
            id=data["id"],
            api_key=data["api_key"],
            enabled=data["enabled"],
            last_sync_time=data["last_sync_time"],
            synced_ip_count=data["synced_ip_count"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            message="success"
        )
    except Exception as e:
        logger.error(f"更新 AbuseIPDB 配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新 AbuseIPDB 配置失败: {str(e)}"
        )


@router.post("/threat-intel/test", response_model=schemas.ThreatIntelTestResponse, summary="测试AbuseIPDB API Key")
async def test_threat_intel_api(
    test_data: schemas.ThreatIntelTestRequest,
    current_user = Depends(get_current_active_user)
):
    """测试 AbuseIPDB API Key 是否可用

    使用测试 IP (8.8.8.8) 调用 AbuseIPDB 验证 API Key 是否有效
    """
    result = await ThreatIntelService.test_api_key(test_data.api_key)
    return schemas.ThreatIntelTestResponse(
        success=result["success"],
        message=result["message"]
    )


@router.post("/threat-intel/sync", response_model=schemas.ThreatIntelSyncResponse, summary="同步AbuseIPDB黑名单到WAF")
async def sync_threat_intel_blacklist(
    db: AsyncSession = Depends(get_waf_db),
    current_user = Depends(get_current_active_user)
):
    """同步 AbuseIPDB 黑名单到 WAF

    拉取恶意 IP 列表，写入 WAF 的 Intelligence Blacklist Ips 组并生效
    """
    result = await ThreatIntelService.sync_blacklist(db)
    return schemas.ThreatIntelSyncResponse(
        success=result["success"],
        total_fetched=result["total_fetched"],
        added_count=result["added_count"],
        message=result["message"],
        last_sync_time=result["last_sync_time"]
    )


@router.post("/threat-intel/analyze", response_model=schemas.ThreatIntelIPAnalysisResponse, summary="查询AbuseIPDB IP信誉")
async def analyze_threat_intel_ip(
    analyze_data: schemas.ThreatIntelIPAnalysisRequest,
    db: AsyncSession = Depends(get_waf_db),
    current_user = Depends(get_current_active_user)
):
    """查询指定 IP 在 AbuseIPDB 的信誉详情
    """
    result = await ThreatIntelService.analyze_ip(db, analyze_data.ip)
    return schemas.ThreatIntelIPAnalysisResponse(
        success=result["success"],
        ip=result["ip"],
        data=result["data"],
        message=result["message"]
    )
