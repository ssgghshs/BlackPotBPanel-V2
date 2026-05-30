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
        log_error "请使用 root 用户运行此安装脚本"
        echo "   sudo bash install.sh"
        exit 1
    fi
}

# ==================== 0. 用户确认 ====================
step_confirm() {
    echo ""
    echo -e "${CYAN}================================================================"
    echo "           BlackPotBPanel V2 安装程序"
    echo "=      __    __           __               __  __              ="
    echo "=     / /_  / /___ ______/ /______  ____  / /_/ /_  ____       ="
    echo "=    / __ \/ / __ \`/ ___/ //_/ __ \/ __ \/ __/ __ \/ __ \\    ="
    echo "=   / /_/ / / /_/ / /__/ ,< / /_/ / /_/ / /_/ /_/ / /_/ /      ="
    echo "=  /_.___/_/\__,_/\___/_/|_/ .___/\____/\__/_.___/ .___/       ="
    echo "=                         /_/                   /_/            ="
    echo "================================================================"
    echo -e "${NC}"
    echo -e "  安装路径: ${YELLOW}$BASE_DIR${NC}"
    echo ""
    echo -ne "是否安装到该路径? ${YELLOW}[y/n]${NC} "
    read -r choice
    case "$choice" in
        y|Y) echo "" ;;
        n|N) log_info "已取消安装"; exit 0 ;;
        *) log_error "无效输入，请输入 y 或 n"; exit 1 ;;
    esac

    echo -ne "选择面板语言 (1: 中文, 2: English, 3: 日本語, 4: 한국어) ${YELLOW}[默认 1]${NC}: "
    read -r lang_choice
    case "$lang_choice" in
        2|en|EN|en-US) CFG_LANGUAGE="en-US" ;;
        3|ja|JP|ja-JP) CFG_LANGUAGE="ja-JP" ;;
        4|ko|KR|ko-KR) CFG_LANGUAGE="ko-KR" ;;
        *) CFG_LANGUAGE="zh-CN" ;;
    esac
    log_info "面板语言: $CFG_LANGUAGE"

    echo -ne "设置面板端口 ${YELLOW}[默认 8000]${NC}: "
    read -r port_input
    if [ -n "$port_input" ]; then
        if [[ "$port_input" =~ ^[0-9]+$ ]] && [ "$port_input" -ge 1 ] && [ "$port_input" -le 65535 ]; then
            CFG_PORT="$port_input"
        else
            log_error "端口无效，请输入 1-65535 之间的数字"
            exit 1
        fi
    else
        CFG_PORT=8000
    fi
    log_info "面板端口: $CFG_PORT"

    echo -ne "是否启用 HTTPS? ${YELLOW}[y/n, 默认 n]${NC}: "
    read -r ssl_input
    case "$ssl_input" in
        y|Y) CFG_SSL="True" ;;
        *) CFG_SSL="False" ;;
    esac
    log_info "HTTPS: $([ "$CFG_SSL" = "True" ] && echo '启用' || echo '禁用')"

    echo -ne "是否启用安全入口（隐藏面板登录页，增强安全性）? ${YELLOW}[y/n, 默认 y]${NC}: "
    read -r entrance_input
    case "$entrance_input" in
        n|N)
            CFG_ENTRANCE=""
            log_info "安全入口: 禁用"
            ;;
        *)
            CFG_ENTRANCE=$(tr -dc 'a-zA-Z0-9' < /dev/urandom 2>/dev/null | fold -w 12 | head -n 1)
            if [ -z "$CFG_ENTRANCE" ]; then
                CFG_ENTRANCE="bp$(date +%s | md5sum | head -c 10)"
            fi
            log_info "安全入口: ${YELLOW}$CFG_ENTRANCE${NC}"
            ;;
    esac

    echo ""
    log_info "开始安装..."
}

