import json
import os
from typing import Dict, List
from config.settings import settings
from app.waf.schemas import WAFBlackWhiteListResponse, WAFBlackWhiteListEntry, WAFURLWhiteListResponse


class WAFRulesService:
    """WAF规则服务类"""
    
    @staticmethod
    def get_blackwhite_list() -> WAFBlackWhiteListResponse:
        """获取IP黑白名单列表
        
        从配置文件中读取IP黑白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_BLACKWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "blackwhite", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回空列表
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 解析白名单
            white_list = []
            for item in config.get('white_list', []):
                white_list.append(WAFBlackWhiteListEntry(
                    name=item.get('name', ''),
                    enabled=item.get('enabled', False),
                    description=item.get('description', ''),
                    ips=item.get('ips', [])
                ))
            
            # 解析黑名单
            black_list = []
            for item in config.get('black_list', []):
                black_list.append(WAFBlackWhiteListEntry(
                    name=item.get('name', ''),
                    enabled=item.get('enabled', False),
                    description=item.get('description', ''),
                    ips=item.get('ips', [])
                ))
            
            return WAFBlackWhiteListResponse(
                white_list=white_list,
                black_list=black_list,
                message="success get blackwhite list"
            )
            
        except Exception as e:
            # 处理异常，返回空列表
            return WAFBlackWhiteListResponse(
                white_list=[],
                black_list=[],
                message=f"error: {str(e)}"
            )
    
    @staticmethod
    def update_blackwhite_group(list_type: str, group_name: str, update_data: dict) -> WAFBlackWhiteListResponse:
        """编辑指定IP组
        
        Args:
            list_type: 列表类型，'white' 或 'black'
            group_name: 组名称
            update_data: 更新数据
            
        Returns:
            更新后的黑白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_BLACKWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "blackwhite", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回空列表
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确定要更新的列表
            list_key = f"{list_type}_list"
            target_list = config.get(list_key, [])
            
            # 查找并更新指定组
            group_found = False
            for group in target_list:
                if group.get('name') == group_name:
                    # 如果更新了IP列表，检查是否与另一个列表中的IP重复
                    if 'ips' in update_data:
                        new_ips = update_data['ips']
                        other_list_type = 'white' if list_type == 'black' else 'black'
                        other_list_key = f"{other_list_type}_list"
                        other_list = config.get(other_list_key, [])
                        
                        for ip in new_ips:
                            for other_group in other_list:
                                # 跳过当前正在更新的组（如果是重命名的情况）
                                if other_group.get('name') == group_name:
                                    continue
                                if ip in other_group.get('ips', []):
                                    return WAFBlackWhiteListResponse(
                                        white_list=[],
                                        black_list=[],
                                        message=f"IP {ip} already exists in {other_list_type} list"
                                    )
                    
                    # 更新组信息
                    if 'name' in update_data:
                        group['name'] = update_data['name']
                    if 'enabled' in update_data:
                        group['enabled'] = update_data['enabled']
                    if 'description' in update_data:
                        group['description'] = update_data['description']
                    if 'ips' in update_data:
                        group['ips'] = update_data['ips']
                    group_found = True
                    break
            
            if not group_found:
                return WAFBlackWhiteListResponse(
                    white_list=[],
                    black_list=[],
                    message=f"Group {group_name} not found in {list_type} list"
                )
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 重新读取并返回更新后的配置
            return WAFRulesService.get_blackwhite_list()
            
        except Exception as e:
            # 处理异常，返回空列表
            return WAFBlackWhiteListResponse(
                white_list=[],
                black_list=[],
                message=f"error: {str(e)}"
            )
    
    @staticmethod
    def delete_blackwhite_group(list_type: str, group_name: str) -> WAFBlackWhiteListResponse:
        """删除指定IP组
        
        Args:
            list_type: 列表类型，'white' 或 'black'
            group_name: 组名称
            
        Returns:
            删除后的黑白名单配置
        """
        try:
            # 禁止删除名为Blocked IPs的组
            if group_name == "Blocked IPs":
                return WAFBlackWhiteListResponse(
                    white_list=[],
                    black_list=[],
                    message="Cannot delete 'Blocked IPs' group"
                )
            
            # 获取配置文件路径
            config_path = settings.WAF_BLACKWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "blackwhite", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回空列表
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确定要删除的列表
            list_key = f"{list_type}_list"
            target_list = config.get(list_key, [])
            
            # 查找并删除指定组
            group_found = False
            updated_list = []
            for group in target_list:
                if group.get('name') != group_name:
                    updated_list.append(group)
                else:
                    group_found = True
            
            if not group_found:
                return WAFBlackWhiteListResponse(
                    white_list=[],
                    black_list=[],
                    message=f"Group {group_name} not found in {list_type} list"
                )
            
            # 更新配置
            config[list_key] = updated_list
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 重新读取并返回更新后的配置
            return WAFRulesService.get_blackwhite_list()
            
        except Exception as e:
            # 处理异常，返回空列表
            return WAFBlackWhiteListResponse(
                white_list=[],
                black_list=[],
                message=f"error: {str(e)}"
            )
    
    @staticmethod
    def add_blackwhite_group(list_type: str, group_data: dict) -> WAFBlackWhiteListResponse:
        """添加IP组
        
        Args:
            list_type: 列表类型，'white' 或 'black'
            group_data: 组数据
            
        Returns:
            添加后的黑白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_BLACKWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "blackwhite", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回空列表
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 确定要添加的列表
            list_key = f"{list_type}_list"
            target_list = config.get(list_key, [])
            
            # 检查是否已存在同名组
            group_name = group_data.get('name')
            for group in target_list:
                if group.get('name') == group_name:
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message=f"Group {group_name} already exists in {list_type} list"
                    )
            
            # 检查IP是否已存在于另一个列表中
            new_ips = group_data.get('ips', [])
            other_list_type = 'white' if list_type == 'black' else 'black'
            other_list_key = f"{other_list_type}_list"
            other_list = config.get(other_list_key, [])
            
            for ip in new_ips:
                for group in other_list:
                    if ip in group.get('ips', []):
                        return WAFBlackWhiteListResponse(
                            white_list=[],
                            black_list=[],
                            message=f"IP {ip} already exists in {other_list_type} list"
                        )
            
            # 添加新组
            new_group = {
                'name': group_data.get('name'),
                'enabled': group_data.get('enabled'),
                'description': group_data.get('description'),
                'ips': new_ips
            }
            target_list.append(new_group)
            
            # 更新配置
            config[list_key] = target_list
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 重新读取并返回更新后的配置
            return WAFRulesService.get_blackwhite_list()
            
        except Exception as e:
            # 处理异常，返回空列表
            return WAFBlackWhiteListResponse(
                white_list=[],
                black_list=[],
                message=f"error: {str(e)}"
            )
    
    @staticmethod
    def block_ip(ip: str) -> WAFBlackWhiteListResponse:
        """拉黑IP到Blocked IPs组
        
        Args:
            ip: 要拉黑的IP地址
            
        Returns:
            更新后的黑白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_BLACKWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "blackwhite", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回空列表
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查IP是否已存在于白名单中
            white_list = config.get('white_list', [])
            for group in white_list:
                if ip in group.get('ips', []):
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message=f"IP {ip} already exists in white list"
                    )
            
            # 检查IP是否已存在于黑名单中
            black_list = config.get('black_list', [])
            for group in black_list:
                if ip in group.get('ips', []):
                    return WAFBlackWhiteListResponse(
                        white_list=[],
                        black_list=[],
                        message=f"IP {ip} already exists in black list"
                    )
            
            # 查找或创建Blocked IPs组
            blocked_ips_group = None
            for group in black_list:
                if group.get('name') == "Blocked IPs":
                    blocked_ips_group = group
                    break
            
            if not blocked_ips_group:
                # 创建Blocked IPs组
                blocked_ips_group = {
                    'name': "Blocked IPs",
                    'enabled': True,
                    'description': "Automatically blocked IPs",
                    'ips': []
                }
                black_list.append(blocked_ips_group)
            
            # 添加IP到Blocked IPs组
            blocked_ips_group['ips'].append(ip)
            
            # 更新配置
            config['black_list'] = black_list
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 重新读取并返回更新后的配置
            return WAFRulesService.get_blackwhite_list()
            
        except Exception as e:
            # 处理异常，返回空列表
            return WAFBlackWhiteListResponse(
                white_list=[],
                black_list=[],
                message=f"error: {str(e)}"
            )
    
    @staticmethod
    def get_url_white_list() -> WAFURLWhiteListResponse:
        """获取URL白名单列表
        
        从配置文件中读取URL白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_URLWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "urlwhitelist", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，返回默认值
                    return WAFURLWhiteListResponse(
                        enabled=False,
                        normal_routes=[],
                        static_paths=[],
                        static_extensions=[],
                        message="Config file not found"
                    )
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 解析配置
            enabled = config.get('enabled', False)
            normal_routes = config.get('normal_routes', [])
            static_paths = config.get('static_paths', [])
            static_extensions = config.get('static_extensions', [])
            
            return WAFURLWhiteListResponse(
                enabled=enabled,
                normal_routes=normal_routes,
                static_paths=static_paths,
                static_extensions=static_extensions,
                message="success get url white list"
            )
            
        except Exception as e:
            # 处理异常，返回默认值
            return WAFURLWhiteListResponse(
                enabled=False,
                normal_routes=[],
                static_paths=[],
                static_extensions=[],
                message=f"error: {str(e)}"
            )

    @staticmethod
    def get_protection_rules() -> Dict:
        """Get all protection rules configuration

        Reads all config.json files from subdirectories under WAF_RULES_PATH
        (excluding blackwhite and urlwhitelist which have their own APIs).

        Returns:
            Dictionary containing protection rules list
        """
        rule_name_map = {
            'bot': 'BOT',
            'cc': 'CC Protection',
            'cmd': 'Command Injection',
            'csrf': 'CSRF',
            'file_inclusion': 'File Inclusion',
            'file_upload': 'File Upload',
            'ldap_injection': 'LDAP Injection',
            'scanner': 'Scanner',
            'sql': 'SQL Injection',
            'ssrf': 'SSRF',
            'xss': 'XSS'
        }

        config_field_map = {
            'bot': ['whitelist'],
            'cc': ['max_requests', 'time_window', 'block_duration'],
            'cmd': ['rules'],
            'csrf': ['check_origin', 'check_referer', 'allowed_origins', 'allowed_referers', 'protected_methods', 'exclude_paths'],
            'file_inclusion': ['rules', 'exclude_paths'],
            'file_upload': ['max_file_size', 'check_content', 'allowed_extensions', 'forbidden_extensions', 'allowed_types', 'forbidden_types', 'forbidden_content', 'exclude_paths'],
            'ldap_injection': ['rules'],
            'scanner': ['scanner_user_agents', 'scanner_headers', 'scanner_paths', 'exclude_paths', 'allowed_crawlers'],
            'sql': ['rules'],
            'ssrf': ['rules'],
            'xss': ['rules']
        }

        try:
            rules = []
            rules_path = settings.WAF_RULES_PATH
            exclude_dirs = {'blackwhite', 'urlwhitelist'}

            if not os.path.exists(rules_path):
                return {"rules": [], "message": "Rules directory not found"}

            for rule_dir in os.listdir(rules_path):
                if rule_dir in exclude_dirs:
                    continue

                config_file = os.path.join(rules_path, rule_dir, 'config.json')
                if not os.path.exists(config_file):
                    continue

                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except Exception:
                    config = {}

                fields = config_field_map.get(rule_dir, ['rules'])
                filtered_config = {}
                for field in fields:
                    if field in config:
                        filtered_config[field] = config[field]

                rules.append({
                    "rule_key": rule_dir,
                    "rule_name": rule_name_map.get(rule_dir, rule_dir.replace('_', ' ').title()),
                    "config": filtered_config
                })

            return {
                "rules": rules,
                "message": "success get protection rules"
            }

        except Exception as e:
            return {
                "rules": [],
                "message": f"error: {str(e)}"
            }

    @staticmethod
    def update_protection_rule(rule_key: str, update_config: dict) -> Dict:
        """Update a single protection rule's config.json

        Reads the existing config.json for the specified rule_key,
        merges in the update_config fields (only fields defined in
        config_field_map are written), and writes back the config file.

        Args:
            rule_key: Rule type identifier (bot/cc/cmd/csrf/...)
            update_config: Dict containing the fields to update

        Returns:
            Dictionary with rule_key, rule_name, updated config, and message
        """
        rule_name_map = {
            'bot': 'BOT',
            'cc': 'CC Protection',
            'cmd': 'Command Injection',
            'csrf': 'CSRF',
            'file_inclusion': 'File Inclusion',
            'file_upload': 'File Upload',
            'ldap_injection': 'LDAP Injection',
            'scanner': 'Scanner',
            'sql': 'SQL Injection',
            'ssrf': 'SSRF',
            'xss': 'XSS'
        }

        config_field_map = {
            'bot': ['whitelist'],
            'cc': ['max_requests', 'time_window', 'block_duration'],
            'cmd': ['rules'],
            'csrf': ['check_origin', 'check_referer', 'allowed_origins', 'allowed_referers', 'protected_methods', 'exclude_paths'],
            'file_inclusion': ['rules', 'exclude_paths'],
            'file_upload': ['max_file_size', 'check_content', 'allowed_extensions', 'forbidden_extensions', 'allowed_types', 'forbidden_types', 'forbidden_content', 'exclude_paths'],
            'ldap_injection': ['rules'],
            'scanner': ['scanner_user_agents', 'scanner_headers', 'scanner_paths', 'exclude_paths', 'allowed_crawlers'],
            'sql': ['rules'],
            'ssrf': ['rules'],
            'xss': ['rules']
        }

        try:
            exclude_dirs = {'blackwhite', 'urlwhitelist'}
            if rule_key in exclude_dirs:
                return {
                    "rule_key": rule_key,
                    "rule_name": "",
                    "config": {},
                    "message": f"Rule type '{rule_key}' is not a protection rule"
                }

            rules_path = settings.WAF_RULES_PATH
            config_file = os.path.join(rules_path, rule_key, 'config.json')

            if not os.path.exists(config_file):
                return {
                    "rule_key": rule_key,
                    "rule_name": "",
                    "config": {},
                    "message": f"Config file for rule '{rule_key}' not found"
                }

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            allowed_fields = config_field_map.get(rule_key, ['rules'])
            for field in allowed_fields:
                if field in update_config:
                    config[field] = update_config[field]

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            filtered_config = {}
            for field in allowed_fields:
                if field in config:
                    filtered_config[field] = config[field]

            return {
                "rule_key": rule_key,
                "rule_name": rule_name_map.get(rule_key, rule_key.replace('_', ' ').title()),
                "config": filtered_config,
                "message": "success update protection rule"
            }

        except Exception as e:
            return {
                "rule_key": rule_key,
                "rule_name": "",
                "config": {},
                "message": f"error: {str(e)}"
            }
    
    @staticmethod
    def update_url_white_list(update_data: dict) -> WAFURLWhiteListResponse:
        """更新URL白名单
        
        Args:
            update_data: 更新数据
            
        Returns:
            更新后的URL白名单配置
        """
        try:
            # 获取配置文件路径
            config_path = settings.WAF_URLWHITE_CONFIG_PATH
            
            # 检查文件是否存在
            if not os.path.exists(config_path):
                # 如果配置文件不存在，尝试使用相对路径
                relative_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", "..", "..", 
                    "server", "waf", "rules", "urlwhitelist", "config.json"
                )
                if os.path.exists(relative_path):
                    config_path = relative_path
                else:
                    # 如果文件不存在，创建默认配置
                    config = {
                        'enabled': False,
                        'normal_routes': [],
                        'static_paths': [],
                        'static_extensions': []
                    }
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新配置
            if 'enabled' in update_data:
                config['enabled'] = update_data['enabled']
            if 'normal_routes' in update_data:
                config['normal_routes'] = update_data['normal_routes']
            if 'static_paths' in update_data:
                config['static_paths'] = update_data['static_paths']
            if 'static_extensions' in update_data:
                config['static_extensions'] = update_data['static_extensions']
            
            # 写回配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 重新读取并返回更新后的配置
            return WAFRulesService.get_url_white_list()
            
        except Exception as e:
            # 处理异常，返回默认值
            return WAFURLWhiteListResponse(
                enabled=False,
                normal_routes=[],
                static_paths=[],
                static_extensions=[],
                message=f"error: {str(e)}"
            )