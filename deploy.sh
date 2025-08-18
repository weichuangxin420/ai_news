#!/bin/bash

# AI新闻收集系统 - Docker部署脚本
# 使用方法: ./deploy.sh [build|start|stop|restart|status|logs|clean|update]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="ai_news"
CONTAINER_NAME="ai_news_app"
IMAGE_NAME="ai_news"

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    if [ ! -f "config/config.yaml" ]; then
        print_error "配置文件不存在: config/config.yaml"
        print_info "请复制 config/config.yaml.template 并填写正确的配置"
        exit 1
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
    cp -r data/ $BACKUP_DIR/
    cp config/config.yaml $BACKUP_DIR/
    
    print_message "数据备份完成: $BACKUP_DIR"
}

# 显示帮助信息
show_help() {
    echo "AI新闻收集系统 - Docker部署脚本"
    echo ""
    echo "使用方法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  build     - 构建Docker镜像"
    echo "  start     - 启动服务"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  status    - 显示服务状态"
    echo "  logs      - 显示服务日志"
    echo "  clean     - 清理所有Docker资源"
    echo "  update    - 更新并重启服务"
    echo "  backup    - 备份数据"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 build     # 构建镜像"
    echo "  $0 start     # 启动服务"
    echo "  $0 logs      # 查看日志"
}

# 主函数
main() {
    check_docker
    
    case "${1:-help}" in
        build)
            check_config
            create_directories
            build_image
            ;;
        start)
            check_config
            create_directories
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        clean)
            clean_resources
            ;;
        update)
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