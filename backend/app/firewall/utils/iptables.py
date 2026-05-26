import subprocess
import re
import shutil
from typing import List, Dict


class IptablesManager:
    def __init__(self):
        self.cmd = shutil.which('iptables') or "/usr/sbin/iptables"
        self.systemctl = shutil.which('systemctl') or "/usr/bin/systemctl"

    def status(self) -> bool:
        try:
            result = subprocess.run(
                [self.cmd, "-L", "-n"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            pass

        try:
            result = subprocess.run(
                [self.systemctl, "is-active", "iptables"],
                capture_output=True, text=True, timeout=5
            )
            if "active" in result.stdout:
                return True
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["/etc/init.d/iptables", "status"],
                capture_output=True, text=True, timeout=5
            )
            return "not running" not in result.stdout
        except Exception:
            return False

    def version(self) -> str:
        try:
            result = subprocess.run(
                [self.cmd, "-v"],
                capture_output=True, text=True, timeout=5
            )
            return result.stderr.split()[1] if result.stderr else "unknown"
        except Exception:
            return "unknown"

    def start(self) -> Dict:
        try:
            subprocess.run([self.systemctl, "start", "iptables"], check=True, timeout=10)
            return {"status": True, "msg": "iptables已启动"}
        except Exception as e:
            return {"status": False, "msg": f"启动iptables失败: {str(e)}"}

    def stop(self) -> Dict:
        try:
            subprocess.run([self.systemctl, "stop", "iptables"], check=True, timeout=10)
            return {"status": True, "msg": "iptables已停止"}
        except Exception as e:
            return {"status": False, "msg": f"停止iptables失败: {str(e)}"}

    def restart(self) -> Dict:
        try:
            subprocess.run(["/etc/init.d/iptables", "restart"], check=True, timeout=15)
            return {"status": True, "msg": "iptables已重启"}
        except Exception as e:
            return {"status": False, "msg": f"重启iptables失败: {str(e)}"}

    def reload(self) -> Dict:
        try:
            subprocess.run(["/etc/init.d/iptables", "save"], check=True, timeout=10)
            subprocess.run(["/etc/init.d/iptables", "restart"], check=True, timeout=10)
            return {"status": True, "msg": "iptables已重载"}
        except Exception as e:
            return {"status": False, "msg": f"重载iptables失败: {str(e)}"}

    def list_port_rules(self) -> List[Dict]:
        rules = []
        try:
            result = subprocess.run(
                [self.cmd, "-L", "INPUT", "-nv", "--line-numbers"],
                capture_output=True, text=True, timeout=5
            )
            protocol_map = {"6": "tcp", "17": "udp", "0": "all"}
            for line in result.stdout.split("\n"):
                if "dpt:" not in line:
                    continue
                parts = line.split()
                if len(parts) < 10:
                    continue
                target = parts[3]
                if target not in ("ACCEPT", "DROP", "REJECT"):
                    continue
                proto = protocol_map.get(parts[4], parts[4])
                if "dpt:" in parts[-1]:
                    port = parts[-1].split(":")[1]
                elif "dpt:" in parts[-5]:
                    port = parts[-5].split(":")[1]
                else:
                    continue
                address = parts[8] if "0.0.0.0/0" not in parts[8] else "all"
                rules.append({
                    "Port": port,
                    "Protocol": proto,
                    "Strategy": target.lower(),
                    "Address": address,
                    "Chain": "INPUT",
                })
        except Exception:
            pass
        return rules

    def list_ip_rules(self) -> List[Dict]:
        rules = []
        try:
            result = subprocess.run(
                [self.cmd, "-L", "INPUT", "-nv", "--line-numbers"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Chain") or "dpt:" in line:
                    continue
                parts = line.split()
                if len(parts) < 10:
                    continue
                target = parts[3]
                if target not in ("ACCEPT", "DROP", "REJECT"):
                    continue
                if "0.0.0.0/0" in parts[8]:
                    continue
                rules.append({
                    "Address": parts[8],
                    "Strategy": target.lower(),
                    "Chain": "INPUT",
                })
        except Exception:
            pass
        return rules

    def add_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        try:
            action = "-A" if chain == "OUTPUT" else "-I"
            subprocess.run(
                [self.cmd, action, chain, "-p", protocol, "-m", "state", "--state", "NEW",
                 "-m", protocol, "--dport", port, "-j", "ACCEPT"],
                check=True, capture_output=True, timeout=5
            )
            return {"status": True, "msg": f"端口 {port}/{protocol} 放行成功"}
        except Exception as e:
            return {"status": False, "msg": f"添加端口规则失败: {str(e)}"}

    def remove_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        try:
            action = "-D"
            subprocess.run(
                [self.cmd, action, chain, "-p", protocol, "-m", "state", "--state", "NEW",
                 "-m", protocol, "--dport", port, "-j", "ACCEPT"],
                check=True, capture_output=True, timeout=5
            )
            return {"status": True, "msg": f"端口 {port}/{protocol} 删除成功"}
        except Exception as e:
            return {"status": False, "msg": f"删除端口规则失败: {str(e)}"}

    def add_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        action = "DROP" if strategy == "drop" else "ACCEPT"
        try:
            subprocess.run(
                [self.cmd, "-I", "INPUT", "-s", address, "-j", action],
                check=True, capture_output=True, timeout=5
            )
            return {"status": True, "msg": f"IP {address} 已{strategy}"}
        except Exception as e:
            return {"status": False, "msg": f"添加IP规则失败: {str(e)}"}

    def remove_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        action = "DROP" if strategy == "drop" else "ACCEPT"
        try:
            subprocess.run(
                [self.cmd, "-D", "INPUT", "-s", address, "-j", action],
                check=True, capture_output=True, timeout=5
            )
            return {"status": True, "msg": f"IP {address} 规则已删除"}
        except Exception as e:
            return {"status": False, "msg": f"删除IP规则失败: {str(e)}"}
