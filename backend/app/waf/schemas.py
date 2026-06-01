from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class SSLCertCreate(BaseModel):
    """创建SSL证书模型"""
    name: str = Field(..., description="SSL证书名称")
    key: str = Field(..., description="SSL私钥内容")
    pem: str = Field(..., description="SSL证书内容(PEM格式)")


class SSLCertUpdate(BaseModel):
    """更新SSL证书模型"""
    key: Optional[str] = Field(None, description="SSL私钥内容")
    pem: Optional[str] = Field(None, description="SSL证书内容(PEM格式)")


class SSLCertInDB(BaseModel):
    """数据库中的SSL证书模型"""
    id: int
    name: str
    domain: Optional[str] = None
    issuer: Optional[str] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SSLCertResponse(BaseModel):
    """SSL证书响应模型"""
    id: int
    name: str
    domain: Optional[str] = None
    issuer: Optional[str] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    message: str


class SSLCertListResponse(BaseModel):
    """SSL证书列表响应模型"""
    certs: List[SSLCertInDB]
    total: int
    message: str


class SSLCertDeleteResponse(BaseModel):
    """SSL证书删除响应模型"""
    message: str


class SSLCertDetailResponse(BaseModel):
    """SSL证书详情响应模型（包含key和pem内容）"""
    id: int
    name: str
    domain: Optional[str] = None
    issuer: Optional[str] = None
    expiry_date: Optional[datetime] = None
    key: str
    pem: str
    created_at: datetime
    updated_at: datetime
    message: str


class WAFContainerStatus(BaseModel):
    """WAF容器状态响应模型"""
    status: str = Field(..., description="容器状态: running, stopped, paused, restarting, dead")
    message: str = Field(..., description="响应消息")


class WAFContainerAction(BaseModel):
    """WAF容器操作请求模型"""
    action: str = Field(..., description="操作类型: start, stop, restart")


class WAFContainerActionResponse(BaseModel):
    """WAF容器操作响应模型"""
    message: str = Field(..., description="操作结果消息")


class GeoIPInfo(BaseModel):
    """GeoIP信息模型"""
    country_code: str = Field(..., description="国家代码")
    city: str = Field(..., description="城市")
    country: str = Field(..., description="国家")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    location: str = Field(..., description="位置")


