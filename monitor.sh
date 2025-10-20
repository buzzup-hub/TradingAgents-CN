#!/bin/bash
# 股票分析应用监控脚本

echo "🔍 TradingAgents-CN 实时监控"
echo "=============================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 监控函数
monitor_logs() {
    echo -e "${BLUE}📝 实时日志监控 (Ctrl+C 退出)${NC}"
    echo "=============================="
    tail -f /data/code/TradingAgents-CN/logs/tradingagents.log
}

monitor_network() {
    echo -e "${GREEN}🌐 网络连接监控${NC}"
    echo "=============================="
    echo "Streamlit端口状态:"
    ss -tlnp | grep :8501
    echo ""
    echo "当前网络连接:"
    netstat -an | grep :8501 | head -10
}

monitor_process() {
    echo -e "${YELLOW}⚙️  进程状态监控${NC}"
    echo "=============================="
    ps aux | grep -E "(streamlit|python.*app)" | grep -v grep
    echo ""
    echo "内存使用情况:"
    free -h
}

monitor_disk() {
    echo -e "${RED}💾 磁盘使用情况${NC}"
    echo "=============================="
    df -h | grep -E "(/$|/data)"
    echo ""
    echo "日志文件大小:"
    ls -lh /data/code/TradingAgents-CN/logs/
}

show_menu() {
    echo ""
    echo "请选择监控选项:"
    echo "1) 实时日志监控"
    echo "2) 网络连接监控"
    echo "3) 进程状态监控"
    echo "4) 磁盘使用监控"
    echo "5) 综合监控"
    echo "6) 退出"
    echo "=============================="
    read -p "请输入选项 (1-6): " choice
}

# 综合监控
comprehensive_monitor() {
    while true; do
        clear
        echo -e "${BLUE}🔍 TradingAgents-CN 综合监控${NC}"
        echo "时间: $(date)"
        echo "=============================="

        # 进程状态
        echo -e "${GREEN}📊 进程状态${NC}"
        ps aux | grep streamlit | grep -v grep | awk '{print "PID:", $2, "CPU:", $3"%", "MEM:", $4"%", "时间:", $9}'

        # 网络连接
        echo -e "${GREEN}🌐 网络状态${NC}"
        connection_count=$(netstat -an | grep :8501 | wc -l)
        echo "当前连接数: $connection_count"

        # 系统负载
        echo -e "${GREEN}⚙️  系统负载${NC}"
        uptime

        # 内存使用
        echo -e "${GREEN}💾 内存使用${NC}"
        free -h | head -2

        # 最近5条日志
        echo -e "${GREEN}📝 最近日志${NC}"
        tail -5 /data/code/TradingAgents-CN/logs/tradingagents.log | grep -E "(INFO|ERROR|WARNING"

        echo "=============================="
        echo "刷新中... (每5秒刷新, Ctrl+C 退出)"
        sleep 5
    done
}

# 主循环
while true; do
    show_menu
    case $choice in
        1)
            monitor_logs
            ;;
        2)
            monitor_network
            ;;
        3)
            monitor_process
            ;;
        4)
            monitor_disk
            ;;
        5)
            comprehensive_monitor
            ;;
        6)
            echo "退出监控"
            exit 0
            ;;
        *)
            echo "无效选项，请重新选择"
            ;;
    esac
done