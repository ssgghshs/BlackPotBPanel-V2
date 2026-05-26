#!/bin/bash

# BlackPotBPanel 管理员密码修改工具
# ========================================

BASE_DIR="/opt/blackpotbpanel-v2"
BACKEND_DIR="$BASE_DIR/backend"
VENV_DIR="$BASE_DIR/venv"
DB_PATH="$BACKEND_DIR/db/app.db"
SERVICE_NAME="Blackpotbpanel"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}[错误] 请使用 root 用户运行此脚本${NC}"
        exit 1
    fi
}

check_dependencies() {
    if [ ! -f "$VENV_DIR/bin/python" ]; then
        echo -e "${RED}[错误] 未找到 Python 虚拟环境: $VENV_DIR/bin/python${NC}"
        exit 1
    fi
    if [ ! -f "$DB_PATH" ]; then
        echo -e "${RED}[错误] 未找到数据库文件: $DB_PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓] 环境检查通过${NC}"
}

change_password() {
    echo -e "${YELLOW}==============================${NC}"
    echo -e "${YELLOW}  修改管理员密码${NC}"
    echo -e "${YELLOW}==============================${NC}"
    echo ""

    local service_running=false
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        service_running=true
        echo -e "${YELLOW}[提示] 面板服务正在运行，修改密码后建议重启服务生效${NC}"
        echo ""
    fi

    read -s -p "请输入新密码: " new_password
    echo ""
    if [ -z "$new_password" ]; then
        echo -e "${RED}[错误] 密码不能为空${NC}"
        return 1
    fi

    read -s -p "请再次输入新密码: " confirm_password
    echo ""
    if [ "$new_password" != "$confirm_password" ]; then
        echo -e "${RED}[错误] 两次输入的密码不一致${NC}"
        return 1
    fi

    if [ ${#new_password} -lt 6 ]; then
        echo -e "${RED}[错误] 密码长度不能少于 6 位${NC}"
        return 1
    fi

    echo ""
    echo -e "${YELLOW}[信息] 正在更新密码...${NC}"

    "$VENV_DIR/bin/python" -c "
import sqlite3
import sys
sys.path.insert(0, '$BACKEND_DIR')
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
hashed = pwd_context.hash('$new_password')
conn = sqlite3.connect('$DB_PATH')
cursor = conn.cursor()
cursor.execute(\"UPDATE users SET hashed_password = ? WHERE username = 'admin'\", (hashed,))
if cursor.rowcount == 0:
    print('FAIL:USER_NOT_FOUND')
else:
    conn.commit()
    print('SUCCESS')
conn.close()
" 2>/dev/null

    local result=$?
    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}[成功] 管理员密码已修改${NC}"
        if [ "$service_running" = true ]; then
            echo ""
            read -p "是否立即重启面板服务使新密码生效？(y/n): " restart_confirm
            if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
                systemctl restart "$SERVICE_NAME" 2>/dev/null
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}[成功] 面板服务已重启${NC}"
                else
                    echo -e "${RED}[错误] 重启失败，请手动重启${NC}"
                fi
            else
                echo -e "${YELLOW}[提示] 请手动重启面板服务使新密码生效${NC}"
            fi
        fi
    else
        echo -e "${RED}[错误] 密码修改失败${NC}"
        return 1
    fi
}

main() {
    check_root
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  BlackPotBPanel 管理员密码修改工具${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    check_dependencies
    echo ""
    change_password
    echo ""
}

main
