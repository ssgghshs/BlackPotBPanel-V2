import re
import os
import json
import asyncio
import socket
from datetime import datetime
from typing import List, Tuple, Dict, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

import logging

logger = logging.getLogger(__name__)

from config.settings import settings
from app.firewall.models import FirewallRule, FirewallIpRule, FirewallForward, FirewallCountryRule
from app.firewall.schemas import (
    PortRuleCreate, PortRuleUpdate,
    IpRuleCreate, IpRuleUpdate,
    ForwardCreate, ForwardUpdate,
    FirewallOperationResponse,
    MergedPortRuleItem,
    MergedIpRuleItem,
    CountryRuleCreate, CountryRuleUpdate, CountryInfo,
    CountryRuleBatchDeleteItem,
)
from app.firewall.utils.firewalld import FirewalldManager
from app.firewall.utils.ufw import UfwManager
from app.firewall.utils.iptables import IptablesManager
from app.firewall.utils.ipset import IpsetManager


class FirewallService:
    _firewall_instance = None

    @classmethod
    def _get_firewall(cls):
        if cls._firewall_instance is not None:
            return cls._firewall_instance

        if os.path.exists('/usr/sbin/firewalld') or os.path.exists('/etc/redhat-release'):
            cls._firewall_instance = FirewalldManager()
            logger.info("检测到系统防火墙: firewalld")
        elif os.path.exists('/usr/sbin/ufw') or os.path.exists('/usr/bin/apt-get'):
            cls._firewall_instance = UfwManager()
            logger.info("检测到系统防火墙: ufw")
        else:
            cls._firewall_instance = IptablesManager()
            logger.info("检测到系统防火墙: iptables")

        return cls._firewall_instance

    @classmethod
    def get_firewall_type(cls) -> str:
        fw = cls._get_firewall()
        if isinstance(fw, FirewalldManager):
            return "firewalld"
        elif isinstance(fw, UfwManager):
            return "ufw"
        else:
            return "iptables"

    @classmethod
    async def get_status(cls) -> Dict:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()
        status = await loop.run_in_executor(None, fw.status)
        return {"status": status, "type": cls.get_firewall_type()}

    @classmethod
    async def get_firewall_info(cls, db: AsyncSession) -> Dict:
        fw = cls._get_firewall()
        fw_type = cls.get_firewall_type()
        loop = asyncio.get_running_loop()
        status = await loop.run_in_executor(None, fw.status)
        logger.debug(f"防火墙状态检测: type={fw_type}, status={status}")

        fw_port_rules = await loop.run_in_executor(None, fw.list_port_rules)
        fw_ip_rules = await loop.run_in_executor(None, fw.list_ip_rules)
        port_count = len(fw_port_rules)
        ip_count = len(fw_ip_rules)

        forward_count = await db.execute(select(func.count(FirewallForward.id)))

        is_ping = True
        try:
            sysctl_path = '/etc/sysctl.conf'
            if os.path.exists(sysctl_path):
                loop = asyncio.get_running_loop()
                def check_ping():
                    with open(sysctl_path, 'r') as f:
                        content = f.read()
                    match = re.search(r"#*net\.ipv4\.icmp_echo_ignore_all\s*=\s*([0-9]+)", content)
                    if match and match.group(1) == '1':
                        return False
                    return True
                is_ping = await loop.run_in_executor(None, check_ping)
        except Exception:
            pass

        country_count_result = await db.execute(select(func.count(FirewallCountryRule.id)))
        country_count = country_count_result.scalar()

        return {
            "port": port_count,
            "ip": ip_count,
            "trans": forward_count.scalar(),
            "country": country_count,
            "ping": is_ping,
            "status": status,
            "type": cls.get_firewall_type(),
        }

    @classmethod
    async def set_status(cls, action: str) -> FirewallOperationResponse:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        action_map = {
            "start": fw.start,
            "stop": fw.stop,
            "restart": fw.restart,
            "reload": fw.reload,
        }

        if action not in action_map:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {action}")

        result = await loop.run_in_executor(None, action_map[action])
        return FirewallOperationResponse(success=result["status"], message=result["msg"])

    @classmethod
    async def set_ping(cls, status: str) -> FirewallOperationResponse:
        filename = '/etc/sysctl.conf'
        if not os.path.exists(filename):
            return FirewallOperationResponse(success=False, message="/etc/sysctl.conf 文件不存在")

        loop = asyncio.get_running_loop()

        def update_sysctl():
            with open(filename, 'r') as f:
                conf = f.read()
            if 'net.ipv4.icmp_echo' in conf:
                conf = re.sub(
                    r"net\.ipv4\.icmp_echo.*",
                    f'net.ipv4.icmp_echo_ignore_all={status}\n',
                    conf
                )
            else:
                conf += f'\nnet.ipv4.icmp_echo_ignore_all={status}\n'
            with open(filename, 'w') as f:
                f.write(conf)
            import subprocess
            subprocess.run(["/usr/sbin/sysctl", "-p"], check=True, capture_output=True, timeout=5)

        try:
            await loop.run_in_executor(None, update_sysctl)
            msg = "已禁Ping" if status == "1" else "已允许Ping"
            return FirewallOperationResponse(success=True, message=msg)
        except Exception as e:
            return FirewallOperationResponse(success=False, message=f"设置失败: {str(e)}")

    @classmethod
    def _check_port_status(cls, port: str, protocol: str) -> int:
        if ":" in port or "-" in port or port.find(".") != -1:
            return -1
        try:
            port_int = int(port)
            proto = protocol.lower()
            if 'tcp' in proto:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(('127.0.0.1', port_int))
                s.close()
                return 2
            return 0
        except Exception:
            return 0

    @classmethod
    async def get_port_rules(
        cls, db: AsyncSession, skip: int = 0, limit: int = 100, query: str = ""
    ) -> Tuple[List[MergedPortRuleItem], int]:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        sys_rules = await loop.run_in_executor(None, fw.list_port_rules)

        db_result = await db.execute(select(FirewallRule))
        db_rules = db_result.scalars().all()

        db_index = {}
        for r in db_rules:
            key = "{}|{}|{}|{}|{}".format(
                r.port, r.protocol, r.strategy, r.address, r.chain
            ).lower()
            db_index[key] = r

        merged = []
        seen_keys = set()

        for sr in sys_rules:
            port = sr.get("Port", "")
            protocol = sr.get("Protocol", "tcp")
            strategy = sr.get("Strategy", "accept")
            address = sr.get("Address", "all")
            chain = sr.get("Chain", "INPUT")

            match_key = "{}|{}|{}|{}|{}".format(
                port, protocol, strategy, address, chain
            ).lower()
            seen_keys.add(match_key)

            db_rule = db_index.get(match_key)
            if db_rule:
                merged.append(MergedPortRuleItem(
                    id=db_rule.id,
                    port=port,
                    protocol=protocol,
                    strategy=strategy,
                    address=address,
                    chain=chain,
                    brief=db_rule.brief or "",
                    addtime=db_rule.addtime.strftime("%Y-%m-%d %H:%M:%S") if db_rule.addtime else "--",
                    status=cls._check_port_status(port, protocol),
                    stype="1",
                ))
            else:
                merged.append(MergedPortRuleItem(
                    port=port,
                    protocol=protocol,
                    strategy=strategy,
                    address=address,
                    chain=chain,
                    status=cls._check_port_status(port, protocol),
                    stype="0",
                ))

        for r in db_rules:
            match_key = "{}|{}|{}|{}|{}".format(
                r.port, r.protocol, r.strategy, r.address, r.chain
            ).lower()
            if match_key not in seen_keys:
                merged.append(MergedPortRuleItem(
                    id=r.id,
                    port=r.port,
                    protocol=r.protocol,
                    strategy=r.strategy,
                    address=r.address,
                    chain=r.chain,
                    brief=r.brief or "",
                    addtime=r.addtime.strftime("%Y-%m-%d %H:%M:%S") if r.addtime else "--",
                    status=cls._check_port_status(r.port, r.protocol),
                    stype="1",
                ))

        merged.sort(key=lambda x: x.addtime, reverse=True)

        if query:
            q = query.lower()
            merged = [m for m in merged if q in m.port.lower() or q in m.brief.lower() or q in m.address.lower()]

        total = len(merged)
        paged = merged[skip:skip + limit]
        return paged, total

    @classmethod
    async def create_port_rule(cls, db: AsyncSession, rule_data: PortRuleCreate) -> FirewallRule:
        existing = await db.execute(
            select(FirewallRule).where(
                FirewallRule.port == rule_data.port,
                FirewallRule.protocol == rule_data.protocol,
                FirewallRule.chain == rule_data.chain,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="端口规则已存在")

        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, fw.add_port_rule, rule_data.port, rule_data.protocol, rule_data.chain
        )
        if not result["status"]:
            raise HTTPException(status_code=500, detail=result["msg"])

        db_rule = FirewallRule(**rule_data.model_dump())
        db.add(db_rule)
        await db.commit()
        await db.refresh(db_rule)
        return db_rule

    @classmethod
    async def delete_port_rule(cls, db: AsyncSession, rule_id: int, port: str, protocol: str, chain: str) -> None:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        sys_result = await loop.run_in_executor(
            None, fw.remove_port_rule, port, protocol, chain
        )
        if not sys_result["status"]:
            logger.warning(f"删除系统防火墙端口规则失败: {sys_result['msg']}")

        if rule_id > 0:
            result = await db.execute(select(FirewallRule).where(FirewallRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                raise HTTPException(status_code=404, detail="端口规则不存在")
            await db.execute(delete(FirewallRule).where(FirewallRule.id == rule_id))
            await db.commit()

    @classmethod
    async def update_port_rule(cls, db: AsyncSession, rule_id: int, rule_data: PortRuleUpdate) -> FirewallRule:
        result = await db.execute(select(FirewallRule).where(FirewallRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="端口规则不存在")

        update_dict = rule_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        old_port = rule.port
        old_protocol = rule.protocol
        old_chain = rule.chain

        new_port = update_dict.get("port", old_port)
        new_protocol = update_dict.get("protocol", old_protocol)
        new_chain = update_dict.get("chain", old_chain)

        if new_port != old_port or new_protocol != old_protocol or new_chain != old_chain:
            remove_result = await loop.run_in_executor(
                None, fw.remove_port_rule, old_port, old_protocol, old_chain
            )
            if not remove_result["status"]:
                logger.warning(f"删除旧端口规则失败: {remove_result['msg']}")

            add_result = await loop.run_in_executor(
                None, fw.add_port_rule, new_port, new_protocol, new_chain
            )
            if not add_result["status"]:
                raise HTTPException(status_code=500, detail=add_result["msg"])

        for key, value in update_dict.items():
            setattr(rule, key, value)

        await db.commit()
        await db.refresh(rule)
        return rule

    @classmethod
    async def get_ip_rules(
        cls, db: AsyncSession, skip: int = 0, limit: int = 100, query: str = ""
    ) -> Tuple[List[MergedIpRuleItem], int]:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        sys_rules = await loop.run_in_executor(None, fw.list_ip_rules)

        db_result = await db.execute(select(FirewallIpRule))
        db_rules = db_result.scalars().all()

        db_index = {}
        for r in db_rules:
            key = "{}|{}|{}".format(r.address, r.strategy, r.chain).lower()
            db_index[key] = r

        merged = []
        seen_keys = set()

        for sr in sys_rules:
            address = sr.get("Address", "")
            strategy = sr.get("Strategy", "drop")
            chain = sr.get("Chain", "INPUT")

            match_key = "{}|{}|{}".format(address, strategy, chain).lower()
            seen_keys.add(match_key)

            db_rule = db_index.get(match_key)
            if db_rule:
                merged.append(MergedIpRuleItem(
                    id=db_rule.id,
                    address=address,
                    strategy=strategy,
                    chain=chain,
                    brief=db_rule.brief or "",
                    addtime=db_rule.addtime.strftime("%Y-%m-%d %H:%M:%S") if db_rule.addtime else "--",
                    stype="1",
                ))
            else:
                merged.append(MergedIpRuleItem(
                    address=address,
                    strategy=strategy,
                    chain=chain,
                    stype="0",
                ))

        for r in db_rules:
            match_key = "{}|{}|{}".format(r.address, r.strategy, r.chain).lower()
            if match_key not in seen_keys:
                merged.append(MergedIpRuleItem(
                    id=r.id,
                    address=r.address,
                    strategy=r.strategy,
                    chain=r.chain,
                    brief=r.brief or "",
                    addtime=r.addtime.strftime("%Y-%m-%d %H:%M:%S") if r.addtime else "--",
                    stype="1",
                ))

        merged.sort(key=lambda x: x.addtime, reverse=True)

        if query:
            q = query.lower()
            merged = [m for m in merged if q in m.address.lower() or q in m.brief.lower()]

        total = len(merged)
        paged = merged[skip:skip + limit]
        return paged, total

    @classmethod
    async def create_ip_rule(cls, db: AsyncSession, rule_data: IpRuleCreate) -> FirewallIpRule:
        existing = await db.execute(
            select(FirewallIpRule).where(
                FirewallIpRule.address == rule_data.address,
                FirewallIpRule.chain == rule_data.chain,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="IP规则已存在")

        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, fw.add_ip_rule, rule_data.address, rule_data.strategy
        )
        if not result["status"]:
            raise HTTPException(status_code=500, detail=result["msg"])

        db_rule = FirewallIpRule(**rule_data.model_dump())
        db.add(db_rule)
        await db.commit()
        await db.refresh(db_rule)
        return db_rule

    @classmethod
    async def delete_ip_rule(cls, db: AsyncSession, rule_id: int, address: str, strategy: str) -> None:
        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()
        sys_result = await loop.run_in_executor(
            None, fw.remove_ip_rule, address, strategy
        )
        if not sys_result["status"]:
            logger.warning(f"删除系统防火墙IP规则失败: {sys_result['msg']}")

        if rule_id > 0:
            result = await db.execute(select(FirewallIpRule).where(FirewallIpRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                raise HTTPException(status_code=404, detail="IP规则不存在")
            await db.execute(delete(FirewallIpRule).where(FirewallIpRule.id == rule_id))
            await db.commit()

    @classmethod
    async def update_ip_rule(cls, db: AsyncSession, rule_id: int, rule_data: IpRuleUpdate) -> FirewallIpRule:
        result = await db.execute(select(FirewallIpRule).where(FirewallIpRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="IP规则不存在")

        update_dict = rule_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        fw = cls._get_firewall()
        loop = asyncio.get_running_loop()

        old_address = rule.address
        old_strategy = rule.strategy

        new_address = update_dict.get("address", old_address)
        new_strategy = update_dict.get("strategy", old_strategy)

        if new_address != old_address or new_strategy != old_strategy:
            remove_result = await loop.run_in_executor(
                None, fw.remove_ip_rule, old_address, old_strategy
            )
            if not remove_result["status"]:
                logger.warning(f"删除旧IP规则失败: {remove_result['msg']}")

            add_result = await loop.run_in_executor(
                None, fw.add_ip_rule, new_address, new_strategy
            )
            if not add_result["status"]:
                raise HTTPException(status_code=500, detail=add_result["msg"])

        for key, value in update_dict.items():
            setattr(rule, key, value)

        await db.commit()
        await db.refresh(rule)
        return rule

    @classmethod
    async def get_forwards(
        cls, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Tuple[List[FirewallForward], int]:
        total_result = await db.execute(select(func.count(FirewallForward.id)))
        total = total_result.scalar()

        stmt = select(FirewallForward).order_by(FirewallForward.addtime.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        forwards = result.scalars().all()

        return forwards, total

    @classmethod
    async def create_forward(cls, db: AsyncSession, forward_data: ForwardCreate) -> FirewallForward:
        existing = await db.execute(
            select(FirewallForward).where(
                FirewallForward.S_Port == forward_data.S_Port,
                FirewallForward.T_Address == forward_data.T_Address,
                FirewallForward.T_Port == forward_data.T_Port,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="端口转发规则已存在")

        db_forward = FirewallForward(**forward_data.model_dump())
        db.add(db_forward)
        await db.commit()
        await db.refresh(db_forward)
        return db_forward

    @classmethod
    async def delete_forward(cls, db: AsyncSession, forward_id: int) -> None:
        result = await db.execute(select(FirewallForward).where(FirewallForward.id == forward_id))
        forward = result.scalar_one_or_none()
        if not forward:
            raise HTTPException(status_code=404, detail="端口转发规则不存在")

        await db.execute(delete(FirewallForward).where(FirewallForward.id == forward_id))
        await db.commit()

    @classmethod
    async def update_forward(cls, db: AsyncSession, forward_id: int, forward_data: ForwardUpdate) -> FirewallForward:
        result = await db.execute(select(FirewallForward).where(FirewallForward.id == forward_id))
        forward = result.scalar_one_or_none()
        if not forward:
            raise HTTPException(status_code=404, detail="端口转发规则不存在")

        update_dict = forward_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        for key, value in update_dict.items():
            setattr(forward, key, value)

        await db.commit()
        await db.refresh(forward)
        return forward

    # ==================== 地区规则 ====================

    _country_ip_cache = None
    _country_name_map = None
    _ipset_manager = None

    _COUNTRY_NAMES_CN_FALLBACK = {
        "US": "美国", "CN": "中国", "JP": "日本", "KR": "韩国",
        "GB": "英国", "DE": "德国", "FR": "法国", "IT": "意大利",
        "RU": "俄罗斯", "CA": "加拿大", "AU": "澳大利亚", "BR": "巴西",
        "IN": "印度", "SG": "新加坡", "HK": "中国香港", "TW": "中国台湾",
        "MO": "中国澳门", "NL": "荷兰", "SE": "瑞典", "NO": "挪威",
        "FI": "芬兰", "DK": "丹麦", "ES": "西班牙", "PT": "葡萄牙",
        "CH": "瑞士", "AT": "奥地利", "BE": "比利时", "IE": "爱尔兰",
        "PL": "波兰", "CZ": "捷克", "SK": "斯洛伐克", "HU": "匈牙利",
        "RO": "罗马尼亚", "GR": "希腊", "TR": "土耳其", "IL": "以色列",
        "SA": "沙特阿拉伯", "AE": "阿联酋", "ZA": "南非", "EG": "埃及",
        "NG": "尼日利亚", "AR": "阿根廷", "MX": "墨西哥", "CO": "哥伦比亚",
        "CL": "智利", "PE": "秘鲁", "NZ": "新西兰", "TH": "泰国",
        "VN": "越南", "ID": "印度尼西亚", "MY": "马来西亚", "PH": "菲律宾",
        "PK": "巴基斯坦", "BD": "孟加拉国", "UA": "乌克兰", "KZ": "哈萨克斯坦",
        "IR": "伊朗", "IQ": "伊拉克", "KW": "科威特", "QA": "卡塔尔",
        "LU": "卢森堡", "MT": "马耳他", "EE": "爱沙尼亚", "LV": "拉脱维亚",
        "LT": "立陶宛", "SI": "斯洛文尼亚", "HR": "克罗地亚", "RS": "塞尔维亚",
        "BG": "保加利亚", "BY": "白俄罗斯", "MM": "缅甸", "KH": "柬埔寨",
        "LA": "老挝", "MN": "蒙古", "NP": "尼泊尔", "LK": "斯里兰卡",
        "UZ": "乌兹别克斯坦", "AZ": "阿塞拜疆", "GE": "格鲁吉亚",
        "KE": "肯尼亚", "TZ": "坦桑尼亚", "ET": "埃塞俄比亚",
        "MA": "摩洛哥", "DZ": "阿尔及利亚", "TN": "突尼斯",
    }

    @classmethod
    def _get_geoip_path(cls) -> str:
        geoip_path = settings.GEOIP_COUNTRY_DB_PATH
        if not os.path.isabs(geoip_path):
            geoip_path = os.path.abspath(geoip_path)
        return geoip_path

    @classmethod
    def _get_country_map_path(cls) -> str:
        map_path = settings.COUNTRY_CODE_MAP_PATH
        if not os.path.isabs(map_path):
            map_path = os.path.abspath(map_path)
        return map_path

    @classmethod
    def _load_country_name_map(cls) -> Dict[str, str]:
        if cls._country_name_map is not None:
            return cls._country_name_map

        map_path = cls._get_country_map_path()
        if os.path.exists(map_path):
            try:
                with open(map_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                result = {}
                for entry in raw_data:
                    code = entry.get("brief")
                    name = entry.get("CH")
                    if code and name:
                        result[code] = name
                cls._country_name_map = result
                logger.info(f"已加载国家代码映射: {len(result)} 条")
                return result
            except Exception as e:
                logger.warning(f"读取国家代码映射文件失败: {e}")

        cls._country_name_map = cls._COUNTRY_NAMES_CN_FALLBACK
        return cls._country_name_map

    @classmethod
    def _get_ipset_manager(cls) -> IpsetManager:
        if cls._ipset_manager is None:
            cls._ipset_manager = IpsetManager()
        return cls._ipset_manager

    @classmethod
    async def _load_country_ip_cache(cls) -> Dict[str, List[str]]:
        if cls._country_ip_cache is not None:
            return cls._country_ip_cache

        geoip_path = cls._get_geoip_path()
        if not os.path.exists(geoip_path):
            logger.error(f"GeoIP 数据库不存在: {geoip_path}")
            raise HTTPException(status_code=404, detail=f"GeoIP 数据库不存在: {geoip_path}")

        loop = asyncio.get_running_loop()

        def _read_json():
            with open(geoip_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            result = {}
            for entry in raw_data:
                code = entry.get("brief")
                ips = entry.get("ips", [])
                if code and ips:
                    result[code] = ips
            return result

        cls._country_ip_cache = await loop.run_in_executor(None, _read_json)
        logger.info(f"已加载 GeoIP 数据: {len(cls._country_ip_cache)} 个国家/地区")
        return cls._country_ip_cache

    @classmethod
    async def get_available_countries(cls) -> List[CountryInfo]:
        cache = await cls._load_country_ip_cache()
        name_map = cls._load_country_name_map()
        countries = []
        for code in sorted(cache.keys()):
            cn_name = name_map.get(code, code)
            countries.append(CountryInfo(country_code=code, country_name=cn_name))
        return countries

    @classmethod
    async def _get_networks_for_country(cls, country_code: str) -> List[str]:
        cache = await cls._load_country_ip_cache()
        networks = cache.get(country_code, [])
        if not networks:
            logger.warning(f"未找到国家 {country_code} 的 IP 段")
        return networks

    @classmethod
    def _get_ipset_name(cls, country_code: str) -> str:
        return f"in_bt_country_{country_code.lower()}"

    @classmethod
    async def get_country_rules(
        cls, db: AsyncSession, skip: int = 0, limit: int = 100, query: str = ""
    ) -> Tuple[List[FirewallCountryRule], int]:
        where_clauses = []
        if query:
            q = query.lower()
            db_rules = await db.execute(
                select(FirewallCountryRule).order_by(FirewallCountryRule.addtime.desc())
            )
            all_rules = db_rules.scalars().all()
            filtered = [
                r for r in all_rules
                if q in r.country_name.lower() or q in r.country_code.lower() or (r.brief and q in r.brief.lower())
            ]
            total = len(filtered)
            paged = filtered[skip:skip + limit]
            return paged, total

        total_result = await db.execute(select(func.count(FirewallCountryRule.id)))
        total = total_result.scalar()

        stmt = select(FirewallCountryRule).order_by(FirewallCountryRule.addtime.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        rules = result.scalars().all()

        return rules, total

    @classmethod
    async def create_country_rule(cls, db: AsyncSession, rule_data: CountryRuleCreate) -> List[FirewallCountryRule]:
        ipset_mgr = cls._get_ipset_manager()
        if not ipset_mgr.is_available():
            raise HTTPException(status_code=500, detail="ipset 不可用，无法创建地区规则")

        created_rules = []
        country_codes = rule_data.country_codes
        strategy = rule_data.strategy
        ports = rule_data.ports
        brief = rule_data.brief

        for code in country_codes:
            existing = await db.execute(
                select(FirewallCountryRule).where(
                    FirewallCountryRule.country_code == code,
                    FirewallCountryRule.strategy == strategy,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"国家 {code} 的地区规则已存在")

            country_name = cls._load_country_name_map().get(code, code)

            networks = await cls._get_networks_for_country(code)
            if not networks:
                raise HTTPException(status_code=404, detail=f"未找到国家 {code} 的 IP 段数据")

            ipset_name = cls._get_ipset_name(code)

            create_result = ipset_mgr.create_ipset(ipset_name)
            if not create_result["status"]:
                raise HTTPException(status_code=500, detail=f"创建 ipset 失败: {create_result['msg']}")

            restore_result = ipset_mgr.restore_ipset(ipset_name, networks)
            if not restore_result["status"]:
                ipset_mgr.destroy_ipset(ipset_name)
                raise HTTPException(status_code=500, detail=f"导入 IP 段失败: {restore_result['msg']}")

            rule_result = ipset_mgr.add_country_iptables_rule(ipset_name, strategy, ports)
            if not rule_result["status"]:
                ipset_mgr.destroy_ipset(ipset_name)
                raise HTTPException(status_code=500, detail=f"添加 iptables 规则失败: {rule_result['msg']}")

            db_rule = FirewallCountryRule(
                country_code=code,
                country_name=country_name,
                strategy=strategy,
                ports=ports,
                brief=brief,
            )
            db.add(db_rule)
            created_rules.append(db_rule)

        await db.commit()
        for rule in created_rules:
            await db.refresh(rule)

        return created_rules

    @classmethod
    async def delete_country_rule(cls, db: AsyncSession, rule_id: int, country_code: str, strategy: str, ports: str) -> None:
        result = await db.execute(select(FirewallCountryRule).where(FirewallCountryRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="地区规则不存在")

        ipset_name = cls._get_ipset_name(country_code)
        ipset_mgr = cls._get_ipset_manager()

        rule_result = ipset_mgr.remove_country_iptables_rule(ipset_name, strategy, ports)
        if not rule_result["status"]:
            logger.warning(f"删除 iptables 规则失败: {rule_result['msg']}")

        await asyncio.sleep(0.3)
        ipset_mgr.destroy_ipset(ipset_name)

        await db.execute(delete(FirewallCountryRule).where(FirewallCountryRule.id == rule_id))
        await db.commit()

    @classmethod
    async def batch_delete_country_rules(cls, db: AsyncSession, items: List[CountryRuleBatchDeleteItem]) -> int:
        deleted_count = 0
        ipset_mgr = cls._get_ipset_manager()

        for item in items:
            try:
                result = await db.execute(select(FirewallCountryRule).where(FirewallCountryRule.id == item.id))
                rule = result.scalar_one_or_none()
                if not rule:
                    logger.warning(f"地区规则不存在，跳过: id={item.id}")
                    continue

                ipset_name = cls._get_ipset_name(item.country_code)

                rule_result = ipset_mgr.remove_country_iptables_rule(ipset_name, item.strategy, item.ports)
                if not rule_result["status"]:
                    logger.warning(f"删除 iptables 规则失败: {rule_result['msg']}")

                await asyncio.sleep(0.3)
                ipset_mgr.destroy_ipset(ipset_name)

                await db.execute(delete(FirewallCountryRule).where(FirewallCountryRule.id == item.id))
                deleted_count += 1
            except Exception as e:
                logger.error(f"批量删除地区规则失败: id={item.id}, error={str(e)}")

        await db.commit()
        return deleted_count

    @classmethod
    async def update_country_rule(cls, db: AsyncSession, rule_id: int, rule_data: CountryRuleUpdate) -> FirewallCountryRule:
        result = await db.execute(select(FirewallCountryRule).where(FirewallCountryRule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="地区规则不存在")

        update_dict = rule_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        new_strategy = update_dict.get("strategy", rule.strategy)
        new_ports = update_dict.get("ports", rule.ports)
        strategy_changed = new_strategy != rule.strategy or new_ports != rule.ports

        if strategy_changed:
            ipset_mgr = cls._get_ipset_manager()
            if not ipset_mgr.is_available():
                raise HTTPException(status_code=500, detail="ipset 不可用")

            ipset_name = cls._get_ipset_name(rule.country_code)

            old_result = ipset_mgr.remove_country_iptables_rule(ipset_name, rule.strategy, rule.ports)
            if not old_result["status"]:
                logger.warning(f"删除旧 iptables 规则失败: {old_result['msg']}")

            new_result = ipset_mgr.add_country_iptables_rule(ipset_name, new_strategy, new_ports)
            if not new_result["status"]:
                logger.warning(f"添加新 iptables 规则失败: {new_result['msg']}")

        for key, value in update_dict.items():
            setattr(rule, key, value)

        await db.commit()
        await db.refresh(rule)
        return rule
