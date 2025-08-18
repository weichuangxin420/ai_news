#!/bin/bash

# AI新闻收集系统 - Docker部署脚本
# 使用方法: ./deploy.sh [install|build|start|stop|restart|status|logs|clean|update|backup]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="ai_news"
CONTAINER_NAME="ai_news_app"
IMAGE_NAME="ai_news"

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] ❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO] ℹ️  $1${NC}"
}

print_step() {
    echo -e "${PURPLE}[STEP] 🚀 $1${NC}"
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
        elif [ -f /etc/redhat-release ] || [ -f /etc/centos-release ] || [ -f /etc/fedora-release ]; then
            OS="redhat"
            # 获取具体版本信息用于调试
            if [ -f /etc/centos-release ]; then
                DISTRO_INFO=$(cat /etc/centos-release)
            elif [ -f /etc/redhat-release ]; then
                DISTRO_INFO=$(cat /etc/redhat-release)
            elif [ -f /etc/fedora-release ]; then
                DISTRO_INFO=$(cat /etc/fedora-release)
            fi
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
}

# 安装Docker（仅Linux）
install_docker() {
    print_step "检查并安装Docker环境..."
    
    # 检查是否已安装
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        print_message "Docker环境已就绪"
        print_info "Docker版本: $(docker --version)"
        print_info "Docker Compose版本: $(docker-compose --version)"
        return 0
    fi
    
    # 检查操作系统支持
    detect_os
    if [[ "$OS" == "redhat" ]]; then
        print_info "检测到系统: $DISTRO_INFO"
    fi
    
    if [[ "$OS" != "debian" && "$OS" != "redhat" ]]; then
        print_error "自动安装仅支持 Ubuntu/Debian 和 CentOS/RHEL 系统"
        print_info "当前检测到的系统类型: $OS"
        print_info "请手动安装Docker和Docker Compose，然后重新运行脚本"
        exit 1
    fi
    
    # 检查权限
    if [ "$EUID" -ne 0 ]; then
        print_error "安装Docker需要root权限"
        print_info "请使用: sudo $0 install"
        exit 1
    fi
    
    print_warning "即将自动安装Docker，是否继续? (y/N)"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            ;;
        *)
            print_info "取消安装，请手动安装Docker后重试"
            exit 0
            ;;
    esac
    
    # 安装Docker
    if ! command -v docker &> /dev/null; then
        print_step "安装Docker..."
        case $OS in
            "debian")
                apt-get update -y
                apt-get install -y curl
                ;;
            "redhat")
                # 检测是否使用dnf或yum
                if command -v dnf &> /dev/null; then
                    print_info "检测到dnf包管理器 (CentOS 8+/RHEL 8+/Fedora)"
                    dnf update -y
                    dnf install -y curl
                elif command -v yum &> /dev/null; then
                    print_info "检测到yum包管理器 (CentOS 7/RHEL 7)"
                    yum update -y
                    yum install -y curl
                else
                    print_error "未找到dnf或yum包管理器"
                    exit 1
                fi
                ;;
        esac
        
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        
        systemctl enable docker
        systemctl start docker
        print_message "Docker安装完成"
    fi
    
    # 安装Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_step "安装Docker Compose..."
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
        print_message "Docker Compose安装完成"
    fi
    
    print_message "Docker环境安装成功！"
}

