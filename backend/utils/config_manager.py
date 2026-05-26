import os
import json
from typing import Dict, Any
from config.settings import settings

class ConfigManager:
    """配置管理器，用于管理访问日志配置文件"""
    
    def __init__(self, config_file_path: str = None):
        # 如果没有指定配置文件路径，则使用默认路径
        if config_file_path is None:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_file_path = os.path.join(current_dir, "data", "access.json")
        else:
            self.config_file_path = config_file_path
            
        # 确保配置文件存在
        self._ensure_config_file_exists()
    
    def _ensure_config_file_exists(self):
        """确保配置文件存在，如果不存在则创建默认配置"""
        if not os.path.exists(self.config_file_path):
            default_config = {
                "access_log_path": settings.ACCESS_LOG_PATH,
                "error_log_path": settings.ERROR_LOG_PATH
            }
            self.save_config(default_config)
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            # 如果配置文件不存在，创建默认配置
            if not os.path.exists(self.config_file_path):
                self._ensure_config_file_exists()
                
            # 读取配置文件
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    # 如果文件为空，返回默认配置
                    return {
                        "access_log_path": settings.ACCESS_LOG_PATH,
                        "error_log_path": settings.ERROR_LOG_PATH
                    }
        except Exception as e:
            # 如果读取失败，返回默认配置
            return {
                "access_log_path": settings.ACCESS_LOG_PATH,
                "error_log_path": settings.ERROR_LOG_PATH
            }
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置文件的目录存在
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
            
            # 写入配置文件
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            return False

# 创建全局配置管理器实例
config_manager = ConfigManager()