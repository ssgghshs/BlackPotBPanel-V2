#!/bin/bash

set -e

BASE_DIR="/opt/blackpotbpanel-v2"
BACKEND_DIR="$BASE_DIR/backend"
VENV_DIR="$BASE_DIR/venv"
SERVER_DIR="$BASE_DIR/server"
CONFIG_FILE="$BASE_DIR/setting.conf"
SERVICE_FILE="/etc/systemd/system/Blackpotbpanel.service"
SERVICE_NAME="Blackpotbpanel"
GIT_REPO_URL="https://gitee.com/ssgghshs/blackpotbpanel-v2.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() {
    echo ""
    echo -e "${BLUE}[$(printf '%02d' $1)/11]${NC} $2"
    echo -e "${BLUE}------------------------------------------------------------${NC}"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root"
        echo "   sudo bash install2.sh"
        exit 1
    fi
}

# ==================== 0. User Confirmation ====================
step_confirm() {
    echo ""
    echo -e "${CYAN}================================================================"
    echo "           BlackPotBPanel V2 Installer"
    echo "=      __    __           __               __  __              ="
    echo "=     / /_  / /___ ______/ /______  ____  / /_/ /_  ____       ="
    echo "=    / __ \/ / __ \`/ ___/ //_/ __ \/ __ \/ __/ __ \/ __ \\    ="
    echo "=   / /_/ / / /_/ / /__/ ,< / /_/ / /_/ / /_/ /_/ / /_/ /      ="
    echo "=  /_.___/_/\__,_/\___/_/|_/ .___/\____/\__/_.___/ .___/       ="
    echo "=                       /_/                   /_/              ="
    echo "================================================================"
    echo -e "${NC}"
    echo -e "  Install path: ${YELLOW}$BASE_DIR${NC}"
    echo ""
    echo -ne "Install to this path? ${YELLOW}[y/n]${NC} "
    read -r choice
    case "$choice" in
        y|Y) echo "" ;;
        n|N) log_info "Installation cancelled"; exit 0 ;;
        *) log_error "Invalid input, please enter y or n"; exit 1 ;;
    esac

    echo -ne "Select panel language (1: 中文, 2: English, 3: 日本語, 4: 한국어) ${YELLOW}[default 2]${NC}: "
    read -r lang_choice
    case "$lang_choice" in
        1|zh|CN|zh-CN) CFG_LANGUAGE="zh-CN" ;;
        3|ja|JP|ja-JP) CFG_LANGUAGE="ja-JP" ;;
        4|ko|KR|ko-KR) CFG_LANGUAGE="ko-KR" ;;
        *) CFG_LANGUAGE="en-US" ;;
    esac
    log_info "Panel language: $CFG_LANGUAGE"

    echo -ne "Set panel port ${YELLOW}[default 8000]${NC}: "
    read -r port_input
    if [ -n "$port_input" ]; then
        if [[ "$port_input" =~ ^[0-9]+$ ]] && [ "$port_input" -ge 1 ] && [ "$port_input" -le 65535 ]; then
            CFG_PORT="$port_input"
        else
            log_error "Invalid port, please enter a number between 1-65535"
            exit 1
        fi
    else
        CFG_PORT=8000
    fi
    log_info "Panel port: $CFG_PORT"

    echo -ne "Enable HTTPS? ${YELLOW}[y/n, default n]${NC}: "
    read -r ssl_input
    case "$ssl_input" in
        y|Y) CFG_SSL="True" ;;
        *) CFG_SSL="False" ;;
    esac
    log_info "HTTPS: $([ "$CFG_SSL" = "True" ] && echo 'enabled' || echo 'disabled')"
    echo ""
    log_info "Starting installation..."
}

