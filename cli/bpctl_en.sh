#!/bin/bash

# BlackPotBPanel Panel Management Tool
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
        echo -e "${RED}[Error] Please run this script as root${NC}"
        exit 1
    fi
}

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "================================================================"
    echo "=           BlackPotBPanel Panel Management Tool v2.0          ="
    echo "=      __    __           __               __  __              ="
    echo "=     / /_  / /___ ______/ /______  ____  / /_/ /_  ____       ="
    echo "=    / __ \/ / __ \`/ ___/ //_/ __ \/ __ \/ __/ __ \/ __ \\    ="
    echo "=   / /_/ / / /_/ / /__/ ,< / /_/ / /_/ / /_/ /_/ / /_/ /      ="
    echo "=  /_.___/_/\__,_/\___/_/|_/ .___/\____/\__/_.___/ .___/       ="
    echo "=                       /_/                   /_/              ="
    echo "================================================================"
    echo -e "${NC}"
}

get_service_status() {
    local state
    state=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null)
    case "$state" in
        active)
            echo -e "${GREEN}[Running]${NC}"
            ;;
        activating)
            echo -e "${YELLOW}[Starting]${NC}"
            ;;
        inactive)
            echo -e "${RED}[Stopped]${NC}"
            ;;
        *)
            echo -e "${YELLOW}[Not Installed]${NC}"
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
        echo -e "${GREEN}[Enabled]${NC}"
    else
        echo -e "${RED}[Disabled]${NC}"
    fi
}

print_menu() {
    local current_port
    current_port=$(get_current_port)
    local service_status
    service_status=$(get_service_status)
    local ssl_status
    ssl_status=$(get_ssl_status)

    echo -e "${YELLOW}Panel Status:${NC}"
    echo "----------------------------------------"
    echo -e "  Service:      $(get_service_status)"
    echo -e "  Port:         ${BLUE}$current_port${NC}"
    echo -e "  SSL:          $ssl_status"
    echo -e "  Install Path: ${BLUE}$BASE_DIR${NC}"
    echo "----------------------------------------"
    echo ""
    echo -e "${YELLOW}Select an option:${NC}"
    echo ""
    echo "  1) Start panel service"
    echo "  2) Stop panel service"
    echo "  3) Restart panel service"
    echo "  4) Change panel port"
    echo "  5) Toggle panel SSL"
    echo "  6) Change admin password"
    echo "  7) Uninstall panel"
    echo "  0) Exit"
    echo ""
}

start_service() {
    echo -e "${YELLOW}[Info] Starting panel service...${NC}"
    systemctl start "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Panel service started${NC}"
    else
        systemctl daemon-reload 2>/dev/null
        systemctl start "$SERVICE_NAME" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK] Panel service started${NC}"
        else
            echo -e "${RED}[Error] Failed to start, please check service configuration${NC}"
        fi
    fi
}

stop_service() {
    echo -e "${YELLOW}[Info] Stopping panel service...${NC}"
    systemctl stop "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Panel service stopped${NC}"
    else
        echo -e "${RED}[Error] Failed to stop${NC}"
    fi
}

restart_service() {
    echo -e "${YELLOW}[Info] Restarting panel service...${NC}"
    systemctl restart "$SERVICE_NAME" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Panel service restarted${NC}"
    else
        systemctl daemon-reload 2>/dev/null
        systemctl restart "$SERVICE_NAME" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}[OK] Panel service restarted${NC}"
        else
            echo -e "${RED}[Error] Failed to restart, please check service configuration${NC}"
        fi
    fi
}

change_port() {
    local current_port
    current_port=$(get_current_port)
    echo -e "${YELLOW}Current panel port: ${BLUE}$current_port${NC}"
    echo ""
    read -p "Enter new panel port (1-65535): " new_port
    if [[ ! "$new_port" =~ ^[0-9]+$ ]] || [ "$new_port" -lt 1 ] || [ "$new_port" -gt 65535 ]; then
        echo -e "${RED}[Error] Invalid port number, please enter a number between 1-65535${NC}"
        return
    fi
    if [ "$new_port" = "$current_port" ]; then
        echo -e "${YELLOW}[Info] Port unchanged${NC}"
        return
    fi
    sed -i "s/^PORT=.*/PORT=$new_port/" "$CONFIG_FILE"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Panel port changed to $new_port${NC}"
        read -p "Port has been changed. Restart service now to apply? (y/n): " restart_confirm
        if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
            restart_service
        else
            echo -e "${YELLOW}[Hint] Please restart the service manually to apply the new port${NC}"
        fi
    else
        echo -e "${RED}[Error] Failed to change port${NC}"
    fi
}

