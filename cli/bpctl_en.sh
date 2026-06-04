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
    echo "=                         /_/                   /_/            ="
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
    local entrance_status
    entrance_status=$(get_security_entrance)
    local domain_binding_status
    domain_binding_status=$(get_domain_binding)
    local allow_ips_status
    allow_ips_status=$(get_allow_ips_status)
    local mfa_status
    mfa_status=$(get_mfa_status)

    echo -e "${YELLOW}Panel Status:${NC}"
    echo "----------------------------------------"
    echo -e "  Service:      $(get_service_status)"
    echo -e "  Port:         ${BLUE}$current_port${NC}"
    echo -e "  SSL:          $ssl_status"
    echo -e "  Entrance:     $entrance_status"
    echo -e "  Domain Bind:  $domain_binding_status"
    echo -e "  Allow IPs:    $allow_ips_status"
    echo -e "  MFA:          $mfa_status"
    echo -e "  Install Path: ${BLUE}$BASE_DIR${NC}"
    echo "----------------------------------------"
    echo ""
    echo -e "${YELLOW}Select an option:${NC}"
    echo ""
    echo "  0) Exit"    
    echo "  1) Start panel service"
    echo "  2) Stop panel service"
    echo "  3) Restart panel service"
    echo "  4) View service status"
    echo "  5) Change panel port"
    echo "  6) Toggle panel SSL"
    echo "  7) Change admin password"
    echo "  8) Change security entrance"
    echo "  9) Bind domain name"
    echo "  10) Toggle allow IPs"
    echo "  11) Toggle MFA"
    echo "  12) Uninstall panel"
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

