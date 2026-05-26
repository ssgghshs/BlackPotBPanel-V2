import os
import logging
import docker
import asyncio
from typing import Optional
from fastapi import HTTPException
from app.waf.schemas import WAFContainerStatus, WAFContainerActionResponse, WAFContainerExistsResponse

logger = logging.getLogger(__name__)


class WAFManagerService:
    """WAF容器管理服务类"""
    
    # WAF容器名称（从docker-compose.yml中获取）
    WAF_CONTAINER_NAME = "waf-openresty"
    
    @staticmethod
    async def get_waf_container_status() -> WAFContainerStatus:
        """获取WAF容器状态
        
        Returns:
            WAFContainerStatus: 包含容器状态信息的响应对象
        """
        try:
            loop = asyncio.get_running_loop()
            
            def get_status_sync():
                try:
                    client = docker.from_env()
                    
                    try:
                        container = client.containers.get(WAFManagerService.WAF_CONTAINER_NAME)
                        container_status = container.status.lower()
                        
                        # 映射Docker状态到标准状态
                        status_mapping = {
                            'running': 'running',
                            'exited': 'stopped',
                            'paused': 'paused',
                            'restarting': 'restarting',
                            'dead': 'dead',
                            'created': 'stopped'
                        }
                        
                        status = status_mapping.get(container_status, 'unknown')
                        
                        return WAFContainerStatus(
                            status=status,
                            message="success get waf container status"
                        )
                    except docker.errors.NotFound:
                        return WAFContainerStatus(
                            status="stopped",
                            message="waf container not found"
                        )
                    finally:
                        client.close()
                except Exception as e:
                    logger.error(f"获取WAF容器状态失败: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"get waf container status failed: {str(e)}"
                    )
            
            return await loop.run_in_executor(None, get_status_sync)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取WAF容器状态时发生错误: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"get waf container status failed: {str(e)}"
            )
    
    @staticmethod
    async def operate_waf_container(action: str) -> WAFContainerActionResponse:
        """操作WAF容器（启动/停止）
        
        Args:
            action: 操作类型，支持 'start' 或 'stop'
            
        Returns:
            WAFContainerActionResponse: 包含操作结果消息的响应对象
        """
        try:
            loop = asyncio.get_running_loop()
            
            def operate_container_sync():
                try:
                    client = docker.from_env()
                    
                    try:
                        container = client.containers.get(WAFManagerService.WAF_CONTAINER_NAME)
                        
                        if action == 'start':
                            container.start()
                            return WAFContainerActionResponse(
                                message="success start waf container"
                            )
                        elif action == 'stop':
                            container.stop()
                            return WAFContainerActionResponse(
                                message="success stop waf container"
                            )
                        elif action == 'restart':
                            container.restart()
                            return WAFContainerActionResponse(
                                message="success restart waf container"
                            )
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail=f"invalid action: {action}, only support 'start', 'stop' or 'restart'"
                            )
                    except docker.errors.NotFound:
                        raise HTTPException(
                            status_code=404,
                            detail="waf container not found"
                        )
                    finally:
                        client.close()
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"操作WAF容器失败: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"operate waf container failed: {str(e)}"
                    )
            
            return await loop.run_in_executor(None, operate_container_sync)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"操作WAF容器时发生错误: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"operate waf container failed: {str(e)}"
            )

    @staticmethod
    async def check_container_exists() -> WAFContainerExistsResponse:
        """检测WAF容器是否存在（是否安装）

        Returns:
            WAFContainerExistsResponse: 包含容器是否存在信息的响应对象
        """
        container_name = WAFManagerService.WAF_CONTAINER_NAME

        try:
            loop = asyncio.get_running_loop()

            def check_exists_sync():
                try:
                    client = docker.from_env()
                    try:
                        client.containers.get(container_name)
                        return WAFContainerExistsResponse(
                            exists=True,
                            container_name=container_name,
                            message="waf container exists"
                        )
                    except docker.errors.NotFound:
                        return WAFContainerExistsResponse(
                            exists=False,
                            container_name=container_name,
                            message="waf container not found, please install first"
                        )
                    finally:
                        client.close()
                except Exception as e:
                    logger.warning(f"连接Docker失败: {str(e)}")
                    return WAFContainerExistsResponse(
                        exists=False,
                        container_name=container_name,
                        message="docker unavailable or not installed"
                    )

            return await loop.run_in_executor(None, check_exists_sync)

        except Exception as e:
            logger.error(f"检测WAF容器是否存在时发生错误: {str(e)}")
            return WAFContainerExistsResponse(
                exists=False,
                container_name=container_name,
                message=f"check failed: {str(e)}"
            )
