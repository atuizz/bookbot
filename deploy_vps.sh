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

# 1. 安装 Docker
install_docker() {
    if ! command -v docker &> /dev/null; then
        info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        info "Docker 安装完成"
    else
        info "Docker 已安装"
    fi

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        warn "Docker Compose 插件未找到，尝试安装..."
        apt-get update && apt-get install -y docker-compose-plugin || warn "自动安装失败，请手动安装 docker-compose-plugin"
    fi
}

# 2. 配置环境变量
configure_env() {
    if [ ! -f .env ]; then
        info "检测到首次运行，正在创建配置文件..."
        cp .env.example .env

        # 交互式输入 Token
        while true; do
            read -p "请输入 Telegram Bot Token (必填): " BOT_TOKEN
            if [ ! -z "$BOT_TOKEN" ]; then
                break
            else
                error "Bot Token 不能为空！"
            fi
        done
        sed -i "s/BOT_TOKEN=.*/BOT_TOKEN=$BOT_TOKEN/" .env

        # 自动生成 Meilisearch Key
        MEILI_KEY=$(openssl rand -hex 16)
        info "已自动生成 Meilisearch Master Key: $MEILI_KEY"
        sed -i "s/MEILI_MASTER_KEY=.*/MEILI_MASTER_KEY=$MEILI_KEY/" .env

        # 询问 Admin ID
        read -p "请输入管理员 Telegram ID (可选, 多个用逗号分隔): " ADMIN_IDS
        if [ ! -z "$ADMIN_IDS" ]; then
            # 简单处理格式，假设用户输入的是数字
            sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=[$ADMIN_IDS]/" .env
        fi

        info "配置文件 .env 已生成！"
    else
        info ".env 配置文件已存在，跳过配置。"
    fi
}

# 3. 启动服务
start_services() {
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
            nano .env
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