# 系统兼容性检查
check_system_compatibility() {
    print_step "🔍 系统兼容性检查..."
    echo ""
    
    # 检测操作系统信息
    print_info "=== 系统信息 ==="
    echo "OSTYPE: $OSTYPE"
    
    if [ -f /etc/os-release ]; then
        echo "操作系统详情:"
        cat /etc/os-release | head -5
    fi
    
    if [ -f /etc/redhat-release ]; then
        echo "RedHat系统: $(cat /etc/redhat-release)"
    fi
    
    if [ -f /etc/centos-release ]; then
        echo "CentOS系统: $(cat /etc/centos-release)"
    fi
    
    # 检测包管理器
    echo ""
    print_info "=== 包管理器检测 ==="
    
    if command -v dnf &> /dev/null; then
        print_message "✅ 找到 dnf: $(dnf --version 2>/dev/null | head -1 || echo "已安装")"
    else
        print_warning "⚠️  未找到 dnf"
    fi
    
    if command -v yum &> /dev/null; then
        print_message "✅ 找到 yum: $(yum --version 2>/dev/null | head -1 || echo "已安装")"
    else
        print_warning "⚠️  未找到 yum"
    fi
    
    if command -v apt-get &> /dev/null; then
        print_message "✅ 找到 apt-get: $(apt-get --version 2>/dev/null | head -1 || echo "已安装")"
    else
        print_warning "⚠️  未找到 apt-get"
    fi
    
    # 检测系统工具
    echo ""
    print_info "=== 系统工具检测 ==="
    
    tools=("curl" "wget" "git" "systemctl")
    missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            print_message "✅ $tool: $(command -v $tool)"
        else
            print_warning "⚠️  $tool: 未安装"
            missing_tools+=("$tool")
        fi
    done
    
    # 检测Docker环境
    echo ""
    print_info "=== Docker环境检测 ==="
    
    if command -v docker &> /dev/null; then
        print_message "✅ Docker: $(docker --version)"
        
        # 检查Docker服务状态
        if systemctl is-active --quiet docker 2>/dev/null; then
            print_message "✅ Docker服务: 运行中"
        else
            print_warning "⚠️  Docker服务: 未运行"
        fi
        
        # 检查Docker权限
        if docker ps &> /dev/null; then
            print_message "✅ Docker权限: 正常"
        else
            print_warning "⚠️  Docker权限: 需要sudo或将用户加入docker组"
        fi
    else
        print_warning "⚠️  Docker: 未安装"
    fi
    
    if command -v docker-compose &> /dev/null; then
        print_message "✅ Docker Compose: $(docker-compose --version)"
    else
        print_warning "⚠️  Docker Compose: 未安装"
    fi
    
    # 检测网络连接
    echo ""
    print_info "=== 网络连接检测 ==="
    
    # 测试关键网络连接
    networks=(
        "GitHub:https://github.com"
        "Docker Hub:https://registry-1.docker.io"
        "Docker安装:https://get.docker.com"
    )
    
    for network in "${networks[@]}"; do
        name="${network%:*}"
        url="${network#*:}"
        if curl -s --connect-timeout 5 "$url" &> /dev/null; then
            print_message "✅ $name 连接: 正常"
        else
            print_warning "⚠️  $name 连接: 失败"
        fi
    done
    
    # 模拟操作系统检测
    echo ""
    print_info "=== 部署兼容性检测 ==="
    
    detect_os
    echo "检测结果: OS=$OS"
    
    if [[ "$OS" == "redhat" ]]; then
        if [[ -n "$DISTRO_INFO" ]]; then
            echo "发行版信息: $DISTRO_INFO"
        fi
        print_message "✅ CentOS/RHEL系统 - 完全兼容"
    elif [[ "$OS" == "debian" ]]; then
        print_message "✅ Ubuntu/Debian系统 - 完全兼容"
    else
        print_warning "⚠️  未知系统类型 - 可能需要手动安装"
    fi
    
    # 检查权限
    echo ""
    print_info "=== 权限检测 ==="
    
    if [ "$EUID" -eq 0 ]; then
        print_message "✅ 当前用户: root (可直接安装Docker)"
    else
        print_warning "⚠️  当前用户: $(whoami) (安装Docker需要sudo权限)"
        
        if sudo -n true 2>/dev/null; then
            print_message "✅ sudo权限: 可用 (无需密码)"
        else
            print_info "ℹ️  sudo权限: 需要密码验证"
        fi
    fi
    
    # 总结和建议
    echo ""
    print_info "=== 检查总结 ==="
    
    if [[ "$OS" == "redhat" ]] || [[ "$OS" == "debian" ]]; then
        print_message "🎉 系统兼容性检查通过！"
        echo ""
        print_info "📋 建议的后续步骤:"
        
        if ! command -v docker &> /dev/null; then
            echo "1. sudo $0 install           # 安装Docker环境"
        else
            echo "1. Docker已安装，跳过安装步骤"
        fi
        
        echo "2. cp config/config.yaml.template config/config.yaml"
        echo "3. 编辑config/config.yaml配置文件"
        echo "4. $0 build                   # 构建镜像"
        echo "5. $0 start                   # 启动服务"
        
        if [[ ${#missing_tools[@]} -gt 0 ]]; then
            echo ""
            print_warning "⚠️  缺失工具建议安装:"
            if [[ "$OS" == "redhat" ]]; then
                if command -v dnf &> /dev/null; then
                    echo "sudo dnf install ${missing_tools[*]}"
                else
                    echo "sudo yum install ${missing_tools[*]}"
                fi
            else
                echo "sudo apt-get install ${missing_tools[*]}"
            fi
        fi
    else
        print_error "❌ 当前系统可能不完全兼容"
        print_info "建议手动安装Docker和Docker Compose"
    fi
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        print_info "运行以下命令自动安装: sudo $0 install"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装"
        print_info "运行以下命令自动安装: sudo $0 install"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    if [ ! -f "config/config.yaml" ]; then
        if [ -f "config/config.yaml.template" ]; then
            print_warning "配置文件不存在，是否从模板创建? (y/N)"
            read -r response
            case "$response" in
                [yY][eE][sS]|[yY]) 
                    cp config/config.yaml.template config/config.yaml
                    print_message "配置文件已创建: config/config.yaml"
                    print_warning "请编辑配置文件填入必要信息后重新运行"
                    exit 0
                    ;;
                *)
                    print_error "配置文件不存在: config/config.yaml"
                    print_info "请复制 config/config.yaml.template 并填写正确的配置"
                    exit 1
                    ;;
            esac
        else
            print_error "配置文件和模板都不存在"
            exit 1
        fi
    fi
    print_message "配置文件检查通过"
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."
    mkdir -p data/logs data/database data/reports logs
    print_message "目录创建完成"
}

# 构建Docker镜像
build_image() {
    print_message "开始构建Docker镜像..."
    docker-compose build --no-cache
    print_message "Docker镜像构建完成"
}

# 启动服务
start_service() {
    print_message "启动AI新闻收集服务..."
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_message "服务启动成功！"
        show_status
    else
        print_error "服务启动失败，请检查日志"
        docker-compose logs --tail=50
        exit 1
    fi
}

# 停止服务
stop_service() {
    print_message "停止AI新闻收集服务..."
    docker-compose down
    print_message "服务已停止"
}

# 重启服务
restart_service() {
    print_message "重启AI新闻收集服务..."
    docker-compose restart
    print_message "服务重启完成"
}

# 显示服务状态
show_status() {
    print_info "=== 服务状态 ==="
    docker-compose ps
    
    print_info "=== 容器健康状态 ==="
    docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "健康检查未配置"
    
    print_info "=== 资源使用情况 ==="
    docker stats --no-stream $CONTAINER_NAME 2>/dev/null || echo "容器未运行"
}

# 显示日志
show_logs() {
    print_info "显示服务日志 (Ctrl+C 退出)..."
    docker-compose logs -f --tail=100
}

# 清理资源
clean_resources() {
    print_warning "这将删除所有容器、镜像和数据卷，是否继续? (y/N)"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            print_message "清理Docker资源..."
            docker-compose down -v --rmi all
            docker system prune -f
            print_message "清理完成"
            ;;
        *)
            print_info "取消清理操作"
            ;;
    esac
}