show_service_status() {
    local port
    port=$(get_current_port)
    local state
    state=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null)
    local enabled
    enabled=$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null)

    echo -e "${YELLOW}--- Basic Status ---${NC}"
    echo -e "  Service Name:  ${BLUE}$SERVICE_NAME${NC}"
    echo -e "  Active State:  $(get_service_status)"
    echo -e "  Enabled:       ${GREEN}$enabled${NC}"
    echo ""
    echo -e "${YELLOW}--- Process Details ---${NC}"

    local pid
    pid=$(systemctl show -p MainPID "$SERVICE_NAME" 2>/dev/null | cut -d= -f2)
    if [ -n "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        echo -e "  PID:           ${BLUE}$pid${NC}"

        local cpu_mem
        cpu_mem=$(ps -p "$pid" -o %cpu,%mem,etime --no-headers 2>/dev/null)
        local cpu
        cpu=$(echo "$cpu_mem" | awk '{print $1}')
        local mem
        mem=$(echo "$cpu_mem" | awk '{print $2}')
        local uptime
        uptime=$(echo "$cpu_mem" | awk '{print $3}')
        echo -e "  CPU Usage:     ${BLUE}${cpu:-N/A}%${NC}"
        echo -e "  Memory Usage:  ${BLUE}${mem:-N/A}%${NC}"
        echo -e "  Process Uptime:${BLUE}${uptime:-N/A}${NC}"

        local rss
        rss=$(ps -p "$pid" -o rss --no-headers 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
        echo -e "  Memory (RSS):  ${BLUE}${rss:-N/A}${NC}"
    else
        echo -e "  PID:           ${RED}[Not Running]${NC}"
    fi

    echo ""
    echo -e "${YELLOW}--- Port Listening ---${NC}"
    if [ -n "$port" ]; then
        if ss -tlnp 2>/dev/null | grep -q ":$port "; then
            local pid_info
            pid_info=$(ss -tlnp 2>/dev/null | grep ":$port " | head -1)
            echo -e "  Port $port:    ${GREEN}[Listening]${NC}"
            echo -e "  Details:       ${BLUE}$pid_info${NC}"
        else
            echo -e "  Port $port:    ${RED}[Not Listening]${NC}"
        fi
    fi

    echo ""
    echo -e "${YELLOW}--- Recent Logs (last 5 lines) ---${NC}"
    journalctl -u "$SERVICE_NAME" --no-pager -n 5 2>/dev/null | tail -5 || echo -e "${YELLOW}[No log available]${NC}"

    echo ""
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

get_security_entrance() {
    local entrance
    entrance=$(grep -E "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$entrance" ]; then
        echo -e "${YELLOW}[Not set]${NC}"
    else
        echo -e "${BLUE}$entrance${NC}"
    fi
}

get_domain_binding() {
    local domain
    domain=$(grep -E "^DOMAIN_BINDING=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$domain" ]; then
        echo -e "${YELLOW}[Not bound]${NC}"
    else
        echo -e "${BLUE}$domain${NC}"
    fi
}

get_allow_ips_status() {
    local allow_file="$BASE_DIR/backend/data/allow_ips.json"
    local ips
    ips=""
    if [ -f "$allow_file" ]; then
        ips=$(python3 -c "import json; d=json.load(open('$allow_file')); print(d.get('ALLOW_IPS','') or '')" 2>/dev/null)
    fi
    if [ -z "$ips" ]; then
        echo -e "${YELLOW}[Disabled]${NC}"
    else
        echo -e "${GREEN}[Enabled]${NC} ${BLUE}$ips${NC}"
    fi
}

get_mfa_status() {
    local mfa_file="$BASE_DIR/backend/data/mfa.json"
    local enabled
    enabled=""
    if [ -f "$mfa_file" ]; then
        enabled=$(python3 -c "import json; d=json.load(open('$mfa_file')); print('true' if d.get('MFA_ENABLED') and d.get('MFA_SECRET') else 'false')" 2>/dev/null)
    fi
    if [ "$enabled" = "true" ]; then
        echo -e "${GREEN}[Enabled]${NC}"
    else
        echo -e "${YELLOW}[Disabled]${NC}"
    fi
}

change_security_entrance() {
    local current_entrance
    current_entrance=$(grep -E "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$current_entrance" ]; then
        current_entrance="(Not set)"
    fi
    echo -e "${YELLOW}Current security entrance: ${BLUE}$current_entrance${NC}"
    echo ""
    echo "Select an option:"
    echo "  1) Enter custom entrance"
    echo "  2) Generate random entrance"
    echo "  3) Clear entrance (disable security entrance)"
    echo "  0) Cancel"
    echo ""
    read -p "Choose [0-3]: " entrance_choice
    case $entrance_choice in
        1)
            echo ""
            read -p "Enter new security entrance (5-16 alphanumeric chars): " new_entrance
            if [ -z "$new_entrance" ]; then
                echo -e "${RED}[Error] Entrance cannot be empty${NC}"
                return
            fi
            if ! [[ "$new_entrance" =~ ^[a-zA-Z0-9]{5,16}$ ]]; then
                echo -e "${RED}[Error] Entrance must be 5-16 alphanumeric characters${NC}"
                return
            fi
            if grep -q "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null; then
                sed -i "s/^SECURITY_ENTRANCE=.*/SECURITY_ENTRANCE=$new_entrance/" "$CONFIG_FILE"
            else
                echo "SECURITY_ENTRANCE=$new_entrance" >> "$CONFIG_FILE"
            fi
            echo -e "${GREEN}[OK] Security entrance changed to ${BLUE}$new_entrance${NC}"
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
            echo -e "${GREEN}[OK] Random entrance generated: ${BLUE}$random_entrance${NC}"
            ;;
        3)
            echo ""
            read -p "Confirm clearing security entrance? (panel will be directly accessible) (y/n): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                if grep -q "^SECURITY_ENTRANCE=" "$CONFIG_FILE" 2>/dev/null; then
                    sed -i "s/^SECURITY_ENTRANCE=.*/SECURITY_ENTRANCE=/" "$CONFIG_FILE"
                fi
                echo -e "${GREEN}[OK] Security entrance cleared${NC}"
            else
                echo -e "${YELLOW}[Info] Cancelled${NC}"
            fi
            ;;
        0)
            echo -e "${YELLOW}[Info] Cancelled${NC}"
            ;;
        *)
            echo -e "${RED}[Error] Invalid option${NC}"
            ;;
    esac

    if [ "$entrance_choice" != "0" ]; then
        read -p "Restart service now to apply? (y/n): " restart_confirm
        if [ "$restart_confirm" = "y" ] || [ "$restart_confirm" = "Y" ]; then
            restart_service
        else
            echo -e "${YELLOW}[Hint] Please restart the service manually to apply the new entrance${NC}"
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

