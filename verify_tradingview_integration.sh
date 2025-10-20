#!/bin/bash
# TradingView 集成验证和部署脚本
# 用途：验证所有修改已就绪，清理缓存，重启服务，监控日志

set -e  # 遇到错误立即退出

echo "================================================================================"
echo "  TradingView 集成验证和部署脚本"
echo "================================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 工作目录
cd /data/code/TradingAgents-CN

echo -e "${BLUE}📋 步骤1: 验证环境配置${NC}"
echo "----------------------------------------"

# 检查.env文件
if [ ! -f .env ]; then
    echo -e "${RED}❌ 错误: .env文件不存在${NC}"
    exit 1
fi

# 检查DEFAULT_CHINA_DATA_SOURCE配置
DATA_SOURCE=$(grep "^DEFAULT_CHINA_DATA_SOURCE=" .env | cut -d'=' -f2)
if [ "$DATA_SOURCE" == "tradingview" ]; then
    echo -e "${GREEN}✅ 数据源配置正确: DEFAULT_CHINA_DATA_SOURCE=tradingview${NC}"
else
    echo -e "${YELLOW}⚠️  当前数据源: $DATA_SOURCE${NC}"
    echo -e "${YELLOW}   建议设置为: tradingview${NC}"
fi

# 检查TradingView认证信息（可选）
if grep -q "^TV_SESSION=" .env && grep -q "^TV_SIGNATURE=" .env; then
    echo -e "${GREEN}✅ TradingView认证信息已配置${NC}"
else
    echo -e "${YELLOW}⚠️  TradingView认证信息未配置（可选）${NC}"
fi

echo ""
echo -e "${BLUE}📋 步骤2: 验证关键文件修改${NC}"
echo "----------------------------------------"

# 检查interface.py是否包含TradingView优先级代码
if grep -q "manager.current_source == ChinaDataSource.TRADINGVIEW" tradingagents/dataflows/interface.py; then
    echo -e "${GREEN}✅ interface.py包含TradingView优先级逻辑${NC}"

    # 统计TradingView检查点数量
    COUNT=$(grep -c "manager.current_source == ChinaDataSource.TRADINGVIEW" tradingagents/dataflows/interface.py || true)
    echo -e "   检测到 ${GREEN}$COUNT${NC} 处TradingView优先级检查点"
else
    echo -e "${RED}❌ interface.py缺少TradingView优先级逻辑${NC}"
    exit 1
fi

# 检查关键函数
echo ""
echo "检查关键函数修改状态:"
if grep -A 20 "def get_hk_stock_data_unified" tradingagents/dataflows/interface.py | grep -q "TRADINGVIEW"; then
    echo -e "  ${GREEN}✅ get_hk_stock_data_unified() - 港股优先TradingView${NC}"
else
    echo -e "  ${RED}❌ get_hk_stock_data_unified() - 未包含TradingView逻辑${NC}"
fi

if grep -A 30 "def get_stock_data_by_market" tradingagents/dataflows/interface.py | grep -q "TRADINGVIEW"; then
    echo -e "  ${GREEN}✅ get_stock_data_by_market() - 美股优先TradingView${NC}"
else
    echo -e "  ${RED}❌ get_stock_data_by_market() - 未包含TradingView逻辑${NC}"
fi

echo ""
echo -e "${BLUE}📋 步骤3: 清理Python缓存${NC}"
echo "----------------------------------------"

# 清理.pyc文件
PYC_COUNT=$(find . -name "*.pyc" 2>/dev/null | wc -l)
if [ $PYC_COUNT -gt 0 ]; then
    echo -e "找到 ${YELLOW}$PYC_COUNT${NC} 个.pyc文件，正在清理..."
    find . -name "*.pyc" -delete
    echo -e "${GREEN}✅ 已清理所有.pyc文件${NC}"
else
    echo -e "${GREEN}✅ 无需清理.pyc文件${NC}"
fi

# 清理__pycache__目录
PYCACHE_COUNT=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
if [ $PYCACHE_COUNT -gt 0 ]; then
    echo -e "找到 ${YELLOW}$PYCACHE_COUNT${NC} 个__pycache__目录，正在清理..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅ 已清理所有__pycache__目录${NC}"
else
    echo -e "${GREEN}✅ 无需清理__pycache__目录${NC}"
fi

echo ""
echo -e "${BLUE}📋 步骤4: 检查日志目录${NC}"
echo "----------------------------------------"

if [ ! -d "logs" ]; then
    echo -e "${YELLOW}⚠️  logs目录不存在，正在创建...${NC}"
    mkdir -p logs
    echo -e "${GREEN}✅ logs目录已创建${NC}"
else
    echo -e "${GREEN}✅ logs目录存在${NC}"
fi

