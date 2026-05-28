from pydantic_settings import BaseSettings
from typing import Optional
from datetime import timezone

_BASE_PANEL = "/opt/blackpotbpanel-v2/server"


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./db/app.db"
    
    # 脚本数据库配置
    SCRIPT_DATABASE_URL: str = "sqlite:///./db/scripts.db"
    
    # 容器数据库配置
    CONTAINER_DATABASE_URL: str = "sqlite:///./db/container.db"
    
    # 防火墙数据库配置
    FIREWALL_DATABASE_URL: str = "sqlite:///./db/firewall.db"
    
    # WAF数据库配置
    WAF_DATABASE_URL: str = "sqlite:///./db/waf.db"
    
    # Cronab数据库配置
    CRONAB_DATABASE_URL: str = "sqlite:///./db/crontab.db"
    
    # 数据库数据库配置
    DATABASE_DATABASE_URL: str = "sqlite:///./db/database.db"
    

    
    # 应用配置
    APP_NAME: str = "BlackPotBPanel"
    DEBUG: bool = False
    VERSION: str = "2.0.1"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    
    # 时区配置
    TIMEZONE: str = "UTC"
    
    # API文档配置
    ENABLE_DOCS: bool = True
    
    # 用户界面配置
    LANGUAGE: str = "zh-CN"
    THEME: str = "dark"
    LOGIN_NOTIFY: bool = True
    # 回收站配置
    RECYCLE: bool = True
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    #登录限制开关
    LOGIN_LIMIT: bool = True
    
    # 面板SSL配置
    SSL_ENABLED: bool = False
    SSL_CERT_PATH: str = "./data/ssl/ssl.crt"
    SSL_KEY_PATH: str = "./data/ssl/ssl.key"
    # 攻击大屏配置
    SCREEN_PATH: str = "./data/screen.json"
    #地理位置数据库路径
    GEOIP_COUNTRY_DB_PATH: str = "./data/GeoLite2-Country.json"
    COUNTRY_CODE_MAP_PATH: str = "./data/country.txt"
    GEOIP_CITY_DB_PATH: str = "./data/GeoLite2-City.mmdb"
    
    # 基础路径
    BASE_PANEL_PATH: str = _BASE_PANEL
    
    # 回收站路径
    RECYCLE_PATH: str = f"{_BASE_PANEL}/.recycle_bp"
    # 网站ssl证书
    WEBSITE_SSL_PATH: str = f"{_BASE_PANEL}/waf/ssl/"
    WAF_ACCESS_LOG_PATH: str = f"{_BASE_PANEL}/waf/logs/access.log"
    # waf站点配置
    WAF_SITE_WWW_PATH: str = f"{_BASE_PANEL}/waf/sites/www/"
    WAF_SITE_CONF_PATH: str = f"{_BASE_PANEL}/waf/sites/conf/"
    WAF_SITE_LOG_PATH: str = f"{_BASE_PANEL}/waf/sites/sitelogs/"

    # waf日志配置
    WAF_LOG_PATH: str = f"{_BASE_PANEL}/waf/logs/waf.log"
    # wafBOT日志配置
    WAF_BOT_LOG_PATH: str = f"{_BASE_PANEL}/waf/logs/bot.log"
    WAF_BOT_CONFIG_PATH: str = f"{_BASE_PANEL}/waf/rules/bot/config.json"
    # waf黑名单日志配置
    WAF_BLACKWHITE_LOG_PATH: str = f"{_BASE_PANEL}/waf/logs/blackwhite.log"
    WAF_BLACKWHITE_CONFIG_PATH: str = f"{_BASE_PANEL}/waf/rules/blackwhite/config.json"
    WAF_URLWHITE_CONFIG_PATH: str = f"{_BASE_PANEL}/waf/rules/urlwhitelist/config.json"
    # waf规则配置
    WAF_RULES_PATH: str = f"{_BASE_PANEL}/waf/rules/"
    # waf nginx配置
    WAF_NGINX_CONF_PATH: str = f"{_BASE_PANEL}/waf/conf/nginx.conf"
    # wafHTML页面
    WAF_HTML_PATH: str = f"{_BASE_PANEL}/waf/html/"
  
    # 定时任务配置
    CRONAB_SCRIPT_PATH: str = f"{_BASE_PANEL}/crontab/scripts/"
    CRONAB_LOG_PATH: str = f"{_BASE_PANEL}/crontab/logs/"

    # 备份配置
    BACKUP_PATH: str = f"{_BASE_PANEL}/backup/database/"


    class Config:
        env_file = "../setting.conf"


settings = Settings()