change_domain_binding() {
    local current_domain
    current_domain=$(grep -E "^DOMAIN_BINDING=" "$CONFIG_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -z "$current_domain" ]; then
        echo -e "${YELLOW}Current bound domain: ${RED}[Not bound]${NC}"
    else
        echo -e "${YELLOW}Current bound domain: ${BLUE}$current_domain${NC}"
    fi
    echo ""
    echo -e "${YELLOW}Domain Binding:${NC}"
    echo "  - Only this domain will be allowed to access the panel, others get 403"
    echo "  - Takes effect immediately, no restart required"
    echo ""
    echo "Select an option:"
    echo "  1) Set / change bound domain"
    echo "  2) Clear binding (allow any domain)"
    echo "  0) Cancel"
    echo ""
    read -p "Choose [0-2]: " domain_choice
    case $domain_choice in
        1)
            echo ""
            read -p "Enter domain to bind (e.g. panel.example.com): " new_domain
            if [ -z "$new_domain" ]; then
                echo -e "${RED}[Error] Domain cannot be empty${NC}"
                return
            fi
            if ! [[ "$new_domain" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*\.)+[a-zA-Z]{2,}$ ]]; then
                echo -e "${RED}[Error] Invalid domain format. Use a valid domain like panel.example.com${NC}"
                return
            fi
            if grep -q "^DOMAIN_BINDING=" "$CONFIG_FILE" 2>/dev/null; then
                sed -i "s/^DOMAIN_BINDING=.*/DOMAIN_BINDING=$new_domain/" "$CONFIG_FILE"
            else
                echo "DOMAIN_BINDING=$new_domain" >> "$CONFIG_FILE"
            fi
            echo -e "${GREEN}[OK] Domain binding set to ${BLUE}$new_domain${NC}"
            echo -e "${YELLOW}[Hint] Already active, no restart needed${NC}"
            ;;
        2)
            echo ""
            read -p "Confirm clearing domain binding? (any domain will be allowed) (y/n): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                if grep -q "^DOMAIN_BINDING=" "$CONFIG_FILE" 2>/dev/null; then
                    sed -i "s/^DOMAIN_BINDING=.*/DOMAIN_BINDING=/" "$CONFIG_FILE"
                fi
                echo -e "${GREEN}[OK] Domain binding cleared${NC}"
                echo -e "${YELLOW}[Hint] Already active, no restart needed${NC}"
            else
                echo -e "${YELLOW}[Info] Cancelled${NC}"
            fi
            ;;
        0)
            echo -e "${YELLOW}[Info] Cancelled${NC}"
            ;;
        *)
            echo -e "${RED}[Error] Invalid option${NC}"
            ;;
    esac
}

toggle_allow_ips() {
    local allow_file="$BASE_DIR/backend/data/allow_ips.json"
    local current_ips
    current_ips=""
    if [ -f "$allow_file" ]; then
        current_ips=$(python3 -c "import json; d=json.load(open('$allow_file')); print(d.get('ALLOW_IPS','') or '')" 2>/dev/null)
    fi

    if [ -n "$current_ips" ]; then
        echo -e "${YELLOW}Current allowed IPs: ${BLUE}$current_ips${NC}"
        echo ""
        read -p "Disable IP access restriction? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo '{"ALLOW_IPS":""}' > "$allow_file"
            echo -e "${GREEN}[OK] IP access restriction disabled${NC}"
            echo -e "${YELLOW}[Hint] Already active, no restart needed${NC}"
        fi
    else
        echo -e "${YELLOW}Current allowed IPs: ${RED}[Disabled]${NC}"
        echo ""
        echo -e "Enter the IP addresses to allow (comma separated, CIDR supported):"
        read -p "e.g. 192.168.1.100 or 10.0.0.0/24,192.168.1.0/24: " new_ips
        if [ -n "$new_ips" ]; then
            echo "{\"ALLOW_IPS\":\"$new_ips\"}" > "$allow_file"
            echo -e "${GREEN}[OK] IPs allowed: ${BLUE}$new_ips${NC}"
            echo -e "${YELLOW}[Hint] Already active, no restart needed${NC}"
        else
            echo -e "${YELLOW}[Info] Cancelled${NC}"
        fi
    fi
}

toggle_mfa() {
    local mfa_file="$BASE_DIR/backend/data/mfa.json"
    local enabled
    enabled=""
    if [ -f "$mfa_file" ]; then
        enabled=$(python3 -c "import json; d=json.load(open('$mfa_file')); print('true' if d.get('MFA_ENABLED') and d.get('MFA_SECRET') else 'false')" 2>/dev/null)
    fi

    if [ "$enabled" = "true" ]; then
        echo -e "${YELLOW}Current MFA status: ${GREEN}[Enabled]${NC}"
        echo ""
        read -p "Disable MFA? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo '{"MFA_ENABLED":false,"MFA_SECRET":"","MFA_INTERVAL":30}' > "$mfa_file"
            echo -e "${GREEN}[OK] MFA disabled${NC}"
            echo -e "${YELLOW}[Hint] Takes effect on next login${NC}"
        fi
    else
        echo -e "${YELLOW}MFA is not enabled, nothing to disable${NC}"
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
        read -p "Please select an option [0-12]: " choice
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
                show_service_status
                ;;
            5)
                change_port
                ;;
            6)
                toggle_ssl
                ;;
            7)
                change_admin_password
                ;;
            8)
                change_security_entrance
                ;;
            9)
                change_domain_binding
                ;;
            10)
                toggle_allow_ips
                ;;
            11)
                toggle_mfa
                ;;
            12)
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