# ==================== 1. 检查系统环境 ====================
step_check_system() {
    log_step 1 "检查系统环境"

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "不支持的操作系统"
        exit 1
    fi
    log_info "操作系统: $OS_NAME $OS_VERSION"

    case "$OS_NAME" in
        ubuntu|debian)
            PKG_MANAGER="apt-get"
            PKG_INSTALL="apt-get install -y"
            PYTHON_PKG="python3 python3-pip python3-venv python3-dev"
            DEV_PKGS="build-essential libssl-dev libbz2-dev libffi-dev zlib1g-dev libreadline-dev libsqlite3-dev tar ipset ufw"
            apt-get update -y
            ;;
        centos|rhel|rocky|almalinux|openEuler|kylin|anolis)
            PKG_MANAGER="dnf"
            PKG_INSTALL="dnf install -y"
            PYTHON_PKG="python3 python3-pip python3-devel"
            DEV_PKGS="gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel dejavu-sans-fonts tar ipset"
            ;;
        *)
            log_error "不支持的操作系统: $OS_NAME"
            exit 1
            ;;
    esac

    $PKG_INSTALL $DEV_PKGS $PYTHON_PKG curl wget git

    if command -v python3 &>/dev/null; then
        py_version=$(python3 --version 2>&1 | awk '{print $2}')
        py_major=$(echo "$py_version" | cut -d. -f1)
        py_minor=$(echo "$py_version" | cut -d. -f2)
        if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
            log_warn "Python 版本 ($py_version) 低于 3.10"
            echo ""
            echo -ne "是否编译安装 Python 3.10 到 /opt/python3.10? ${YELLOW}[y/n]${NC}: "
            read -r py_choice
            case "$py_choice" in
                y|Y)
                    log_info "开始编译安装 Python 3.10..."
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
                    log_info "Python 3.10 编译安装完成"
                    ;;
                n|N)
                    log_error "已取消安装，需要 Python 3.10+ 才能运行面板"
                    exit 1
                    ;;
                *)
                    log_error "无效输入"
                    exit 1
                    ;;
            esac
        else
            PYTHON_CMD="python3"
            log_info "Python 版本: $py_version"
        fi
    else
        log_error "未检测到 Python3"
        exit 1
    fi

    mem_total=$(free -m | awk '/^Mem:/{print $2}')
    log_info "系统内存: ${mem_total}MB"
    if [ "$mem_total" -lt 512 ]; then
        log_warn "内存不足 512MB，面板运行可能不稳定"
    fi
}

# ==================== 2. 克隆仓库 ====================
step_clone_repo() {
    log_step 2 "克隆仓库"

    if [ -d "$BASE_DIR" ]; then
        log_info "目录 $BASE_DIR 已存在"
        if [ -f "$BACKEND_DIR/main.py" ]; then
            log_info "项目代码已存在，跳过克隆"
            return
        fi
        log_warn "目录存在但项目不完整，重新克隆..."
        rm -rf "$BASE_DIR"
    fi

    if ! command -v git &>/dev/null; then
        $PKG_INSTALL git
    fi

    log_info "克隆仓库: $GIT_REPO_URL"
    git clone --depth 1 "$GIT_REPO_URL" "$BASE_DIR"
    log_info "仓库克隆完成"
}

# ==================== 3. 创建目录结构 ====================
step_create_dirs() {
    log_step 3 "创建目录结构"

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
            log_info "创建目录: $dir"
        fi
    done
}

# ==================== 4. 创建虚拟环境 ====================
step_create_venv() {
    log_step 4 "创建 Python 虚拟环境"

    if [ -d "$VENV_DIR" ]; then
        log_info "虚拟环境已存在，跳过创建"
    else
        log_info "创建虚拟环境: $VENV_DIR"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi

    log_info "升级 pip..."
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
    "$VENV_DIR/bin/pip" config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
}

# ==================== 5. 安装依赖 ====================
step_install_deps() {
    log_step 5 "安装 Python 依赖"

    if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
        log_error "未找到 $BACKEND_DIR/requirements.txt"
        exit 1
    fi

    log_info "安装依赖..."
    "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" --default-timeout=100
    log_info "依赖安装完成"
}

# ==================== 6. 配置面板设置 ====================
step_configure() {
    log_step 6 "配置面板设置"

    secret_key=$($PYTHON_CMD -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32 2>/dev/null || echo "blackpotbpanel-$(date +%s)-$$")

    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
    fi

    cat > "$CONFIG_FILE" <<EOF
# 应用配置
APP_NAME=BlackPotBPanel
DEBUG=False
VERSION=2.0.1

# JWT配置
SECRET_KEY=$secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 时区配置
TIMEZONE=Asia/Shanghai

# API文档配置
ENABLE_DOCS=True

# 通用设置
LANGUAGE=$CFG_LANGUAGE
THEME=dark
LOGIN_NOTIFY=True
RECYCLE=True

# 服务器配置
HOST=0.0.0.0
PORT=$CFG_PORT

# SSL配置
SSL_ENABLED=$CFG_SSL

# 安全入口配置
SECURITY_ENTRANCE=$CFG_ENTRANCE
EOF
    log_info "配置文件已创建/更新"

    if [ -f "$BACKEND_DIR/app/__init__.py.prod" ] && [ ! -f "$BACKEND_DIR/app/__init__.py" ]; then
        cp "$BACKEND_DIR/app/__init__.py.prod" "$BACKEND_DIR/app/__init__.py"
        log_info "__init__.py 已配置"
    fi
}

