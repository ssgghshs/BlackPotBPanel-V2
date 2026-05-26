"""
CC (Challenge Collapsar) 防护测试脚本

测试目标: WAF 的 CC 频率限制功能
默认配置: max_requests=100, time_window=60s
用法: python test_cc.py
"""

import requests
import time
import sys
import json
import os

# ====== 配置区域 ======
TARGET_URL = "http://192.168.223.180:81/"
WAF_LOG_PATH = "d:/pycharm/pythonproject/blackpotbpanel/blackpotbpanel-v2/blackpotbpanel-v2/server/waf/logs/waf.log"

TOTAL_REQUESTS = 110  # 超过 max_requests(100)
BURST_SIZE = 50       # 每批发送数
PAUSE_BETWEEN = 0.5   # 批次间隔（秒）

HEADERS = {
    "User-Agent": "CC-Test-Script/1.0",
    "Accept": "text/html"
}

VERIFY_LOG = True     # 发送完成后检查 waf.log

# ====================


def send_burst(session, url, count, label):
    """发送一批请求并统计状态码"""
    status_count = {}
    start = time.time()

    for i in range(count):
        try:
            r = session.get(url, headers=HEADERS, timeout=3)
            code = r.status_code
            status_count[code] = status_count.get(code, 0) + 1
        except requests.exceptions.ConnectionError as e:
            status_count["conn_err"] = status_count.get("conn_err", 0) + 1
        except requests.exceptions.Timeout:
            status_count["timeout"] = status_count.get("timeout", 0) + 1
        except Exception as e:
            status_count["error"] = status_count.get("error", 0) + 1

        if (i + 1) % 10 == 0:
            elapsed = time.time() - start
            print(f"  [{label}] {i + 1}/{count} 完成 ({elapsed:.1f}s)")

    elapsed = time.time() - start
    print(f"  [{label}] 全部完成: {elapsed:.1f}s")
    return status_count


def check_waf_log(expected_ip):
    """检查 waf.log 中的 CC 日志条目"""
    if not os.path.exists(WAF_LOG_PATH):
        print(f"\n[!] waf.log 不存在: {WAF_LOG_PATH}")
        return

    cc_count = 0
    scanner_count = 0
    other_count = 0

    with open(WAF_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("client_ip") != expected_ip:
                    continue
                if entry.get("attack_type") == "cc":
                    cc_count += 1
                elif entry.get("attack_type") == "scanner":
                    scanner_count += 1
                else:
                    other_count += 1
            except json.JSONDecodeError:
                pass

    print(f"\n【waf.log 检查】IP: {expected_ip}")
    print(f"  CC 攻击日志: {cc_count} 条")
    print(f"  Scanner 日志: {scanner_count} 条")
    print(f"  其他类型日志: {other_count} 条")

    if cc_count > 0:
        print(f"  ✅ CC 防护日志正常记录 ({cc_count} 条)")
    else:
        print(f"  ❌ 未找到 CC 日志！攻击可能被 scanner 或其他模块提前拦截")
        if scanner_count > 0:
            print(f"     → scanner 拦截了 {scanner_count} 条，CC 没机会执行")


def main():
    print("=" * 50)
    print("  WAF CC 防护测试")
    print("=" * 50)

    # 0. 获取本机 IP
    try:
        my_ip = requests.get("https://api.ipify.org", timeout=5).text
    except Exception:
        my_ip = requests.get("http://httpbin.org/ip", timeout=5).json()["origin"]

    print(f"\n[1] 本机 IP: {my_ip}")
    print(f"[2] 目标: {TARGET_URL}")
    print(f"[3] 发送 {TOTAL_REQUESTS} 个请求，含 User-Agent 避免触发 scanner")

    session = requests.Session()

    # 第一波：BURST_SIZE 个请求
    print(f"\n[4] 第一波: {BURST_SIZE} 个请求")
    s1 = send_burst(session, TARGET_URL, BURST_SIZE, "第一波")

    time.sleep(PAUSE_BETWEEN)

    # 第二波：剩余请求
    remaining = TOTAL_REQUESTS - BURST_SIZE
    print(f"\n[5] 第二波: {remaining} 个请求")
    s2 = send_burst(session, TARGET_URL, remaining, "第二波")

    # 汇总
    all_stats = {}
    for code, cnt in s1.items():
        all_stats[code] = all_stats.get(code, 0) + cnt
    for code, cnt in s2.items():
        all_stats[code] = all_stats.get(code, 0) + cnt

    print(f"\n【汇总】共 {TOTAL_REQUESTS} 个请求:")
    for code in sorted(str(k) for k in all_stats):
        cnt = all_stats.get(code, 0) or all_stats.get(int(code) if code.isdigit() else 0, 0)
        print(f"  状态码 {code}: {all_stats.get(code, all_stats.get(int(code) if code.isdigit() else code, 0))} 次")

    # 说明
    print(f"\n【预期结果】")
    print(f"  前 {100} 个请求 → 200 OK（正常通过）")
    print(f"  第 {101} 个开始 → 200 OK + 日志记录（record 模式）或 403（block 模式）")
    print(f"  waf.log 中应出现 attack_type=cc 的日志条目")

    # 检查日志
    if VERIFY_LOG:
        check_waf_log(my_ip)

    print("\n完成。")


if __name__ == "__main__":
    main()