toggle_ssl() {
    local ssl_enabled
    ssl_enabled=$(grep -E "^SSL_ENABLED=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ "$ssl_enabled" = "True" ]; then
        echo -e "${YELLOW}[Info] Current SSL status: ${GREEN}Enabled${NC}"
        echo ""
        read -p "Do you want to disable SSL? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            sed -i "s/^SSL_ENABLED=.*/SSL_ENABLED=False/" "$CONFIG_FILE"
            echo -e "${GREEN}[OK] SSL has been disabled${NC}"
            read -p "Restart service now to apply? (y/n): " restart_confirm
            if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
                restart_service
            fi
        fi
    else
        echo -e "${YELLOW}[Info] Current SSL status: ${RED}Disabled${NC}"
        echo ""
        if [ ! -f "$BASE_DIR/backend/data/ssl/ssl.crt" ] || [ ! -f "$BASE_DIR/backend/data/ssl/ssl.key" ]; then
            echo -e "${YELLOW}[Warning] SSL certificate files not found${NC}"
            local ssl_cert_path
            ssl_cert_path=$(grep -E "^SSL_CERT_PATH=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
            local ssl_key_path
            ssl_key_path=$(grep -E "^SSL_KEY_PATH=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
            echo -e "  SSL_CERT_PATH: ${BLUE}${ssl_cert_path:-./data/ssl/ssl.crt}${NC}"
            echo -e "  SSL_KEY_PATH:  ${BLUE}${ssl_key_path:-./data/ssl/ssl.key}${NC}"
        fi
        echo ""
        read -p "Do you want to enable SSL? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            sed -i "s/^SSL_ENABLED=.*/SSL_ENABLED=True/" "$CONFIG_FILE"
            echo -e "${GREEN}[OK] SSL has been enabled${NC}"
            read -p "Restart service now to apply? (y/n): " restart_confirm
            if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
                restart_service
            fi
        fi
    fi
}

change_admin_password() {
    SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
    if [ -f "$SCRIPT_DIR/password.sh" ]; then
        bash "$SCRIPT_DIR/password.sh"
    else
        echo -e "${RED}[Error] password.sh not found${NC}"
    fi
}

uninstall_panel() {
    echo -e "${YELLOW}==============================${NC}"
    echo -e "${YELLOW}  Uninstall BlackPotBPanel${NC}"
    echo -e "${YELLOW}==============================${NC}"
    echo ""
    echo -e "${RED}[Warning] This will stop and remove the panel service${NC}"
    echo ""
    read -p "Are you sure you want to uninstall the panel? (y/n): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}[Info] Uninstall cancelled${NC}"
        return
    fi

    echo ""
    echo -e "${YELLOW}[Info] Stopping panel service...${NC}"
    systemctl stop "$SERVICE_NAME" 2>/dev/null
    systemctl disable "$SERVICE_NAME" 2>/dev/null

    echo -e "${YELLOW}[Info] Removing systemd service file...${NC}"
    rm -f /etc/systemd/system/Blackpotbpanel.service
    rm -f /etc/systemd/system/blackpotbpanel.service
    systemctl daemon-reload 2>/dev/null

    echo -e "${YELLOW}[Info] Removing symlink...${NC}"
    rm -f /usr/local/bin/bpctl

    echo ""
    echo -e "${GREEN}[OK] Panel service stopped and removed${NC}"
    echo ""
    echo -e "${YELLOW}Delete the installation directory ${BLUE}$BASE_DIR${YELLOW}?${NC}"
    echo -e "  ${YELLOW}Note:${NC} This will permanently delete all panel data"
    read -p "Confirm deletion? (y/n): " rm_confirm
    if [ "$rm_confirm" = "y" ] || [ "$rm_confirm" = "Y" ]; then
        echo -e "${YELLOW}[Info] Removing installation directory...${NC}"
        rm -rf "$BASE_DIR"
        echo -e "${GREEN}[OK] Installation directory deleted${NC}"
        echo -e "${GREEN}Panel has been completely uninstalled${NC}"
        exit 0
    else
        echo -e "${YELLOW}[Hint] Installation directory preserved: $BASE_DIR${NC}"
        echo -e "${YELLOW}[Hint] Keep the installation directory if you plan to reinstall${NC}"
        echo -e "${GREEN}Panel uninstalled (data preserved)${NC}"
    fi
}

main() {
    check_root
    while true; do
        print_banner
        print_menu
        read -p "Please select an option [0-7]: " choice
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
                uninstall_panel
                ;;
            0)
                echo -e "${GREEN}Thank you for using BlackPotBPanel Panel Management Tool${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}[Error] Invalid option, please try again${NC}"
                ;;
        esac
        if [ "$choice" != "0" ]; then
            echo ""
            read -p "Press Enter to continue..."
        fi
    done
}

main
