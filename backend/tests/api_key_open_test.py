import time
import hashlib
import requests

# ====== 配置 ======
API_KEY = ""   # 面板生成的密钥
BASE_URL = ""             # 面板地址

# ====== 生成 Token ======
timestamp = str(int(time.time()))
raw = f"blackpotbpanel{API_KEY}{timestamp}"
token = hashlib.md5(raw.encode()).hexdigest()

# ====== 发起请求 ======
headers = {
    "Blackpotbpanel-Token": token,
    "Blackpotbpanel-Timestamp": timestamp,
}

resp = requests.get(f"{BASE_URL}/api/v2/monitor/system-info", headers=headers)
print(f"Status: {resp.status_code}")
print(resp.json())