class WAFLogEntry(BaseModel):
    """WAF拦截日志条目模型"""
    attack_type: str = Field(..., description="攻击类型: bot, cc, sql")
    reason: str = Field(..., description="拦截原因")
    action: str = Field(..., description="操作类型: blocked, challenge")
    client_ip: str = Field(..., description="客户端IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_uri: str = Field(..., description="请求URI")
    request_method: str = Field(..., description="请求方法")
    application: str = Field(..., description="应用URL")
    timestamp: float = Field(..., description="时间戳")
    datetime: str = Field(..., description="日期时间")
    geoip: GeoIPInfo = Field(..., description="GeoIP信息")


class WAFLogListResponse(BaseModel):
    """WAF日志列表响应模型"""
    logs: List[WAFLogEntry]
    total: int
    message: str


class WAFBotLogEntry(BaseModel):
    """WAF BOT验证日志条目模型"""
    action: str = Field(..., description="操作类型: verified, challenge")
    client_ip: str = Field(..., description="客户端IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_uri: str = Field(..., description="请求URI")
    request_method: str = Field(..., description="请求方法")
    application_url: str = Field(..., description="应用URL")
    verify_mode: str = Field(..., description="验证模式: 0=无感验证, 1=5秒页面验证, 2=滑动验证")
    verification_status: str = Field(..., description="验证状态: triggered, passed, failed")
    timestamp: float = Field(..., description="时间戳")
    datetime: str = Field(..., description="日期时间")
    geoip: GeoIPInfo = Field(..., description="GeoIP信息")


class WAFBotLogListResponse(BaseModel):
    """WAF BOT日志列表响应模型"""
    logs: List[WAFBotLogEntry]
    total: int
    message: str


class WAFLogCleanRequest(BaseModel):
    """WAF日志清理请求模型"""
    days: Optional[int] = Field(None, description="保留最近的天数，不指定则清空所有日志")


class WAFLogCleanResponse(BaseModel):
    """WAF日志清理响应模型"""
    message: str = Field(..., description="清理结果消息")


class WAFBlackWhiteLogEntry(BaseModel):
    """WAF黑白名单日志条目模型"""
    action: str = Field(..., description="操作类型: allow, block")
    client_ip: str = Field(..., description="客户端IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    application_url: str = Field(..., description="应用URL")
    group: Optional[str] = Field(None, description="分组名称")
    timestamp: float = Field(..., description="时间戳")
    datetime: str = Field(..., description="日期时间")
    geoip: GeoIPInfo = Field(..., description="GeoIP信息")


class WAFBlackWhiteLogListResponse(BaseModel):
    """WAF黑白名单日志列表响应模型"""
    logs: List[WAFBlackWhiteLogEntry]
    total: int
    message: str


class WAFOverviewResponse(BaseModel):
    """WAF基本概况响应模型"""
    # 访问日志统计
    access_logs: dict = Field(..., description="访问日志统计")
    # WAF拦截日志统计
    waf_logs: dict = Field(..., description="WAF拦截日志统计")
    # 黑白名单日志统计
    blackwhite_logs: dict = Field(..., description="黑白名单日志统计")
    # BOT验证日志统计
    bot_logs: dict = Field(..., description="BOT验证日志统计")
    message: str = Field(..., description="响应消息")


class WAFBlackWhiteListEntry(BaseModel):
    """WAF黑白名单条目模型"""
    name: str = Field(..., description="规则名称")
    enabled: bool = Field(..., description="是否启用")
    description: str = Field(..., description="规则描述")
    ips: List[str] = Field(..., description="IP列表")


class WAFBlackWhiteListResponse(BaseModel):
    """WAF黑白名单响应模型"""
    white_list: List[WAFBlackWhiteListEntry] = Field(..., description="白名单")
    black_list: List[WAFBlackWhiteListEntry] = Field(..., description="黑名单")
    message: str = Field(..., description="响应消息")


class WAFBlackWhiteGroupCreate(BaseModel):
    """WAF黑白名单组创建模型"""
    name: str = Field(..., description="规则名称")
    enabled: bool = Field(True, description="是否启用")
    description: str = Field("", description="规则描述")
    ips: List[str] = Field(default_factory=list, description="IP列表")


class WAFBlackWhiteGroupUpdate(BaseModel):
    """WAF黑白名单组更新模型"""
    name: Optional[str] = Field(None, description="规则名称")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, description="规则描述")
    ips: Optional[List[str]] = Field(None, description="IP列表")


class WAFIPBlockRequest(BaseModel):
    """WAF IP拉黑请求模型"""
    ip: str = Field(..., description="要拉黑的IP地址")


class WAFURLWhiteListResponse(BaseModel):
    """WAF URL白名单响应模型"""
    enabled: bool = Field(..., description="是否启用")
    normal_routes: List[str] = Field(..., description="正常路由白名单")
    static_paths: List[str] = Field(..., description="静态资源路径白名单")
    static_extensions: List[str] = Field(..., description="静态资源扩展名白名单")
    message: str = Field(..., description="响应消息")


class WAFURLWhiteListUpdate(BaseModel):
    """WAF URL白名单更新模型"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    normal_routes: Optional[List[str]] = Field(None, description="正常路由白名单")
    static_paths: Optional[List[str]] = Field(None, description="静态资源路径白名单")
    static_extensions: Optional[List[str]] = Field(None, description="静态资源扩展名白名单")


class WAFSiteLogResponse(BaseModel):
    """WAF站点日志响应模型"""
    access_log: str = Field(..., description="访问日志内容")
    error_log: str = Field(..., description="错误日志内容")
    message: str = Field(..., description="响应消息")


class WAFSiteInfo(BaseModel):
    """WAF Site Info Model"""
    name: str = Field(..., description="Site name (internal slug)")
    display_name: str = Field(..., description="Site display name (original name input by user)")
    type: str = Field(..., description="Site type: Static Site / Reverse Proxy / PHP Site")
    waf_mode: str = Field(..., description="WAF mode: block=block, record=record, Maintenance=maintenance")
    domain: str = Field(..., description="Domain")
    port: str = Field(..., description="Port")
    is_ssl: bool = Field(..., description="Is SSL")
    ssl_cert_name: Optional[str] = Field(None, description="SSL certificate name (only when SSL is enabled)")
    bot_status: str = Field(..., description="Bot verification status: Disabled/Silent Verification/5s Verification/Slide Verification")
    cc_status: str = Field(..., description="CC protection status: Enabled/Disabled")
    protection_status: Dict[str, str] = Field(..., description="Detailed protection status")
    upstream_server: str = Field(..., description="Upstream server (for reverse proxy) or static file root path (for static site)")
    php_fpm_host: Optional[str] = Field(None, description="PHP-FPM host (for PHP Site)")
    today_requests: int = Field(..., description="Today's requests")
    today_blocks: int = Field(..., description="Today's blocks")


class WAFSiteLogCleanRequest(BaseModel):
    """WAF Site Log Clean Request Model"""
    log_type: str = Field(..., description="Log type: access or error")


class WAFSiteLogCleanResponse(BaseModel):
    """WAF Site Log Clean Response Model"""
    message: str = Field(..., description="Response message")


class WAFSiteUpdateRequest(BaseModel):
    """WAF Site Update Request Model"""
    waf_mode: Optional[str] = Field(None, description="WAF mode: block=block, record=record, Maintenance=maintenance")
    bot_enabled: Optional[int] = Field(None, description="Bot verification enabled: 1=enabled, 0=disabled")
    bot_verify_enabled: Optional[int] = Field(None, description="Bot verification mode: 0=silent, 1=5s, 2=slide")
    domain: Optional[str] = Field(None, description="Domain")
    port: Optional[str] = Field(None, description="Port")
    cc_enabled: Optional[int] = Field(None, description="CC protection enabled: 1=enabled, 0=disabled")
    upstream_server: Optional[str] = Field(None, description="Upstream server (for reverse proxy only)")
    php_fpm_host: Optional[str] = Field(None, description="PHP-FPM host (for PHP Site only)")


class WAFSiteListResponse(BaseModel):
    """WAF Site List Response Model"""
    sites: List[WAFSiteInfo] = Field(..., description="Site list")
    message: str = Field(..., description="Response message")


class WAFSiteSSLUpdateRequest(BaseModel):
    """WAF Site SSL Update Request Model"""
    enabled: bool = Field(..., description="SSL enabled: true=enabled, false=disabled")
    cert_name: Optional[str] = Field(None, description="SSL certificate name (required when enabled=true)")
    http2: Optional[bool] = Field(True, description="HTTP/2 enabled: true=enabled, false=disabled")
    ssl_protocols: Optional[str] = Field("TLSv1.2 TLSv1.3", description="SSL protocols")
    ssl_ciphers: Optional[str] = Field(
        "ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384",
        description="SSL ciphers"
    )


class WAFSiteSSLUpdateResponse(BaseModel):
    """WAF Site SSL Update Response Model"""
    message: str = Field(..., description="Response message")


class WAFSiteProtectionUpdateRequest(BaseModel):
    """WAF Site Protection Update Request Model"""
    sql_injection: Optional[bool] = Field(None, description="SQL injection protection enabled: true=enabled, false=disabled")
    xss: Optional[bool] = Field(None, description="XSS protection enabled: true=enabled, false=disabled")
    command_injection: Optional[bool] = Field(None, description="Command injection protection enabled: true=enabled, false=disabled")
    ssrf: Optional[bool] = Field(None, description="SSRF protection enabled: true=enabled, false=disabled")
    ldap_injection: Optional[bool] = Field(None, description="LDAP injection protection enabled: true=enabled, false=disabled")
    csrf: Optional[bool] = Field(None, description="CSRF protection enabled: true=enabled, false=disabled")
    file_inclusion: Optional[bool] = Field(None, description="File inclusion protection enabled: true=enabled, false=disabled")
    file_upload: Optional[bool] = Field(None, description="File upload protection enabled: true=enabled, false=disabled")
    scanner: Optional[bool] = Field(None, description="Scanner protection enabled: true=enabled, false=disabled")


class WAFSiteConfigResponse(BaseModel):
    """WAF Site Config Response Model"""
    content: str = Field(..., description="Configuration file content")
    message: str = Field(..., description="Response message")


class WAFSiteConfigUpdateRequest(BaseModel):
    """WAF Site Config Update Request Model"""
    content: str = Field(..., description="New configuration file content")


class QPSNode(BaseModel):
    """QPS节点数据模型"""
    qps: float = Field(..., description="QPS值")
    requests: int = Field(..., description="请求数")
    blocks: int = Field(..., description="拦截数")
    time: str = Field(..., description="时间点 (HH:MM:SS)")


class WAFQPSResponse(BaseModel):
    """WAF QPS Response Model - 实时监控数据"""
    data: Dict[str, List[QPSNode]] = Field(..., description="监控数据，包含nodes数组")
    err: Optional[str] = Field(None, description="错误信息")
    msg: str = Field(..., description="响应消息")


class ClientStatItem(BaseModel):
    """Client Stat Item Model"""
    name: str = Field(..., description="Client name (OS or browser)")
    count: int = Field(..., description="Request count")


class StatusStatItem(BaseModel):
    """Status Stat Item Model"""
    status_code: str = Field(..., description="HTTP status code")
    count: int = Field(..., description="Request count")


class WAFClientStatsResponse(BaseModel):
    """WAF Client Stats Response Model"""
    operating_systems: List[ClientStatItem] = Field(..., description="Operating systems statistics (sorted by count desc)")
    browsers: List[ClientStatItem] = Field(..., description="Browsers statistics (sorted by count desc)")
    status_codes: List[StatusStatItem] = Field(..., description="HTTP status codes statistics (sorted by count desc)")
    message: str = Field(..., description="Response message")


class WAFHtmlPageInfo(BaseModel):
    """WAF HTML页面信息模型"""
    name: str = Field(..., description="HTML文件名")
    path: str = Field(..., description="HTML文件完整路径")
    content: str = Field(..., description="HTML文件内容")


class WAFHtmlPageListResponse(BaseModel):
    """WAF HTML页面列表响应模型"""
    pages: List[WAFHtmlPageInfo] = Field(..., description="HTML页面列表（包含内容）")
    message: str = Field(..., description="响应消息")


class WAFHtmlPageUpdateRequest(BaseModel):
    """WAF HTML页面更新请求模型"""
    content: str = Field(..., description="新的HTML文件内容")


class WAFHtmlPageUpdateResponse(BaseModel):
    """WAF HTML页面更新响应模型"""
    name: str = Field(..., description="HTML文件名")
    message: str = Field(..., description="响应消息")


class BigScreenConfig(BaseModel):
    """大屏配置模型"""
    title: str = Field(..., description="大屏名称")
    theme: str = Field(..., description="主题色")
    screen: bool = Field(..., description="大屏开关")


class BigScreenConfigUpdate(BaseModel):
    """大屏配置更新请求模型"""
    title: Optional[str] = Field(None, description="大屏名称")
    theme: Optional[str] = Field(None, description="主题色")
    screen: Optional[bool] = Field(None, description="大屏开关")


class BigScreenConfigResponse(BaseModel):
    """大屏配置响应模型"""
    title: str = Field(..., description="大屏名称")
    theme: str = Field(..., description="主题色")
    screen: bool = Field(..., description="大屏开关")
    message: str = Field(..., description="响应消息")


class LocationStatItem(BaseModel):
    """地点统计条目模型"""
    location: str = Field(..., description="地点/位置")
    count: int = Field(..., description="访问或拦截次数")


class LocationStatsResponse(BaseModel):
    """地点统计响应模型"""
    waf_logs: List[LocationStatItem] = Field(..., description="WAF拦截日志地点统计")
    access_logs: List[LocationStatItem] = Field(..., description="访问日志地点统计")
    message: str = Field(..., description="响应消息")


class WAFSiteDeleteResponse(BaseModel):
    """WAF站点删除响应模型"""
    site_name: str = Field(..., description="站点名称")
    site_type: str = Field(..., description="站点类型: Static Site / Reverse Proxy")
    message: str = Field(..., description="响应消息")


class WAFSiteCreateRequest(BaseModel):
    """WAF站点创建请求模型"""
    site_name: str = Field(..., description="站点名称，用于标识站点")
    site_type: str = Field(..., description="站点类型: Static Site / Reverse Proxy / PHP Site")
    domain: str = Field(..., description="域名")
    port: str = Field(..., description="端口")
    upstream_server: Optional[str] = Field(None, description="上游服务器地址（仅反向代理站点需要）")
    php_fpm_host: Optional[str] = Field(None, description="PHP-FPM 地址（仅PHP站点需要，默认 php-fpm:9000）")
    is_ssl: bool = Field(False, description="是否启用SSL")
    ssl_cert_name: Optional[str] = Field(None, description="SSL证书名称（启用SSL时必填）")
    index_content: Optional[str] = Field(None, description="自定义index.html/index.php内容（仅静态/PHP站点，不传则使用默认模板）")


class WAFSiteCreateResponse(BaseModel):
    """WAF站点创建响应模型"""
    site_name: str = Field(..., description="站点名称")
    site_type: str = Field(..., description="站点类型: Static Site / Reverse Proxy / PHP Site")
    domain: str = Field(..., description="域名")
    port: str = Field(..., description="端口")
    php_fpm_host: Optional[str] = Field(None, description="PHP-FPM地址")
    message: str = Field(..., description="响应消息")


class WAFProtectionRuleItem(BaseModel):
    """防护规则条目模型"""
    rule_key: str = Field(..., description="规则标识: bot/cc/cmd/csrf/file_inclusion/file_upload/ldap_injection/scanner/sql/ssrf/xss")
    rule_name: str = Field(..., description="规则显示名称")
    config: dict = Field(..., description="规则配置内容")


class WAFProtectionRuleResponse(BaseModel):
    """防护规则列表响应模型"""
    rules: List[WAFProtectionRuleItem] = Field(..., description="防护规则列表")
    message: str = Field(..., description="响应消息")


class WAFProtectionRuleUpdateRequest(BaseModel):
    """防护规则更新请求模型"""
    config: dict = Field(..., description="规则配置内容，需包含该规则类型支持的全部字段")


class WAFProtectionRuleUpdateResponse(BaseModel):
    """防护规则更新响应模型"""
    rule_key: str = Field(..., description="规则标识")
    rule_name: str = Field(..., description="规则显示名称")
    config: dict = Field(..., description="更新后的规则配置内容")
    message: str = Field(..., description="响应消息")


class WAFGlobalConfigResponse(BaseModel):
    """WAF全局nginx配置响应模型"""
    worker_connections: int = Field(..., description="单个worker最大连接数")
    keepalive_timeout: int = Field(..., description="长连接保持时间（秒）")
    client_max_body_size: str = Field(..., description="上传文件大小限制，如100m")
    client_body_timeout: int = Field(..., description="客户端请求体超时（秒）")
    client_header_timeout: int = Field(..., description="客户端请求头超时（秒）")
    send_timeout: int = Field(..., description="响应发送超时（秒）")
    gzip_enabled: bool = Field(..., description="Gzip压缩开关")
    gzip_comp_level: int = Field(..., description="Gzip压缩级别 (1-9)")
    gzip_min_length: str = Field(..., description="最小压缩长度，如1k")
    gzip_vary: bool = Field(..., description="Vary: Accept-Encoding头")
    gzip_disable: str = Field(..., description="禁用压缩的UA正则")
    sendfile: bool = Field(..., description="sendfile开关")
    tcp_nopush: bool = Field(..., description="tcp_nopush开关")
    tcp_nodelay: bool = Field(..., description="tcp_nodelay开关")
    multi_accept: bool = Field(..., description="multi_accept开关")
    proxy_intercept_errors: bool = Field(..., description="拦截后端错误页面开关")
    lua_code_cache: bool = Field(..., description="Lua代码缓存开关")
    message: str = Field(..., description="响应消息")


class WAFContainerExistsResponse(BaseModel):
    """WAF容器是否存在响应模型"""
    exists: bool = Field(..., description="容器是否存在")
    container_name: str = Field(..., description="容器名称")
    message: str = Field(..., description="响应消息")


class WAFGlobalConfigUpdateRequest(BaseModel):
    """WAF全局nginx配置更新请求模型"""
    worker_connections: Optional[int] = Field(None, ge=1, description="单个worker最大连接数")
    keepalive_timeout: Optional[int] = Field(None, ge=1, description="长连接保持时间（秒）")
    client_max_body_size: Optional[str] = Field(None, description="上传文件大小限制")
    client_body_timeout: Optional[int] = Field(None, ge=1, description="客户端请求体超时（秒）")
    client_header_timeout: Optional[int] = Field(None, ge=1, description="客户端请求头超时（秒）")
    send_timeout: Optional[int] = Field(None, ge=1, description="响应发送超时（秒）")
    gzip_enabled: Optional[bool] = Field(None, description="Gzip压缩开关")
    gzip_comp_level: Optional[int] = Field(None, ge=1, le=9, description="Gzip压缩级别 (1-9)")
    gzip_min_length: Optional[str] = Field(None, description="最小压缩长度")
    gzip_vary: Optional[bool] = Field(None, description="Vary: Accept-Encoding头")
    gzip_disable: Optional[str] = Field(None, description="禁用压缩的UA正则")
    sendfile: Optional[bool] = Field(None, description="sendfile开关")
    tcp_nopush: Optional[bool] = Field(None, description="tcp_nopush开关")
    tcp_nodelay: Optional[bool] = Field(None, description="tcp_nodelay开关")
    multi_accept: Optional[bool] = Field(None, description="multi_accept开关")
    proxy_intercept_errors: Optional[bool] = Field(None, description="拦截后端错误页面开关")
    lua_code_cache: Optional[bool] = Field(None, description="Lua代码缓存开关")


class ThreatIntelConfigResponse(BaseModel):
    """AbuseIPDB威胁情报配置响应模型"""
    id: int = Field(..., description="配置ID")
    api_key: str = Field(..., description="API密钥")
    enabled: bool = Field(..., description="是否启用")
    last_sync_time: Optional[datetime] = Field(None, description="最后一次同步时间")
    synced_ip_count: int = Field(0, description="已同步的恶意IP数量")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    message: str = Field(..., description="响应消息")


class ThreatIntelConfigUpdateRequest(BaseModel):
    """AbuseIPDB威胁情报配置更新请求模型"""
    api_key: str = Field(..., min_length=1, description="API密钥")
    enabled: Optional[bool] = Field(True, description="是否启用")


class ThreatIntelTestRequest(BaseModel):
    """AbuseIPDB API测试请求模型"""
    api_key: str = Field(..., min_length=1, description="API密钥")


class ThreatIntelTestResponse(BaseModel):
    """AbuseIPDB API测试响应模型"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")


class ThreatIntelSyncResponse(BaseModel):
    """AbuseIPDB黑名单同步响应模型"""
    success: bool = Field(..., description="同步是否成功")
    total_fetched: int = Field(0, description="从平台获取的IP数量")
    added_count: int = Field(0, description="新增到黑名单的IP数量")
    message: str = Field(..., description="同步结果消息")
    last_sync_time: Optional[datetime] = Field(None, description="同步时间")


class ThreatIntelIPAnalysisRequest(BaseModel):
    """IP分析请求模型"""
    ip: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", description="要分析的IPv4地址")


class ThreatIntelIPAnalysisResponse(BaseModel):
    """AbuseIPDB IP分析响应模型"""
    success: bool = Field(..., description="分析是否成功")
    ip: str = Field(..., description="分析的IP地址")
    data: Optional[dict] = Field(None, description="IP分析数据")
    message: str = Field(..., description="分析结果消息")