# ==================== 1. System Check ====================
step_check_system() {
    log_step 1 "Checking system environment"

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "Unsupported operating system"
        exit 1
    fi
    log_info "Operating system: $OS_NAME $OS_VERSION"

    case "$OS_NAME" in
        ubuntu|debian)
            PKG_MANAGER="apt-get"
            PKG_INSTALL="apt-get install -y"
            PYTHON_PKG="python3 python3-pip python3-venv python3-dev"
            DEV_PKGS="build-essential libssl-dev libbz2-dev libffi-dev zlib1g-dev libreadline-dev libsqlite3-dev tar ipset ufw"
            apt-get update -y
            ;;
        centos|rhel|rocky|almalinux)
            PKG_MANAGER="dnf"
            PKG_INSTALL="dnf install -y"
            PYTHON_PKG="python3 python3-pip python3-devel"
            DEV_PKGS="gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel dejavu-sans-fonts tar ipset"
            ;;
        *)
            log_error "Unsupported OS: $OS_NAME"
            exit 1
            ;;
    esac

    $PKG_INSTALL $DEV_PKGS $PYTHON_PKG curl wget git

    if command -v python3 &>/dev/null; then
        py_version=$(python3 --version 2>&1 | awk '{print $2}')
        py_major=$(echo "$py_version" | cut -d. -f1)
        py_minor=$(echo "$py_version" | cut -d. -f2)
        if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
            log_warn "Python version ($py_version) is below 3.10"
            echo ""
            echo -ne "Compile and install Python 3.10 to /opt/python3.10? ${YELLOW}[y/n]${NC}: "
            read -r py_choice
            case "$py_choice" in
                y|Y)
                    log_info "Compiling Python 3.10 from source..."
                    $PKG_INSTALL $DEV_PKGS wget
                    cd /opt
                    wget -q https://www.python.org/ftp/python/3.10.10/Python-3.10.10.tgz
                    tar -xzf Python-3.10.10.tgz
                    cd Python-3.10.10
                    ./configure --prefix=/opt/python3.10
                    make -j"$(nproc)"
                    make altinstall
                    cd /
                    rm -rf /opt/Python-3.10.10 /opt/Python-3.10.10.tgz
                    PYTHON_CMD="/opt/python3.10/bin/python3.10"
                    VENV_DIR="$BASE_DIR/venv"
                    log_info "Python 3.10 compiled and installed"
                    ;;
                n|N)
                    log_error "Installation cancelled, Python 3.10+ is required"
                    exit 1
                    ;;
                *)
                    log_error "Invalid input"
                    exit 1
                    ;;
            esac
        else
            PYTHON_CMD="python3"
            log_info "Python version: $py_version"
        fi
    else
        log_error "Python3 not found"
        exit 1
    fi

    mem_total=$(free -m | awk '/^Mem:/{print $2}')
    log_info "Memory: ${mem_total}MB"
    if [ "$mem_total" -lt 512 ]; then
        log_warn "Memory below 512MB, panel may be unstable"
    fi
}

# ==================== 2. Clone Repository ====================
step_clone_repo() {
    log_step 2 "Cloning repository"

    if [ -d "$BASE_DIR" ]; then
        log_info "Directory $BASE_DIR already exists"
        if [ -f "$BACKEND_DIR/main.py" ]; then
            log_info "Project already exists, skipping clone"
            return
        fi
        log_warn "Directory exists but project is incomplete, re-cloning..."
        rm -rf "$BASE_DIR"
    fi

    if ! command -v git &>/dev/null; then
        $PKG_INSTALL git
    fi

    log_info "Cloning repository: $GIT_REPO_URL"
    git clone --depth 1 "$GIT_REPO_URL" "$BASE_DIR"
    log_info "Repository cloned"
}

