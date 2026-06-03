import time
import hashlib
import requests

# ====== 配置 ======
API_KEY = ""   # 面板生成的密钥
BASE_URL = "http://127.0.0.1:8000"  # 面板地址

print("=== 1. 当前时间戳请求（应成功）===")
timestamp = str(int(time.time()))
raw = f"blackpotbpanel{API_KEY}{timestamp}"
token = hashlib.md5(raw.encode()).hexdigest()

headers = {
    "Blackpotbpanel-Token": token,
    "Blackpotbpanel-Timestamp": timestamp,
}

resp = requests.get(f"{BASE_URL}/api/v2/monitor/system-info", headers=headers)
print(f"Status: {resp.status_code}")
print(resp.json())

print("\n=== 2. 过期时间戳请求（应 401）===")
# 有效期设置 120 分钟，用一个 3 小时前的时间戳
old_ts = str(int(time.time()) - 10800)  # 10800秒 = 3小时前
raw_old = f"blackpotbpanel{API_KEY}{old_ts}"
old_token = hashlib.md5(raw_old.encode()).hexdigest()

old_headers = {
    "Blackpotbpanel-Token": old_token,
    "Blackpotbpanel-Timestamp": old_ts,
}

resp = requests.get(f"{BASE_URL}/api/v2/monitor/system-info", headers=old_headers)
print(f"Status: {resp.status_code}")
print(resp.json())