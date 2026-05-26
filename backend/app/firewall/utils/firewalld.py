import subprocess
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional


class FirewalldManager:
    def __init__(self):
        self.cmd = "/usr/bin/firewall-cmd"
        self.systemctl = "/usr/bin/systemctl"
        self.public_xml = "/etc/firewalld/zones/public.xml"

    def status(self) -> bool:
        try:
            result = subprocess.run(
                [self.cmd, "--state"],
                capture_output=True, text=True, timeout=5
            )
            return "running" in result.stdout
        except Exception:
            try:
                result = subprocess.run(
                    [self.systemctl, "is-active", "firewalld"],
                    capture_output=True, text=True, timeout=5
                )
                return "active" in result.stdout
            except Exception:
                return False

    def version(self) -> str:
        try:
            result = subprocess.run(
                [self.cmd, "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def start(self) -> Dict:
        try:
            subprocess.run([self.systemctl, "start", "firewalld"], check=True, timeout=10)
            return {"status": True, "msg": "firewalld已启动"}
        except Exception as e:
            return {"status": False, "msg": f"启动firewalld失败: {str(e)}"}

    def stop(self) -> Dict:
        try:
            subprocess.run([self.systemctl, "stop", "firewalld"], check=True, timeout=10)
            return {"status": True, "msg": "firewalld已停止"}
        except Exception as e:
            return {"status": False, "msg": f"停止firewalld失败: {str(e)}"}

    def restart(self) -> Dict:
        try:
            subprocess.run([self.systemctl, "restart", "firewalld"], check=True, timeout=15)
            return {"status": True, "msg": "firewalld已重启"}
        except Exception as e:
            return {"status": False, "msg": f"重启firewalld失败: {str(e)}"}

    def reload(self) -> Dict:
        try:
            subprocess.run([self.cmd, "--reload"], check=True, timeout=10)
            return {"status": True, "msg": "firewalld已重载"}
        except Exception as e:
            return {"status": False, "msg": f"重载firewalld失败: {str(e)}"}

    def list_port_rules(self) -> List[Dict]:
        rules = []
        if not os.path.exists(self.public_xml):
            return rules
        try:
            tree = ET.parse(self.public_xml)
            root = tree.getroot()
            for elem in root:
                if elem.tag == "port":
                    rules.append({
                        "Port": elem.attrib.get("port"),
                        "Protocol": elem.attrib.get("protocol", "tcp"),
                        "Strategy": "accept",
                        "Address": "all",
                        "Chain": "INPUT",
                    })
        except Exception:
            pass
        return rules

    def list_ip_rules(self) -> List[Dict]:
        rules = []
        if not os.path.exists(self.public_xml):
            return rules
        try:
            tree = ET.parse(self.public_xml)
            root = tree.getroot()
            for elem in root:
                if elem.tag != "rule":
                    continue
                rule = {"Family": elem.attrib.get("family", "ipv4")}
                strategy = "accept"
                address = None
                for sub in elem:
                    if sub.tag == "source":
                        address = sub.attrib.get("address", "all")
                    elif sub.tag == "drop":
                        strategy = "drop"
                    elif sub.tag == "reject":
                        strategy = "reject"
                    elif sub.tag == "accept":
                        strategy = "accept"
                if address:
                    rule["Address"] = address
                    rule["Strategy"] = strategy
                    rule["Chain"] = "INPUT"
                    rules.append(rule)
        except Exception:
            pass
        return rules

    def add_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        if chain == "OUTPUT":
            return self._add_output_port_rule(port, protocol)
        try:
            port_str = port.replace(":", "-")
            subprocess.run(
                [self.cmd, "--zone=public", f"--add-port={port_str}/{protocol}", "--permanent"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"端口 {port}/{protocol} 放行成功"}
        except Exception as e:
            return {"status": False, "msg": f"添加端口规则失败: {str(e)}"}

    def _add_output_port_rule(self, port: str, protocol: str = "tcp") -> Dict:
        try:
            port_str = port.replace(":", ":")
            subprocess.run(
                [self.cmd, "--permanent", "--direct", "--add-rule", "ipv4", "filter", "OUTPUT", "0",
                 "-p", protocol, "--dport", port_str, "-j", "ACCEPT"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"出站端口 {port}/{protocol} 放行成功"}
        except Exception as e:
            return {"status": False, "msg": f"添加出站端口规则失败: {str(e)}"}

    def remove_port_rule(self, port: str, protocol: str = "tcp", chain: str = "INPUT") -> Dict:
        if chain == "OUTPUT":
            return self._remove_output_port_rule(port, protocol)
        try:
            port_str = port.replace(":", "-")
            subprocess.run(
                [self.cmd, "--zone=public", f"--remove-port={port_str}/{protocol}", "--permanent"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"端口 {port}/{protocol} 删除成功"}
        except Exception as e:
            return {"status": False, "msg": f"删除端口规则失败: {str(e)}"}

    def _remove_output_port_rule(self, port: str, protocol: str = "tcp") -> Dict:
        try:
            port_str = port.replace(":", ":")
            subprocess.run(
                [self.cmd, "--permanent", "--direct", "--remove-rule", "ipv4", "filter", "OUTPUT", "0",
                 "-p", protocol, "--dport", port_str, "-j", "ACCEPT"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"出站端口 {port}/{protocol} 删除成功"}
        except Exception as e:
            return {"status": False, "msg": f"删除出站端口规则失败: {str(e)}"}

    def add_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        try:
            family = "ipv6" if ":" in address else "ipv4"
            subprocess.run(
                [self.cmd, "--permanent",
                 f"--add-rich-rule=rule family={family} source address=\"{address}\" {strategy}"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"IP {address} 已{strategy}"}
        except Exception as e:
            return {"status": False, "msg": f"添加IP规则失败: {str(e)}"}

    def remove_ip_rule(self, address: str, strategy: str = "drop") -> Dict:
        try:
            family = "ipv6" if ":" in address else "ipv4"
            subprocess.run(
                [self.cmd, "--permanent",
                 f"--remove-rich-rule=rule family={family} source address=\"{address}\" {strategy}"],
                check=True, capture_output=True, timeout=10
            )
            subprocess.run([self.cmd, "--reload"], check=True, capture_output=True, timeout=10)
            return {"status": True, "msg": f"IP {address} 规则已删除"}
        except Exception as e:
            return {"status": False, "msg": f"删除IP规则失败: {str(e)}"}
