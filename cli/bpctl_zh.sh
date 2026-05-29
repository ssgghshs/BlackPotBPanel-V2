#!/bin/bash

# BlackPotBPanel 面板管理工具
# ========================================

BASE_DIR="/opt/blackpotbpanel-v2"
BACKEND_DIR="$BASE_DIR/backend"
VENV_DIR="$BASE_DIR/venv"
CONFIG_FILE="$BASE_DIR/setting.conf"
SERVICE_NAME="Blackpotbpanel"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}[错误] 请使用 root 用户运行此脚本${NC}"
        exit 1
    fi
}

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "================================================================"
    echo "=                BlackPotBPanel 面板管理工具 v2.0                ="
    echo "=      __    __           __               __  __              ="
    echo "=     / /_  / /___ ______/ /______  ____  / /_/ /_  ____       ="
    echo "=    / __ \/ / __ \`/ ___/ //_/ __ \/ __ \/ __/ __ \/ __ \\    ="
    echo "=   / /_/ / / /_/ / /__/ ,< / /_/ / /_/ / /_/ /_/ / /_/ /      ="
    echo "=  /_.___/_/\__,_/\___/_/|_/ .___/\____/\__/_.___/ .___/       ="
    echo "=                         /_/                   /_/            ="
    echo "================================================================"
    echo -e "${NC}"
}

get_service_status() {
    local state
    state=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null)
    case "$state" in
        active)
            echo -e "${GREEN}[运行中]${NC}"
            ;;
        activating)
            echo -e "${YELLOW}[启动中]${NC}"
            ;;
        inactive)
            echo -e "${RED}[已停止]${NC}"
            ;;
        *)
            echo -e "${YELLOW}[未安装]${NC}"
            ;;
    esac
}

