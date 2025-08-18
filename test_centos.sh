#!/bin/bash

# CentOS兼容性测试脚本
# 用于测试deploy.sh在CentOS系统上的兼容性

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_header() {
    echo -e "${PURPLE}"
    echo "=========================================="
    echo "      CentOS兼容性测试脚本"
    echo "=========================================="
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检测操作系统信息
check_os_info() {
    echo ""
    print_info "=== 系统信息检测 ==="
    
    echo "OSTYPE: $OSTYPE"
    
    if [ -f /etc/os-release ]; then
        echo "OS Release信息:"
        cat /etc/os-release
    fi
    
    if [ -f /etc/redhat-release ]; then
        echo "RedHat Release: $(cat /etc/redhat-release)"
    fi
    
    if [ -f /etc/centos-release ]; then
        echo "CentOS Release: $(cat /etc/centos-release)"
    fi
    
    if [ -f /etc/fedora-release ]; then
        echo "Fedora Release: $(cat /etc/fedora-release)"
    fi
}

# 检测包管理器
check_package_managers() {
    echo ""
    print_info "=== 包管理器检测 ==="
    
    if command -v dnf &> /dev/null; then
        print_success "找到 dnf: $(dnf --version | head -1)"
    else
        print_warning "未找到 dnf"
    fi
    
    if command -v yum &> /dev/null; then
        print_success "找到 yum: $(yum --version | head -1)"
    else
        print_warning "未找到 yum"
    fi
}

# 检测系统工具
check_system_tools() {
    echo ""
    print_info "=== 系统工具检测 ==="
    
    tools=("curl" "wget" "git" "systemctl")
    
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            print_success "$tool: $(command -v $tool)"
        else
            print_warning "$tool: 未安装"
        fi
    done
}

# 检测Docker相关
check_docker() {
    echo ""
    print_info "=== Docker环境检测 ==="
    
    if command -v docker &> /dev/null; then
        print_success "Docker: $(docker --version)"
    else
        print_warning "Docker: 未安装"
    fi
    
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose: $(docker-compose --version)"
    else
        print_warning "Docker Compose: 未安装"
    fi
    
    # 检查Docker服务状态
    if systemctl is-active --quiet docker 2>/dev/null; then
        print_success "Docker服务: 运行中"
    else
        print_warning "Docker服务: 未运行或未安装"
    fi
}

# 检测网络连接
check_network() {
    echo ""
    print_info "=== 网络连接检测 ==="
    
    # 测试GitHub连接
    if curl -s --connect-timeout 5 https://github.com &> /dev/null; then
        print_success "GitHub连接: 正常"
    else
        print_warning "GitHub连接: 失败"
    fi
    
    # 测试Docker Hub连接
    if curl -s --connect-timeout 5 https://registry-1.docker.io &> /dev/null; then
        print_success "Docker Hub连接: 正常"
    else
        print_warning "Docker Hub连接: 失败"
    fi
    
    # 测试get.docker.com连接
    if curl -s --connect-timeout 5 https://get.docker.com &> /dev/null; then
        print_success "Docker安装脚本连接: 正常"
    else
        print_warning "Docker安装脚本连接: 失败"
    fi
}

# 模拟deploy.sh的操作系统检测
simulate_os_detection() {
    echo ""
    print_info "=== 模拟deploy.sh操作系统检测 ==="
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
        elif [ -f /etc/redhat-release ] || [ -f /etc/centos-release ] || [ -f /etc/fedora-release ]; then
            OS="redhat"
            # 获取具体版本信息
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
    else
        OS="unknown"
    fi
    
    echo "检测结果: OS=$OS"
    if [[ "$OS" == "redhat" ]]; then
        echo "发行版信息: $DISTRO_INFO"
        print_success "CentOS/RHEL系统检测成功"
    else
        print_error "未检测到CentOS/RHEL系统"
    fi
}

# 检查权限
check_permissions() {
    echo ""
    print_info "=== 权限检测 ==="
    
    if [ "$EUID" -eq 0 ]; then
        print_success "当前用户: root (可以安装Docker)"
    else
        print_warning "当前用户: $(whoami) (需要sudo权限安装Docker)"
        
        if sudo -n true 2>/dev/null; then
            print_success "sudo权限: 可用 (无需密码)"
        else
            print_info "sudo权限: 需要密码验证"
        fi
    fi
}

# 主函数
main() {
    print_header
    
    check_os_info
    check_package_managers
    check_system_tools
    check_docker
    check_network
    simulate_os_detection
    check_permissions
    
    echo ""
    print_info "=== 测试完成 ==="
    
    if [[ "$OS" == "redhat" ]]; then
        print_success "✅ 系统兼容性检查通过！deploy.sh应该可以在此CentOS系统上正常工作"
        echo ""
        print_info "📋 建议的部署步骤:"
        echo "1. sudo ./deploy.sh install    # 安装Docker环境"
        echo "2. cp config/config.yaml.template config/config.yaml"
        echo "3. 编辑config/config.yaml配置文件"
        echo "4. ./deploy.sh build          # 构建镜像" 
        echo "5. ./deploy.sh start          # 启动服务"
    else
        print_error "❌ 当前系统可能不完全兼容，建议手动安装Docker"
    fi
}

# 运行测试
main 