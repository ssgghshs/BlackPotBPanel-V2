import subprocess
import re
from typing import List, Dict


class UfwManager:
    def __init__(self):
        self.cmd = "/usr/sbin/ufw"
        self.systemctl = "/usr/bin/systemctl"

    def status(self) -> bool:
        try:
            result = subprocess.run(
                [self.cmd, "status", "verbose"],
                capture_output=True, text=True, timeout=5
            )
            if "Status: active" in result.stdout:
                return True
            if "Status: inactive" in result.stdout:
                return False
        except Exception:
            pass

        try:
            result = subprocess.run(
                [self.systemctl, "is-active", "ufw"],
                capture_output=True, text=True, timeout=5
            )
            return "active" in result.stdout
        except Exception:
            return False

    def version(self) -> str:
        try:
            result = subprocess.run(
                [self.cmd, "version"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.replace("ufw ", "").strip()
        except Exception:
            return "unknown"

    def start(self) -> Dict:
        try:
            subprocess.run(
                ["/usr/bin/bash", "-c", f"echo y | {self.cmd} enable"],
                check=True, timeout=10
            )
            return {"status": True, "msg": "ufw已启动"}
        except Exception as e:
            return {"status": False, "msg": f"启动ufw失败: {str(e)}"}

    def stop(self) -> Dict:
        try:
            subprocess.run([self.cmd, "disable"], check=True, timeout=10)
            return {"status": True, "msg": "ufw已停止"}
        except Exception as e:
            return {"status": False, "msg": f"停止ufw失败: {str(e)}"}

    def restart(self) -> Dict:
        try:
            subprocess.run([self.cmd, "disable"], check=True, timeout=10)
            subprocess.run(
                ["/usr/bin/bash", "-c", f"echo y | {self.cmd} enable"],
                check=True, timeout=10
            )
            return {"status": True, "msg": "ufw已重启"}
        except Exception as e:
            return {"status": False, "msg": f"重启ufw失败: {str(e)}"}

    def reload(self) -> Dict:
        try:
            subprocess.run([self.cmd, "reload"], check=True, timeout=10)
            return {"status": True, "msg": "ufw已重载"}
        except Exception as e:
            return {"status": False, "msg": f"重载ufw失败: {str(e)}"}

    def _parse_rules_output(self) -> List[str]:
        result = subprocess.run(
            [self.cmd, "status", "verbose"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.split("\n")
        is_start = False
        rules = []
        for line in lines:
            if "fail2ban" in line.lower():
                continue
            if "(v6)" in line:
                continue
            if line.startswith("-"):
                is_start = True
                continue
            if not is_start or not line.strip():
                continue
            rules.append(line)
        return rules

    def _parse_rule_line(self, line: str, rule_type: str = "port") -> Dict:
        parts = line.split()
        if not parts:
            return {}

        action = "unknown"
        for p in parts:
            pl = p.lower()
            if pl in ("allow", "deny", "reject", "limit"):
                action = pl
                break

        proto = "tcp/udp"
        port = ""
        address = "all"
        chain = "INPUT"
        direction = parts[-1].lower() if len(parts) > 1 else "in"

        if direction == "out":
            chain = "OUTPUT"

        for p in parts:
            if "/" in p and p.split("/")[0].isdigit():
                port = p.split("/")[0]
                proto = p.split("/")[1]
                break
            elif p.isdigit():
                port = p
                break

        for p in parts:
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", p):
                address = p
                break

        if rule_type == "port":
            return {
                "Port": port.replace(":", "-") if port else "",
                "Protocol": proto,
                "Strategy": "accept" if action == "allow" else "drop",
                "Address": address,
                "Chain": chain,
            }
        else:
            return {
                "Address": address,
                "Strategy": "accept" if action == "allow" else "drop",
                "Chain": chain,
            }

    def list_port_rules(self) -> List[Dict]:
        rules = []
        try:
            raw_rules = self._parse_rules_output()
            for line in raw_rules:
                item = self._parse_rule_line(line, "port")
                if item.get("Port") and item["Port"] != "Anywhere" and "." not in item["Port"]:
                    rules.append(item)
        except Exception:
            pass
        return rules

    def list_ip_rules(self) -> List[Dict]:
        rules = []
        try:
            raw_rules = self._parse_rules_output()
            for line in raw_rules:
                item = self._parse_rule_line(line, "address")
                if item.get("Address") and item["Address"] != "Anywhere" and "." in item["Address"]:
                    rules.append(item)
        except Exception:
            pass
        return rules

    def add_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        try:
            protos = protocol.split("/") if "/" in protocol else [protocol]
            for proto in protos:
                if chain == "OUTPUT":
                    subprocess.run(
                        [self.cmd, "allow", "out", f"{port}/{proto}"],
                        check=True, capture_output=True, timeout=5
                    )
                else:
                    subprocess.run(
                        [self.cmd, "allow", f"{port}/{proto}"],
                        check=True, capture_output=True, timeout=5
                    )
            return {"status": True, "msg": f"端口 {port}/{protocol} 放行成功"}
        except Exception as e:
            return {"status": False, "msg": f"添加端口规则失败: {str(e)}"}

    def remove_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        try:
            protos = protocol.split("/") if "/" in protocol else [protocol]
            for proto in protos:
                if chain == "OUTPUT":
                    cmd_with = [self.cmd, "delete", "allow", "out", f"{port}/{proto}"]
                    cmd_fallback = [self.cmd, "delete", "allow", "out", port]
                else:
                    cmd_with = [self.cmd, "delete", "allow", f"{port}/{proto}"]
                    cmd_fallback = [self.cmd, "delete", "allow", port]
                try:
                    subprocess.run(cmd_with, check=True, capture_output=True, timeout=5)
                except subprocess.CalledProcessError:
                    subprocess.run(cmd_fallback, check=True, capture_output=True, timeout=5)
            return {"status": True, "msg": f"端口 {port}/{protocol} 删除成功"}
        except Exception as e:
            return {"status": False, "msg": f"删除端口规则失败: {str(e)}"}

    def add_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        try:
            if strategy == "drop":
                subprocess.run(
                    [self.cmd, "deny", "from", address],
                    check=True, capture_output=True, timeout=5
                )
            else:
                subprocess.run(
                    [self.cmd, "allow", "from", address],
                    check=True, capture_output=True, timeout=5
                )
            return {"status": True, "msg": f"IP {address} 已{strategy}"}
        except Exception as e:
            return {"status": False, "msg": f"添加IP规则失败: {str(e)}"}

    def remove_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        try:
            if strategy == "drop":
                subprocess.run(
                    [self.cmd, "delete", "deny", "from", address],
                    check=True, capture_output=True, timeout=5
                )
            else:
                subprocess.run(
                    [self.cmd, "delete", "allow", "from", address],
                    check=True, capture_output=True, timeout=5
                )
            return {"status": True, "msg": f"IP {address} 规则已删除"}
        except Exception as e:
            return {"status": False, "msg": f"删除IP规则失败: {str(e)}"}
