#!/bin/bash

# BookBot 一键部署脚本 (VPS专用)
# 支持系统: Ubuntu, Debian, CentOS
# 功能: 安装Docker, 配置环境, 启动服务, 更新代码

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}请使用 root 权限运行此脚本 (sudo ./deploy_vps.sh)${NC}"
  exit 1
fi

# 函数: 打印带颜色的信息
info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 0. 安装基础工具
install_base_tools() {
    info "检查并安装基础工具 (git, nano, curl)..."
    if command -v apt-get &> /dev/null; then
        apt-get update -y
        apt-get install -y git nano curl
    elif command -v yum &> /dev/null; then
        yum install -y git nano curl
    else
        warn "未检测到 apt 或 yum，跳过基础工具安装，请手动确保安装了 git, nano, curl"
    fi
}

# 1. 安装 Docker
install_docker() {
    if ! command -v docker &> /dev/null; then
        info "正在安装 Docker..."
        if curl -fsSL https://get.docker.com | sh; then
            systemctl enable docker
            systemctl start docker
            info "Docker 安装完成"
        else
            error "Docker 自动安装失败，请尝试手动安装：curl -fsSL https://get.docker.com | sh"
            exit 1
        fi
    else
        info "Docker 已安装"
    fi

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        warn "Docker Compose 插件未找到，尝试安装..."
        if command -v apt-get &> /dev/null; then
            apt-get update && apt-get install -y docker-compose-plugin
        elif command -v yum &> /dev/null; then
            yum install -y docker-compose-plugin
        else
            warn "自动安装失败，请手动安装 docker-compose-plugin"
        fi
    fi
}

# 2. 配置环境变量
configure_env() {
    if [ ! -f .env ]; then
        info "检测到首次运行，正在创建配置文件..."
        if [ -f .env.example ]; then
            cp .env.example .env
        else
            warn "未找到 .env.example，将创建空白 .env"
            touch .env
        fi

        # 交互式输入 Token
        while true; do
            read -p "请输入 Telegram Bot Token (必填): " BOT_TOKEN
            if [ ! -z "$BOT_TOKEN" ]; then
                break
            else
                error "Bot Token 不能为空！"
            fi
        done
        # 如果 .env 中没有 BOT_TOKEN= 行，追加一行
        if ! grep -q "BOT_TOKEN=" .env; then
            echo "BOT_TOKEN=" >> .env
        fi
        sed -i "s/BOT_TOKEN=.*/BOT_TOKEN=$BOT_TOKEN/" .env

        # 自动生成 Meilisearch Key
        MEILI_KEY=$(openssl rand -hex 16)
        info "已自动生成 Meilisearch Master Key: $MEILI_KEY"
        if ! grep -q "MEILI_MASTER_KEY=" .env; then
            echo "MEILI_MASTER_KEY=" >> .env
        fi
        sed -i "s/MEILI_MASTER_KEY=.*/MEILI_MASTER_KEY=$MEILI_KEY/" .env

        # 询问 Admin ID
        read -p "请输入管理员 Telegram ID (可选, 多个用逗号分隔): " ADMIN_IDS
        if [ ! -z "$ADMIN_IDS" ]; then
             # 清理输入：替换中文逗号，去除首尾空格，去除尾部逗号
            ADMIN_IDS=$(echo "$ADMIN_IDS" | sed 's/，/,/g' | sed 's/^[ \t]*//;s/[ \t]*$//' | sed 's/,$//')
            
            if [ ! -z "$ADMIN_IDS" ]; then
                if ! grep -q "ADMIN_IDS=" .env; then
                    echo "ADMIN_IDS=" >> .env
                fi
                sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=[$ADMIN_IDS]/" .env
            fi
        fi

        info "配置文件 .env 已生成！"
    else
        info ".env 配置文件已存在，跳过配置。"
    fi
}

# 3. 启动服务
start_services() {
    if ! command -v docker &> /dev/null; then
        error "未找到 docker 命令。请先安装 Docker。"
        exit 1
    fi
    info "正在启动服务..."
    docker compose up -d --build
    if [ $? -eq 0 ]; then
        info "✅ 服务启动成功！"
        echo -e "------------------------------------------------"
        echo -e "你可以使用以下命令查看日志："
        echo -e "${YELLOW}docker compose logs -f${NC}"
        echo -e "------------------------------------------------"
    else
        error "服务启动失败，请检查上方错误信息。"
    fi
}

# 4. 更新代码
update_code() {
    info "正在拉取最新代码..."
    git pull
    if [ $? -ne 0 ]; then
        error "Git pull 失败，请检查网络或 Git 配置"
        return
    fi
    info "正在重建并重启服务..."
    docker compose up -d --build
    info "✅ 更新完成！"
}

# 5. 查看日志
view_logs() {
    docker compose logs -f
}

# 6. 停止服务
stop_services() {
    info "正在停止服务..."
    docker compose down
    info "✅ 服务已停止"
}

# 主菜单
show_menu() {
    clear
    echo -e "========================================"
    echo -e "   📚 BookBot 搜书机器人管理脚本"
    echo -e "========================================"
    echo -e "1. 🚀 安装并启动 (首次部署)"
    echo -e "2. 🔄 更新代码并重启"
    echo -e "3. 📜 查看运行日志"
    echo -e "4. 🛑 停止服务"
    echo -e "5. ⚙️  编辑配置文件 (.env)"
    echo -e "0. 🚪 退出"
    echo -e "========================================"
    read -p "请输入数字 [0-5]: " choice

    case $choice in
        1)
            install_base_tools
            install_docker
            configure_env
            start_services
            ;;
        2)
            update_code
            ;;
        3)
            view_logs
            ;;
        4)
            stop_services
            ;;
        5)
            if command -v nano &> /dev/null; then
                nano .env
            else
                vi .env
            fi
            ;;
        0)
            exit 0
            ;;
        *)
            error "无效的选择"
            sleep 1
            show_menu
            ;;
    esac
}

# 如果带参数运行，则执行对应函数（方便自动化）
if [ "$1" == "install" ]; then
    install_base_tools
    install_docker
    configure_env
    start_services
    exit 0
fi

# 否则显示菜单
while true; do
    show_menu
    echo -e "\n按 Enter 键返回菜单..."
    read
done