# 检查日志文件权限
if [ -f "logs/tradingagents.log" ]; then
    if [ -w "logs/tradingagents.log" ]; then
        echo -e "${GREEN}✅ tradingagents.log可写${NC}"
    else
        echo -e "${RED}❌ tradingagents.log不可写，尝试修复权限...${NC}"
        chmod 666 logs/tradingagents.log
    fi
fi

echo ""
echo -e "${BLUE}📋 步骤5: 验证数据目录${NC}"
echo "----------------------------------------"

# 创建TradingView数据目录
if [ ! -d "data/tradingview" ]; then
    echo -e "${YELLOW}⚠️  data/tradingview目录不存在，正在创建...${NC}"
    mkdir -p data/tradingview
    echo -e "${GREEN}✅ data/tradingview目录已创建${NC}"
else
    echo -e "${GREEN}✅ data/tradingview目录存在${NC}"
fi

echo ""
echo -e "${BLUE}📋 步骤6: 部署选项${NC}"
echo "----------------------------------------"
echo ""
echo "请选择部署方式:"
echo "  1) Docker部署 (docker-compose restart)"
echo "  2) Streamlit本地部署 (杀死现有进程并重启)"
echo "  3) 仅验证，不重启"
echo "  4) 退出"
echo ""
read -p "请输入选项 [1-4]: " DEPLOY_OPTION

case $DEPLOY_OPTION in
    1)
        echo ""
        echo -e "${BLUE}🐳 Docker部署${NC}"
        echo "----------------------------------------"

        # 检查docker-compose是否存在
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}❌ docker-compose未安装${NC}"
            exit 1
        fi

        # 检查docker-compose.yml是否存在
        if [ ! -f "docker-compose.yml" ]; then
            echo -e "${RED}❌ docker-compose.yml不存在${NC}"
            exit 1
        fi

        echo "正在重启Docker服务..."
        docker-compose restart

        echo -e "${GREEN}✅ Docker服务已重启${NC}"
        echo ""
        echo -e "${BLUE}📊 查看日志:${NC}"
        echo "  docker-compose logs -f --tail=100 | grep -E 'TradingView|港股|美股'"
        ;;

    2)
        echo ""
        echo -e "${BLUE}🚀 Streamlit本地部署${NC}"
        echo "----------------------------------------"

        # 查找并杀死现有Streamlit进程
        STREAMLIT_PIDS=$(pgrep -f "streamlit run" || true)
        if [ ! -z "$STREAMLIT_PIDS" ]; then
            echo -e "${YELLOW}⚠️  发现现有Streamlit进程: $STREAMLIT_PIDS${NC}"
            echo "正在停止..."
            kill $STREAMLIT_PIDS 2>/dev/null || true
            sleep 2
            echo -e "${GREEN}✅ 已停止现有进程${NC}"
        else
            echo -e "${GREEN}✅ 无运行中的Streamlit进程${NC}"
        fi

        # 启动Streamlit
        echo ""
        echo "正在启动Streamlit..."
        echo -e "${YELLOW}提示: 使用 Ctrl+C 停止服务${NC}"
        echo ""

        cd web
        python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
        ;;

    3)
        echo ""
        echo -e "${GREEN}✅ 验证完成，未重启服务${NC}"
        ;;

    4)
        echo ""
        echo -e "${BLUE}👋 退出${NC}"
        exit 0
        ;;

    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "================================================================================"
echo -e "${GREEN}  部署完成！${NC}"
echo "================================================================================"
echo ""
echo -e "${BLUE}📊 监控TradingView日志输出:${NC}"
echo ""
echo "  tail -f logs/tradingagents.log | grep --color=always -E 'TradingView|港股|美股|SSE:|HKEX:|NASDAQ:'"
echo ""
echo -e "${BLUE}🧪 测试命令:${NC}"
echo ""
echo "  # A股测试 (贵州茅台)"
echo "  python -c 'from tradingagents.dataflows.interface import get_china_stock_data_unified; print(get_china_stock_data_unified(\"600519\", \"2025-10-01\", \"2025-10-16\"))'"
echo ""
echo "  # 港股测试 (腾讯控股)"
echo "  python -c 'from tradingagents.dataflows.interface import get_hk_stock_data_unified; print(get_hk_stock_data_unified(\"0700.HK\", \"2025-10-01\", \"2025-10-16\"))'"
echo ""
echo "  # 美股测试 (Apple)"
echo "  python -c 'from tradingagents.dataflows.interface import get_stock_data_by_market; print(get_stock_data_by_market(\"AAPL\", \"2025-10-01\", \"2025-10-16\"))'"
echo ""
echo -e "${BLUE}📋 预期日志输出:${NC}"
echo ""
echo "  A股: 🔍 TradingView获取数据: SSE:600519"
echo "  港股: 🔄 使用TradingView获取港股数据: 0700.HK"
echo "  美股: 🇺🇸 使用TradingView获取美股数据: AAPL"
echo ""
echo -e "${GREEN}✅ 如果看到以上日志，说明TradingView集成成功！${NC}"
echo ""