# ==================== 7. 配置系统服务 ====================
step_systemd() {
    log_step 7 "配置系统服务"

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
    log_info "Systemd 服务文件已创建"
}

# ==================== 8. 部署 CLI 管理工具 ====================
step_deploy_cli() {
    log_step 8 "部署 CLI 管理工具"

    local bpctl_src="$BASE_DIR/cli/bpctl"
    local bpctl_dst="/usr/local/bin/bpctl"

    if [ -f "$bpctl_src" ]; then
        if [ -L "$bpctl_dst" ] || [ -f "$bpctl_dst" ]; then
            log_info "bpctl 已部署，更新链接..."
            rm -f "$bpctl_dst"
        fi
        chmod +x "$bpctl_src"
        ln -sf "$bpctl_src" "$bpctl_dst"
        log_info "bpctl 已部署到 /usr/local/bin/bpctl"
    else
        log_warn "未找到 $bpctl_src，跳过部署"
    fi
}

# ==================== 9. 配置防火墙 ====================
step_firewall() {
    log_step 9 "配置防火墙"

    log_info "开放端口: $CFG_PORT"

    if command -v firewall-cmd &>/dev/null; then
        firewall-cmd --zone=public --add-port="${CFG_PORT}/tcp" --permanent 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    elif command -v ufw &>/dev/null; then
        ufw allow "${CFG_PORT}/tcp" 2>/dev/null || true
    else
        log_warn "请手动开放端口 $CFG_PORT"
    fi
}

# ==================== 10. 启动面板服务 ====================
step_start() {
    log_step 10 "启动面板服务"

    systemctl enable "$SERVICE_NAME" 2>/dev/null || true
    systemctl restart "$SERVICE_NAME" 2>/dev/null || {
        log_warn "systemctl 启动失败，尝试直接启动..."
        cd "$BACKEND_DIR"
        nohup "$VENV_DIR/bin/python" main.py > /dev/null 2>&1 &
        log_info "面板已启动 (PID: $!)"
    }

    sleep 2

    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "面板服务运行正常"
    elif pgrep -f "python main.py" > /dev/null; then
        log_info "面板进程运行正常"
    else
        log_warn "面板未运行，请检查日志后手动启动"
    fi
}

# ==================== 11. 安装完成 ====================
step_done() {
    log_step 11 "安装完成"

    ip_addr=$(ip -4 route get 1 2>/dev/null | grep -oP 'src \K[\d.]+' 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || curl -s --max-time 3 ifconfig.me 2>/dev/null || echo "")

    if [ "$CFG_SSL" = "True" ]; then
        proto="https"
        ssl_label="已启用"
    else
        proto="http"
        ssl_label="已禁用"
    fi

    echo ""
    echo -e "${GREEN}================================================================"
    echo "               BlackPotBPanel V2 安装成功！"
    echo "================================================================"
    echo -e "${NC}"
    if [ -n "$ip_addr" ]; then
        echo -e "  面板地址:    ${CYAN}${proto}://${ip_addr}:${CFG_PORT}${NC}"
        if [ -n "$CFG_ENTRANCE" ]; then
            echo -e "  入口地址:    ${CYAN}${proto}://${ip_addr}:${CFG_PORT}/${CFG_ENTRANCE}${NC}"
        fi
    fi
    echo -e "  面板地址:    ${CYAN}${proto}://localhost:${CFG_PORT}${NC}"
    if [ -n "$CFG_ENTRANCE" ]; then
        echo -e "  入口地址:    ${CYAN}${proto}://localhost:${CFG_PORT}/${CFG_ENTRANCE}${NC}"
    fi
    echo ""
    echo -e "  默认账号:    ${YELLOW}admin${NC}"
    echo -e "  默认密码:    ${YELLOW}admin@123${NC}"
    echo ""
    echo -e "  安装目录:    ${BLUE}$BASE_DIR${NC}"
    echo -e "  虚拟环境:    ${BLUE}$VENV_DIR${NC}"
    echo -e "  HTTPS:       ${YELLOW}$ssl_label${NC}"
    echo ""
    echo -e "  ${YELLOW}管理命令:${NC}"
    echo -e "    bpctl"
    echo ""
    echo -e "  ${YELLOW}请及时修改默认密码！${NC}"
    echo ""
    echo -e "${GREEN}==============================================================${NC}"
}

# ==================== 主流程 ====================
main() {
    check_root

    echo ""
    log_info "安装目录: $BASE_DIR"
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