# ==================== 3. Create Directory Structure ====================
step_create_dirs() {
    log_step 3 "Creating directory structure"

    local dirs=(
        "$SERVER_DIR/waf/sites/www"
        "$SERVER_DIR/waf/sites/conf"
        "$SERVER_DIR/waf/sites/sitelogs"
        "$SERVER_DIR/waf/ssl"
        "$SERVER_DIR/waf/logs"
        "$SERVER_DIR/waf/data"
        "$SERVER_DIR/crontab/scripts"
        "$SERVER_DIR/crontab/logs"
        "$SERVER_DIR/backup/database"
        "$SERVER_DIR/.recycle_bp"
        "$SERVER_DIR/composeapp/compose-localhost"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Creating directory: $dir"
        fi
    done
}

# ==================== 4. Create Virtual Environment ====================
step_create_venv() {
    log_step 4 "Creating Python virtual environment"

    if [ -d "$VENV_DIR" ]; then
        log_info "Virtual environment already exists, skipping"
    else
        log_info "Creating virtual environment: $VENV_DIR"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi

    log_info "Upgrading pip..."
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
    "$VENV_DIR/bin/pip" config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
}

# ==================== 5. Install Dependencies ====================
step_install_deps() {
    log_step 5 "Installing Python dependencies"

    if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
        log_error "$BACKEND_DIR/requirements.txt not found"
        exit 1
    fi

    log_info "Installing dependencies..."
    "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" --default-timeout=100
    log_info "Dependencies installed"
}

# ==================== 6. Configure Panel Settings ====================
step_configure() {
    log_step 6 "Configuring panel settings"

    secret_key=$($PYTHON_CMD -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32 2>/dev/null || echo "blackpotbpanel-$(date +%s)-$$")

    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
    fi

    cat > "$CONFIG_FILE" <<EOF
# Application Settings
APP_NAME=BlackPotBPanel
DEBUG=False
VERSION=2.0.1

# JWT Settings
SECRET_KEY=$secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Timezone Settings
TIMEZONE=Asia/Shanghai

# API Documentation
ENABLE_DOCS=True

# General Settings
LANGUAGE=$CFG_LANGUAGE
THEME=dark
LOGIN_NOTIFY=True
RECYCLE=True

# Server Settings
HOST=0.0.0.0
PORT=$CFG_PORT

# SSL Settings
SSL_ENABLED=$CFG_SSL
EOF
    log_info "Configuration file created/updated"

    if [ -f "$BACKEND_DIR/app/__init__.py.prod" ] && [ ! -f "$BACKEND_DIR/app/__init__.py" ]; then
        cp "$BACKEND_DIR/app/__init__.py.prod" "$BACKEND_DIR/app/__init__.py"
        log_info "__init__.py configured"
    fi
}

# ==================== 7. Configure Systemd Service ====================
step_systemd() {
    log_step 7 "Configuring systemd service"

    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=BlackPotBPanel Backend Service
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Systemd service file created"
}

# ==================== 8. Deploy CLI Tool ====================
step_deploy_cli() {
    log_step 8 "Deploying CLI tool"

    local bpctl_src="$BASE_DIR/cli/bpctl"
    local bpctl_dst="/usr/local/bin/bpctl"

    if [ -f "$bpctl_src" ]; then
        if [ -L "$bpctl_dst" ] || [ -f "$bpctl_dst" ]; then
            log_info "bpctl already deployed, updating link..."
            rm -f "$bpctl_dst"
        fi
        chmod +x "$bpctl_src"
        ln -sf "$bpctl_src" "$bpctl_dst"
        log_info "bpctl deployed to /usr/local/bin/bpctl"
    else
        log_warn "$bpctl_src not found, skipping"
    fi
}

# ==================== 9. Configure Firewall ====================
step_firewall() {
    log_step 9 "Configuring firewall"

    log_info "Opening port: $CFG_PORT"

    if command -v firewall-cmd &>/dev/null; then
        firewall-cmd --zone=public --add-port="${CFG_PORT}/tcp" --permanent 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    elif command -v ufw &>/dev/null; then
        ufw allow "${CFG_PORT}/tcp" 2>/dev/null || true
    else
        log_warn "Please manually open port $CFG_PORT"
    fi
}

# ==================== 10. Start Panel Service ====================
step_start() {
    log_step 10 "Starting panel service"

    systemctl enable "$SERVICE_NAME" 2>/dev/null || true
    systemctl restart "$SERVICE_NAME" 2>/dev/null || {
        log_warn "systemctl start failed, trying direct start..."
        cd "$BACKEND_DIR"
        nohup "$VENV_DIR/bin/python" main.py > /dev/null 2>&1 &
        log_info "Panel started (PID: $!)"
    }

    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "Panel service is running"
    elif pgrep -f "python main.py" > /dev/null; then
        log_info "Panel process is running"
    else
        log_warn "Panel is not running, please check logs and start manually"
    fi
}

# ==================== 11. Installation Complete ====================
step_done() {
    log_step 11 "Installation complete"

    ip_addr=$(ip -4 route get 1 2>/dev/null | grep -oP 'src \K[\d.]+' 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || curl -s --max-time 3 ifconfig.me 2>/dev/null || echo "")

    if [ "$CFG_SSL" = "True" ]; then
        proto="https"
        ssl_label="enabled"
    else
        proto="http"
        ssl_label="disabled"
    fi

    echo ""
    echo -e "${GREEN}================================================================"
    echo "           BlackPotBPanel V2 installed successfully!"
    echo "================================================================"
    echo -e "${NC}"
    if [ -n "$ip_addr" ]; then
        echo -e "  Panel URL:    ${CYAN}${proto}://${ip_addr}:${CFG_PORT}${NC}"
    fi
    echo -e "  Panel URL:    ${CYAN}${proto}://localhost:${CFG_PORT}${NC}"
    echo ""
    echo -e "  Username:     ${YELLOW}admin${NC}"
    echo -e "  Password:     ${YELLOW}admin@123${NC}"
    echo ""
    echo -e "  Install path: ${BLUE}$BASE_DIR${NC}"
    echo -e "  Virtual env:  ${BLUE}$VENV_DIR${NC}"
    echo -e "  HTTPS:        ${YELLOW}$ssl_label${NC}"
    echo ""
    echo -e "  ${YELLOW}Management:${NC}"
    echo -e "    bpctl"
    echo ""
    echo -e "  ${YELLOW}Please change the default password!${NC}"
    echo ""
    echo -e "${GREEN}==============================================================${NC}"
}

# ==================== Main ====================
main() {
    check_root

    echo ""
    log_info "Install path: $BASE_DIR"
    echo ""

    step_confirm
    step_check_system
    step_clone_repo
    step_create_dirs
    step_create_venv
    step_install_deps
    step_configure
    step_systemd
    step_deploy_cli
    step_firewall
    step_start
    step_done
}

main "$@"