get_current_port() {
    local port
    port=$(grep -E "^PORT=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    echo "${port:-8000}"
}

get_ssl_status() {
    local ssl_enabled
    ssl_enabled=$(grep -E "^SSL_ENABLED=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ "$ssl_enabled" = "True" ]; then
        echo -e "${GREEN}[已开启]${NC}"
    else
        echo -e "${RED}[已关闭]${NC}"
    fi
}

print_menu() {
    local current_port
    current_port=$(get_current_port)
    local service_status
    service_status=$(get_service_status)
    local ssl_status
    ssl_status=$(get_ssl_status)
    local entrance_status
    entrance_status=$(get_security_entrance)

    echo -e "${YELLOW}面板状态信息：${NC}"
    echo "----------------------------------------"
    echo -e "  服务状态：    $(get_service_status)"
    echo -e "  监听端口：    ${BLUE}$current_port${NC}"
    echo -e "  SSL状态：     $ssl_status"
    echo -e "  安全入口：    $entrance_status"
    echo -e "  安装目录：    ${BLUE}$BASE_DIR${NC}"
    echo "----------------------------------------"
    echo ""
    echo -e "${YELLOW}请选择操作：${NC}"
    echo ""
    echo "  1) 启动面板服务"
    echo "  2) 停止面板服务"
    echo "  3) 重启面板服务"
    echo "  4) 修改面板端口"
    echo "  5) 开关面板 SSL"
    echo "  6) 修改 admin 密码"
    echo "  7) 修改面板入口"
    echo "  8) 卸载面板"
    echo "  0) 退出"
    echo ""
}

start_service() {
    echo -e "${YELLOW}[信息] 正在启动面板服务...${NC}"
    systemctl start "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[成功] 面板服务已启动${NC}"
    else
        systemctl daemon-reload 2>/dev/null
        systemctl start "$SERVICE_NAME" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[成功] 面板服务已启动${NC}"
        else
            echo -e "${RED}[错误] 启动失败，请检查服务配置${NC}"
        fi
    fi
}

stop_service() {
    echo -e "${YELLOW}[信息] 正在停止面板服务...${NC}"
    systemctl stop "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[成功] 面板服务已停止${NC}"
    else
        echo -e "${RED}[错误] 停止失败${NC}"
    fi
}

restart_service() {
    echo -e "${YELLOW}[信息] 正在重启面板服务...${NC}"
    systemctl restart "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[成功] 面板服务已重启${NC}"
    else
        systemctl daemon-reload 2>/dev/null
        systemctl restart "$SERVICE_NAME" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[成功] 面板服务已重启${NC}"
        else
            echo -e "${RED}[错误] 重启失败，请检查服务配置${NC}"
        fi
    fi
}

change_port() {
    local current_port
    current_port=$(get_current_port)
    echo -e "${YELLOW}当前面板端口：${BLUE}$current_port${NC}"
    echo ""
    read -p "请输入新的面板端口 (1-65535): " new_port
    if [[ ! "$new_port" =~ ^[0-9]+$ ]] || [ "$new_port" -lt 1 ] || [ "$new_port" -gt 65535 ]; then
        echo -e "${RED}[错误] 端口号无效，请输入 1-65535 之间的数字${NC}"
        return
    fi
    if [ "$new_port" = "$current_port" ]; then
        echo -e "${YELLOW}[信息] 端口未发生变化${NC}"
        return
    fi
    sed -i "s/^PORT=.*/PORT=$new_port/" "$CONFIG_FILE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[成功] 面板端口已修改为 $new_port${NC}"
        read -p "检测到端口已修改，是否立即重启服务生效？(y/n): " restart_confirm
        if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
            restart_service
        else
            echo -e "${YELLOW}[提示] 请手动重启服务以生效新的端口配置${NC}"
        fi
    else
        echo -e "${RED}[错误] 修改端口失败${NC}"
    fi
}

toggle_ssl() {
    local ssl_enabled
    ssl_enabled=$(grep -E "^SSL_ENABLED=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ "$ssl_enabled" = "True" ]; then
        echo -e "${YELLOW}[信息] 当前 SSL 状态：${GREEN}已开启${NC}"
        echo ""
        read -p "是否关闭 SSL？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            sed -i "s/^SSL_ENABLED=.*/SSL_ENABLED=False/" "$CONFIG_FILE"
            echo -e "${GREEN}[成功] SSL 已关闭${NC}"
            read -p "是否立即重启服务生效？(y/n): " restart_confirm
            if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
                restart_service
            fi
        fi
    else
        echo -e "${YELLOW}[信息] 当前 SSL 状态：${RED}已关闭${NC}"
        echo ""
        if [ ! -f "$BASE_DIR/backend/data/ssl/ssl.crt" ] || [ ! -f "$BASE_DIR/backend/data/ssl/ssl.key" ]; then
            echo -e "${YELLOW}[警告] 未检测到 SSL 证书文件${NC}"
            local ssl_cert_path
            ssl_cert_path=$(grep -E "^SSL_CERT_PATH=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
            local ssl_key_path
            ssl_key_path=$(grep -E "^SSL_KEY_PATH=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
            echo -e "  SSL_CERT_PATH: ${BLUE}${ssl_cert_path:-./data/ssl/ssl.crt}${NC}"
            echo -e "  SSL_KEY_PATH:  ${BLUE}${ssl_key_path:-./data/ssl/ssl.key}${NC}"
        fi
        echo ""
        read -p "是否开启 SSL？(y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            sed -i "s/^SSL_ENABLED=.*/SSL_ENABLED=True/" "$CONFIG_FILE"
            echo -e "${GREEN}[成功] SSL 已开启${NC}"
            read -p "是否立即重启服务生效？(y/n): " restart_confirm
            if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
                restart_service
            fi
        fi
    fi
}

get_security_entrance() {
    local entrance
    entrance=$(grep -E "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$entrance" ]; then
        echo -e "${YELLOW}[未设置]${NC}"
    else
        echo -e "${BLUE}$entrance${NC}"
    fi
}

change_security_entrance() {
    local current_entrance
    current_entrance=$(grep -E "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$current_entrance" ]; then
        current_entrance="（未设置）"
    fi
    echo -e "${YELLOW}当前安全入口：${BLUE}$current_entrance${NC}"
    echo ""
    echo "请选择操作："
    echo "  1) 输入自定义入口"
    echo "  2) 自动生成随机入口"
    echo "  3) 清除入口（禁用安全入口功能）"
    echo "  0) 取消"
    echo ""
    read -p "请选择 [0-3]: " entrance_choice
    case $entrance_choice in
        1)
            echo ""
            read -p "请输入新的安全入口（5-16位字母数字，不含特殊字符）: " new_entrance
            if [ -z "$new_entrance" ]; then
                echo -e "${RED}[错误] 入口不能为空${NC}"
                return
            fi
            if ! [[ "$new_entrance" =~ ^[a-zA-Z0-9]{5,16}$ ]]; then
                echo -e "${RED}[错误] 入口必须是 5-16 位字母数字组合${NC}"
                return
            fi
            if grep -q "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null; then
                sed -i "s/^SECURITY_ENTRANCE=.*/SECURITY_ENTRANCE=$new_entrance/" "$CONFIG_FILE"
            else
                echo "SECURITY_ENTRANCE=$new_entrance" >> "$CONFIG_FILE"
            fi
            echo -e "${GREEN}[成功] 安全入口已修改为 ${BLUE}$new_entrance${NC}"
            ;;
        2)
            local random_entrance
            random_entrance=$(tr -dc 'a-zA-Z0-9' < /dev/urandom 2>/dev/null | fold -w 12 | head -n 1)
            if [ -z "$random_entrance" ]; then
                random_entrance=$(date +%s | md5sum | head -c 12)
            fi
            if grep -q "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null; then
                sed -i "s/^SECURITY_ENTRANCE=.*/SECURITY_ENTRANCE=$random_entrance/" "$CONFIG_FILE"
            else
                echo "SECURITY_ENTRANCE=$random_entrance" >> "$CONFIG_FILE"
            fi
            echo -e "${GREEN}[成功] 已生成随机入口：${BLUE}$random_entrance${NC}"
            ;;
        3)
            echo ""
            read -p "确认清除安全入口？（面板将恢复直接访问）(y/n): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                if grep -q "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null; then
                    sed -i "s/^SECURITY_ENTRANCE=.*/SECURITY_ENTRANCE=/" "$CONFIG_FILE"
                fi
                echo -e "${GREEN}[成功] 安全入口已清除${NC}"
            else
                echo -e "${YELLOW}[信息] 已取消${NC}"
            fi
            ;;
        0)
            echo -e "${YELLOW}[信息] 已取消${NC}"
            ;;
        *)
            echo -e "${RED}[错误] 无效的选项${NC}"
            ;;
    esac

    if [ "$entrance_choice" != "0" ]; then
        read -p "是否立即重启服务生效？(y/n): " restart_confirm
        if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
            restart_service
        else
            echo -e "${YELLOW}[提示] 请手动重启服务以生效新的入口配置${NC}"
        fi
    fi
}

