#!/bin/bash

# AI新闻收集系统 - Docker部署脚本
# 使用方法: ./deploy.sh [install|build|start|stop|restart|status|logs|clean|update|backup]

set -e

# 捕获Ctrl+C中断信号
trap 'echo -e "\n${YELLOW}⚠️  检查被用户中断${NC}"; exit 130' INT

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

# 测试网络连接
test_connection() {
    local name="$1"
    local url="$2"
    local timeout="${3:-15}"
    
    if command -v timeout &> /dev/null; then
        if timeout "$timeout" curl -s --connect-timeout 10 --max-time "$timeout" "$url" &> /dev/null; then
            return 0
        else
            return 1
        fi
    else
        if curl -s --connect-timeout 10 --max-time "$timeout" "$url" &> /dev/null; then
            return 0
        else
            return 1
        fi
    fi
}

# 快速检测关键源
quick_source_check() {
    print_step "快速检测关键软件源..."
    
    local critical_sources=(
        "PyPI官方:https://pypi.org"
        "PyPI清华镜像:https://pypi.tuna.tsinghua.edu.cn"
        "Docker Hub:https://registry-1.docker.io"
        "GitHub:https://github.com"
    )
    
    local quick_successful=0
    for source in "${critical_sources[@]}"; do
        name="${source%:*}"
        url="${source#*:}"
        print_info "测试 $name..."
        
        if test_connection "$name" "$url" 10; then
            print_message "✅ $name: 正常"
            ((quick_successful++))
        else
            print_warning "❌ $name: 失败"
        fi
    done
    
    echo ""
    print_info "关键源检测: $quick_successful/${#critical_sources[@]} 可用"
    
    if [[ $quick_successful -eq ${#critical_sources[@]} ]]; then
        print_message "🌟 所有关键源都可用，网络环境优秀！"
        return 0
    elif [[ $quick_successful -gt $((${#critical_sources[@]} / 2)) ]]; then
        print_warning "⚠️  部分关键源不可用，但仍可继续部署"
        return 1
    else
        print_error "🚨 大部分关键源不可用，建议检查网络连接"
        return 2
    fi
}

# 完整的源检测功能
full_source_check() {
    print_step "开始完整的软件源检测..."
    
    # 定义所有要检测的源
    declare -A sources=(
        # Python PyPI源
        ["PyPI官方"]="https://pypi.org"
        ["PyPI清华镜像"]="https://pypi.tuna.tsinghua.edu.cn"
        ["PyPI阿里镜像"]="https://mirrors.aliyun.com/pypi"
        ["PyPI豆瓣镜像"]="https://pypi.douban.com"
        ["PyPI中科大镜像"]="https://pypi.mirrors.ustc.edu.cn"
        
        # Docker相关源
        ["Docker Hub"]="https://registry-1.docker.io"
        ["Docker安装脚本"]="https://get.docker.com"
        ["Docker阿里镜像"]="https://registry.cn-hangzhou.aliyuncs.com"
        
        # Linux包管理源
        ["Ubuntu官方源"]="http://archive.ubuntu.com"
        ["Ubuntu清华镜像"]="https://mirrors.tuna.tsinghua.edu.cn/ubuntu"
        ["Ubuntu阿里镜像"]="https://mirrors.aliyun.com/ubuntu"
        ["Debian官方源"]="http://deb.debian.org"
        ["Debian清华镜像"]="https://mirrors.tuna.tsinghua.edu.cn/debian"
        ["CentOS阿里镜像"]="https://mirrors.aliyun.com/centos"
        ["EPEL源"]="https://dl.fedoraproject.org/pub/epel"
        
        # Git相关
        ["GitHub"]="https://github.com"
        ["GitLab"]="https://gitlab.com"
        ["Gitee"]="https://gitee.com"
    )
    
    # 统计变量
    total_sources=${#sources[@]}
    successful_sources=0
    failed_sources=()
    pypi_available=()
    
    echo ""
    print_info "=== 开始检测各类软件源 ==="
    echo ""
    
    # 遍历检测所有源
    for name in "${!sources[@]}"; do
        url="${sources[$name]}"
        print_info "正在测试 $name..."
        
        if test_connection "$name" "$url" 15; then
            print_message "✅ $name: 连接正常"
            ((successful_sources++))
            
            # 记录可用的PyPI源
            if [[ "$name" == *"PyPI"* ]]; then
                pypi_available+=("$name: $url")
            fi
        else
            print_warning "❌ $name: 连接失败"
            failed_sources+=("$name")
        fi
        
        # 添加短暂延迟，避免过于频繁的请求
        sleep 0.1
    done
    
    # 显示检测总结
    echo ""
    print_info "=== 源检测总结 ==="
    print_info "总检测数: $total_sources"
    print_info "成功连接: $successful_sources"
    print_info "连接失败: $((total_sources - successful_sources))"
    print_info "成功率: $(( successful_sources * 100 / total_sources ))%"
    
    # 显示可用的PyPI源建议
    if [[ ${#pypi_available[@]} -gt 0 ]]; then
        echo ""
        print_info "=== 可用的PyPI源 ==="
        for pypi in "${pypi_available[@]}"; do
            print_message "✅ $pypi"
        done
        print_info "Dockerfile将智能选择最优源进行构建"
    fi
    
    # 网络环境评估
    echo ""
    print_info "=== 网络环境评估 ==="
    if [[ $successful_sources -gt $((total_sources * 80 / 100)) ]]; then
        print_message "🌟 网络环境: 优秀 (>80% 源可用)"
        print_info "建议: 可以使用官方源，构建速度会很快"
        return 0
    elif [[ $successful_sources -gt $((total_sources * 60 / 100)) ]]; then
        print_message "🟢 网络环境: 良好 (>60% 源可用)"
        print_info "建议: 优先使用国内镜像源以提高稳定性"
        return 0
    elif [[ $successful_sources -gt $((total_sources * 40 / 100)) ]]; then
        print_warning "🟡 网络环境: 一般 (>40% 源可用)"
        print_info "建议: 使用多源配置，设置备用源"
        return 1
    else
        print_error "🔴 网络环境: 较差 (<40% 源可用)"
        print_info "建议: 检查网络连接，考虑使用代理或VPN"
        return 2
    fi
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
    
    # 检查是否跳过网络测试
    SKIP_NETWORK_CHECK="${2:-false}"
    if [[ "$SKIP_NETWORK_CHECK" == "--skip-network" ]]; then
        print_warning "⚠️  跳过网络连接检查"
        SKIP_NETWORK_CHECK=true
    else
        SKIP_NETWORK_CHECK=false
    fi
    
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
    
    # 检测网络连接和软件源
    if [[ "$SKIP_NETWORK_CHECK" == "false" ]]; then
        echo ""
        print_info "=== 软件源连接检测 ==="
        print_info "ℹ️  网络检查可能需要1-2分钟，如需跳过请使用: $0 check --skip-network"
        
        # 执行快速检测
        if quick_source_check; then
            print_info "快速检测通过，是否需要完整检测？[y/N]"
            read -t 10 -r do_full_check
            if [[ "$do_full_check" == "y" || "$do_full_check" == "Y" ]]; then
                full_source_check
            else
                print_info "已跳过完整检测，关键源检测通过"
            fi
        else
            print_warning "快速检测发现问题，建议运行完整检测"
            print_info "是否运行完整检测？[Y/n]"
            read -t 15 -r do_full_check
            if [[ "$do_full_check" != "n" && "$do_full_check" != "N" ]]; then
                full_source_check
            else
                print_warning "已跳过完整检测，可能影响构建成功率"
            fi
        fi
    else
        echo ""
        print_warning "⚠️  已跳过网络连接检测"
    fi
    
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
    
    # 检查是否支持多架构构建
    if command -v docker buildx >/dev/null 2>&1; then
        print_info "检测到Docker Buildx，是否使用多架构构建？[y/N]"
        read -t 10 -r use_buildx
        if [[ "$use_buildx" == "y" || "$use_buildx" == "Y" ]]; then
            print_info "使用Docker Buildx进行多架构构建..."
            docker buildx build --platform linux/amd64,linux/arm64 -t "${IMAGE_NAME}:latest" . --load || \
            docker build -t "${IMAGE_NAME}:latest" .
            print_message "多架构Docker镜像构建完成"
            return
        fi
    fi
    
    # 使用标准构建（Dockerfile已经包含多源优化）
    print_info "使用多源优化Dockerfile进行构建..."
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
    echo "              可选参数: --skip-network (跳过网络检查)"
    echo "  sources   - 检测软件源连接状态"
    echo "              --quick: 快速检测关键源"
    echo "              --full:  完整检测所有源 (默认)"
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
            check_system_compatibility "$@"
            ;;
        sources)
            case "${2:-}" in
                --quick|-q)
                    quick_source_check
                    ;;
                --full|-f|"")
                    full_source_check
                    ;;
                *)
                    print_error "未知源检测选项: $2"
                    echo "用法: $0 sources [--quick|--full]"
                    exit 1
                    ;;
            esac
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