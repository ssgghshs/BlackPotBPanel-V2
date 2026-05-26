# app/__init__.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.user.routers import router as user_router
from app.system.routers import router as system_router
from app.log.routers import router as log_router
from app.monitor.routers import router as monitor_router
from app.file.routers import router as file_router
from app.host.routers import router as host_router
from app.container.routers import router as container_router
from app.script.routers import router as script_router
from app.firewall.routers import router as firewall_router
from app.waf.routers import router as waf_router
from app.service.routers import router as service_router
from app.crontab.routers import router as crontab_router
from app.database.routers import router as database_router
import os
import config.settings

def create_app():
    # 从配置中获取文档设置
    enable_docs = config.settings.settings.ENABLE_DOCS
    
    app = FastAPI(
        title=config.settings.settings.APP_NAME,
        description="BlackPotBPanel backend API",
        version=config.settings.settings.VERSION,
        debug=config.settings.settings.DEBUG,
        docs_url="/api/v2/docs" if enable_docs else None,
        redoc_url="/api/v2/redoc" if enable_docs else None,
        openapi_url="/api/v2/openapi.json" if enable_docs else None
    )
    
    # ===================== 新增：请求方法限制中间件 =====================
    # @app.middleware("http")
    # async def limit_request_methods(request: Request, call_next):
    #     # 1. 定义白名单：登录接口路径（根据你的实际登录接口修改！）
    #     login_post_paths = ["/api/v2/users/login","/api/v2/host/ssh/log"]  # 替换为你真实的登录接口路径
    #     # 2. 获取请求方法和路径
    #     method = request.method
    #     path = request.url.path

    #     # 3. 规则判断：仅允许 GET 请求 或 登录接口的 POST 请求
    #     if method == "GET":
    #         # 允许所有 GET 请求
    #         response = await call_next(request)
    #         return response
    #     elif method == "POST" and path in login_post_paths:
    #         # 允许登录接口的 POST 请求
    #         response = await call_next(request)
    #         return response
    #     else:
    #         # 其他请求返回 405 方法不允许
    #         return JSONResponse(
    #             status_code=405,
    #             content={"detail": "演示环境，不允许操作"}
    #         )
    # ===================== 中间件结束 =====================




    # API路由前缀
    api_prefix = "/api/v2"
    
    # 注册路由
    app.include_router(user_router, prefix=api_prefix)
    app.include_router(system_router, prefix=api_prefix)
    app.include_router(log_router, prefix=api_prefix)
    app.include_router(monitor_router, prefix=api_prefix)
    app.include_router(file_router, prefix=api_prefix)
    app.include_router(host_router, prefix=api_prefix)
    app.include_router(container_router, prefix=api_prefix)
    app.include_router(script_router, prefix=api_prefix)
    app.include_router(firewall_router, prefix=api_prefix)
    app.include_router(waf_router, prefix=api_prefix)
    app.include_router(service_router, prefix=api_prefix)
    app.include_router(crontab_router, prefix=api_prefix)
    app.include_router(database_router, prefix=api_prefix)

    
    # 配置静态文件服务，处理所有非API请求
    from fastapi.responses import FileResponse
    
    # 计算前端静态文件目录路径
    web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    
    # 添加API根路由，避免404
    @app.get(api_prefix, tags=["api"])
    async def api_root():
        return {
            "message": "BlackPotBPanel API",
            "version": config.settings.settings.VERSION,
            "docs": f"{api_prefix}/docs"
        }
    
    # 挂载静态文件目录
    app.mount("/assets", StaticFiles(directory=os.path.join(web_dir, "assets")), name="assets")
    
    # 单独挂载login.png文件
    login_png_path = os.path.join(web_dir, "login.png")
    if os.path.exists(login_png_path):
        @app.get("/login.png", include_in_schema=False)
        async def serve_login_png():
            return FileResponse(login_png_path, media_type="image/png")
    
    # 单独挂载favicon.ico文件
    favicon_ico_path = os.path.join(web_dir, "favicon.ico")
    if os.path.exists(favicon_ico_path):
        @app.get("/favicon.ico", include_in_schema=False)
        async def serve_favicon_ico():
            return FileResponse(favicon_ico_path, media_type="image/x-icon")
    
    # 兜底路由：将所有非API请求重定向到index.html，支持前端路由
    @app.get("{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        # 排除API路径
        if path.startswith(api_prefix.strip("/")):
            raise HTTPException(status_code=404, detail="Not Found")
        
        # 检查请求的文件是否存在
        file_path = os.path.join(web_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # 为PNG文件设置正确的MIME类型
            media_type = "image/png" if path.lower().endswith(".png") else None
            return FileResponse(file_path, media_type=media_type)
        
        # 否则返回index.html，由前端路由处理
        index_path = os.path.join(web_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        raise HTTPException(status_code=404, detail="Not Found")
        
    return app