change_admin_password() {
    SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
    if [ -f "$SCRIPT_DIR/password.sh" ]; then
        bash "$SCRIPT_DIR/password.sh"
    else
        echo -e "${RED}[错误] 未找到 password.sh 脚本${NC}"
    fi
}

uninstall_panel() {
    echo -e "${YELLOW}==============================${NC}"
    echo -e "${YELLOW}  卸载 BlackPotBPanel 面板${NC}"
    echo -e "${YELLOW}==============================${NC}"
    echo ""
    echo -e "${RED}[警告] 此操作将停止并卸载面板服务${NC}"
    echo ""
    read -p "是否确认卸载面板？(y/n): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}[信息] 已取消卸载${NC}"
        return
    fi

    echo ""
    echo -e "${YELLOW}[信息] 正在停止面板服务...${NC}"
    systemctl stop "$SERVICE_NAME" 2>/dev/null
    systemctl disable "$SERVICE_NAME" 2>/dev/null

    echo -e "${YELLOW}[信息] 正在删除 systemd 服务文件...${NC}"
    rm -f /etc/systemd/system/Blackpotbpanel.service
    rm -f /etc/systemd/system/blackpotbpanel.service
    systemctl daemon-reload 2>/dev/null

    echo -e "${YELLOW}[信息] 正在删除软链接...${NC}"
    rm -f /usr/local/bin/bpctl

    echo ""
    echo -e "${GREEN}[成功] 面板服务已停止并移除${NC}"
    echo ""
    echo -e "${YELLOW}是否删除面板安装目录 ${BLUE}$BASE_DIR${YELLOW}？${NC}"
    echo -e "  ${YELLOW}注意：${NC}这将永久删除所有面板数据"
    read -p "确认删除？(y/n): " rm_confirm
    if [ "$rm_confirm" = "y" ] || [ "$rm_confirm" = "Y" ]; then
        echo -e "${YELLOW}[信息] 正在删除安装目录...${NC}"
        rm -rf "$BASE_DIR"
        echo -e "${GREEN}[成功] 安装目录已删除${NC}"
        echo -e "${GREEN}面板已完全卸载${NC}"
        exit 0
    else
        echo -e "${YELLOW}[提示] 安装目录已保留: $BASE_DIR${NC}"
        echo -e "${YELLOW}[提示] 如需重新安装面板，请保留安装目录${NC}"
        echo -e "${GREEN}面板已卸载（数据已保留）${NC}"
    fi
}

main() {
    check_root
    while true; do
        print_banner
        print_menu
        read -p "请输入选项 [0-8]: " choice
        echo ""
        case $choice in
            1)
                start_service
                ;;
            2)
                stop_service
                ;;
            3)
                restart_service
                ;;
            4)
                change_port
                ;;
            5)
                toggle_ssl
                ;;
            6)
                change_admin_password
                ;;
            7)
                change_security_entrance
                ;;
            8)
                uninstall_panel
                ;;
            0)
                echo -e "${GREEN}感谢使用 BlackPotBPanel 面板管理工具${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}[错误] 无效的选项，请重新选择${NC}"
                ;;
        esac
        if [ "$choice" != "0" ]; then
            echo ""
            read -p "按 Enter 键继续..."
        fi
    done
}

main
