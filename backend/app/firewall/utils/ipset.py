import subprocess
import os
import shutil
import tempfile
from typing import List, Dict, Optional


class IpsetManager:
    def __init__(self):
        self.ipset_cmd = shutil.which('ipset') or "/usr/sbin/ipset"
        self.iptables_cmd = shutil.which('iptables') or "/usr/sbin/iptables"
        self.ip6tables_cmd = shutil.which('ip6tables') or "/usr/sbin/ip6tables"
        self._country_chain = "IN_BT_Country"

    def _check_ipset_available(self) -> bool:
        if not self.ipset_cmd:
            return False
        try:
            subprocess.run([self.ipset_cmd, "version"], capture_output=True, timeout=3)
            return True
        except Exception:
            return False

    def _ensure_country_chain(self) -> bool:
        try:
            result = subprocess.run(
                [self.iptables_cmd, "-n", "-L", self._country_chain],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                subprocess.run(
                    [self.iptables_cmd, "-N", self._country_chain],
                    check=True, capture_output=True, timeout=5
                )
                subprocess.run(
                    [self.iptables_cmd, "-I", "INPUT", "-j", self._country_chain],
                    check=True, capture_output=True, timeout=5
                )
            return True
        except Exception:
            return False

    def create_ipset(self, ipset_name: str, maxelem: int = 1000000) -> Dict:
        try:
            result = subprocess.run(
                [self.ipset_cmd, "list", ipset_name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                subprocess.run(
                    [self.ipset_cmd, "flush", ipset_name],
                    check=True, capture_output=True, timeout=5
                )
                return {"status": True, "msg": f"ipset {ipset_name} 已存在，已清空"}
            subprocess.run(
                [self.ipset_cmd, "create", ipset_name, "hash:net", "maxelem", str(maxelem)],
                check=True, capture_output=True, timeout=10
            )
            return {"status": True, "msg": f"ipset {ipset_name} 创建成功"}
        except subprocess.CalledProcessError as e:
            return {"status": False, "msg": f"创建 ipset 失败: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {"status": False, "msg": f"创建 ipset 异常: {str(e)}"}

    def destroy_ipset(self, ipset_name: str) -> Dict:
        try:
            result = subprocess.run(
                [self.ipset_cmd, "list", ipset_name],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return {"status": True, "msg": f"ipset {ipset_name} 不存在"}
            subprocess.run(
                [self.ipset_cmd, "destroy", ipset_name],
                check=True, capture_output=True, timeout=10
            )
            return {"status": True, "msg": f"ipset {ipset_name} 已销毁"}
        except Exception as e:
            return {"status": False, "msg": f"销毁 ipset 失败: {str(e)}"}

    def restore_ipset(self, ipset_name: str, networks: List[str]) -> Dict:
        if not networks:
            return {"status": False, "msg": "IP 段列表为空"}
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                for net in networks:
                    f.write(f"add {ipset_name} {net}\n")
                tmp_path = f.name
            result = subprocess.run(
                [self.ipset_cmd, "restore", "-f", tmp_path],
                capture_output=True, text=True, timeout=60
            )
            os.unlink(tmp_path)
            if result.returncode != 0:
                return {"status": False, "msg": f"导入 IP 段失败: {result.stderr}"}
            return {"status": True, "msg": f"已导入 {len(networks)} 个 IP 段到 {ipset_name}"}
        except Exception as e:
            return {"status": False, "msg": f"恢复 ipset 异常: {str(e)}"}

    def add_country_iptables_rule(self, ipset_name: str, strategy: str, ports: Optional[str] = None) -> Dict:
        self._ensure_country_chain()
        action = "ACCEPT" if strategy == "accept" else "DROP"
        try:
            if ports:
                for port in ports.split(','):
                    port = port.strip()
                    if not port:
                        continue
                    subprocess.run(
                        [self.iptables_cmd, "-I", self._country_chain,
                         "-m", "set", "--match-set", ipset_name, "src",
                         "-p", "tcp", "--destination-port", port, "-j", action],
                        check=True, capture_output=True, timeout=5
                    )
            else:
                subprocess.run(
                    [self.iptables_cmd, "-I", self._country_chain,
                     "-m", "set", "--match-set", ipset_name, "src", "-j", action],
                    check=True, capture_output=True, timeout=5
                )
            return {"status": True, "msg": f"iptables 规则添加成功"}
        except subprocess.CalledProcessError as e:
            return {"status": False, "msg": f"添加 iptables 规则失败: {e.stderr.decode() if e.stderr else str(e)}"}
        except Exception as e:
            return {"status": False, "msg": f"添加 iptables 规则异常: {str(e)}"}

    def remove_country_iptables_rule(self, ipset_name: str, strategy: str, ports: Optional[str] = None) -> Dict:
        action = "ACCEPT" if strategy == "accept" else "DROP"
        try:
            if ports:
                for port in ports.split(','):
                    port = port.strip()
                    if not port:
                        continue
                    subprocess.run(
                        [self.iptables_cmd, "-D", self._country_chain,
                         "-m", "set", "--match-set", ipset_name, "src",
                         "-p", "tcp", "--destination-port", port, "-j", action],
                        check=True, capture_output=True, timeout=5
                    )
            else:
                subprocess.run(
                    [self.iptables_cmd, "-D", self._country_chain,
                     "-m", "set", "--match-set", ipset_name, "src", "-j", action],
                    check=True, capture_output=True, timeout=5
                )
            return {"status": True, "msg": f"iptables 规则删除成功"}
        except subprocess.CalledProcessError:
            return {"status": True, "msg": "iptables 规则已不存在"}
        except Exception as e:
            return {"status": False, "msg": f"删除 iptables 规则异常: {str(e)}"}

    def is_available(self) -> bool:
        return self._check_ipset_available()