# 更新服务
update_service() {
    print_message "更新AI新闻收集服务..."
    
    # 拉取最新代码（如果使用Git）
    if [ -d ".git" ]; then
        print_info "拉取最新代码..."
        git pull
    fi
    
    # 重新构建并启动
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    print_message "服务更新完成"
}

# 备份数据
backup_data() {
    BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
    print_message "备份数据到 $BACKUP_DIR..."
    
    mkdir -p $BACKUP_DIR
    cp -r data/ $BACKUP_DIR/ 2>/dev/null || print_warning "data目录不存在，跳过"
    cp config/config.yaml $BACKUP_DIR/ 2>/dev/null || print_warning "配置文件不存在，跳过"
    
    print_message "数据备份完成: $BACKUP_DIR"
}

# 显示帮助信息
show_help() {
    echo "AI新闻收集系统 - Docker部署脚本"
    echo ""
    echo "使用方法: $0 [命令]"
    echo ""
    echo "🔧 环境管理:"
    echo "  install   - 自动安装Docker环境 (需要sudo权限)"
    echo "  check     - 检查系统兼容性和环境状态"
    echo ""
    echo "🚀 服务管理:"
    echo "  build     - 构建Docker镜像"
    echo "  start     - 启动服务"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  status    - 显示服务状态"
    echo "  logs      - 显示服务日志"
    echo ""
    echo "🛠️  维护操作:"
    echo "  update    - 更新并重启服务"
    echo "  backup    - 备份数据"
    echo "  clean     - 清理所有Docker资源"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "📝 使用示例:"
    echo "  sudo $0 install    # 首次安装Docker环境"
    echo "  $0 build          # 构建镜像"
    echo "  $0 start          # 启动服务"
    echo "  $0 logs           # 查看日志"
    echo ""
    echo "💡 快速开始:"
    echo "  1. $0 check               # 检查系统兼容性"
    echo "  2. sudo $0 install        # 安装Docker环境"
    echo "  3. 编辑 config/config.yaml 配置文件"
    echo "  4. $0 build && $0 start    # 构建并启动服务"
}

# 主函数
main() {
    case "${1:-help}" in
        check)
            check_system_compatibility
            ;;
        install)
            install_docker
            ;;
        build)
            check_docker
            check_config
            create_directories
            build_image
            ;;
        start)
            check_docker
            check_config
            create_directories
            start_service
            ;;
        stop)
            check_docker
            stop_service
            ;;
        restart)
            check_docker
            restart_service
            ;;
        status)
            check_docker
            show_status
            ;;
        logs)
            check_docker
            show_logs
            ;;
        clean)
            check_docker
            clean_resources
            ;;
        update)
            check_docker
            update_service
            ;;
        backup)
            backup_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 