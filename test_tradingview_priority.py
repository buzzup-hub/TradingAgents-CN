#!/usr/bin/env python3
"""
快速测试TradingView优先级
不依赖日志系统，直接验证代码逻辑
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/data/code/TradingAgents-CN')

print("=" * 80)
print("  TradingView 优先级测试")
print("=" * 80)
print()

# 测试1: 检查环境变量
print("1️⃣  检查环境变量配置...")
print("-" * 40)

from dotenv import load_dotenv
load_dotenv()

data_source = os.getenv('DEFAULT_CHINA_DATA_SOURCE', 'unknown')
print(f"   DEFAULT_CHINA_DATA_SOURCE = {data_source}")

if data_source == 'tradingview':
    print("   ✅ 环境变量配置正确\n")
else:
    print(f"   ⚠️  环境变量不是tradingview (当前: {data_source})\n")

# 测试2: 检查数据源管理器
print("2️⃣  检查数据源管理器...")
print("-" * 40)

try:
    from tradingagents.dataflows.data_source_manager import get_data_source_manager, ChinaDataSource

    manager = get_data_source_manager()
    current_source = manager.get_current_source()

    print(f"   当前数据源: {current_source.value}")
    print(f"   默认数据源: {manager.default_source.value}")
    print(f"   可用数据源: {[s.value for s in manager.available_sources]}")

    if current_source == ChinaDataSource.TRADINGVIEW:
        print("   ✅ 数据源管理器配置正确\n")
    else:
        print(f"   ⚠️  当前数据源不是TradingView (当前: {current_source.value})\n")

except Exception as e:
    print(f"   ❌ 数据源管理器测试失败: {e}\n")
    import traceback
    traceback.print_exc()

# 测试3: 检查interface.py代码逻辑
print("3️⃣  检查interface.py代码逻辑...")
print("-" * 40)

try:
    with open('/data/code/TradingAgents-CN/tradingagents/dataflows/interface.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查港股函数
    hk_has_tradingview = 'manager.current_source == ChinaDataSource.TRADINGVIEW' in content
    hk_in_function = 'def get_hk_stock_data_unified' in content

    if hk_has_tradingview and hk_in_function:
        print("   ✅ 港股函数包含TradingView优先级检查")
    else:
        print("   ❌ 港股函数缺少TradingView优先级检查")

    # 检查美股函数
    us_has_tradingview = content.count('manager.current_source == ChinaDataSource.TRADINGVIEW') >= 2
    us_in_function = 'def get_stock_data_by_market' in content

    if us_has_tradingview and us_in_function:
        print("   ✅ 美股函数包含TradingView优先级检查")
    else:
        print("   ❌ 美股函数缺少TradingView优先级检查")

    # 统计TradingView检查点
    tradingview_checks = content.count('manager.current_source == ChinaDataSource.TRADINGVIEW')
    print(f"   📊 检测到 {tradingview_checks} 处TradingView优先级检查点\n")

except Exception as e:
    print(f"   ❌ 代码检查失败: {e}\n")

# 测试4: 验证函数调用路径（不实际调用API）
print("4️⃣  验证函数调用路径...")
print("-" * 40)

print("   导入测试函数...")
try:
    from tradingagents.dataflows.interface import (
        get_china_stock_data_unified,
        get_hk_stock_data_unified,
        get_stock_data_by_market
    )
    print("   ✅ 所有统一接口函数导入成功")
    print("      - get_china_stock_data_unified (A股)")
    print("      - get_hk_stock_data_unified (港股)")
    print("      - get_stock_data_by_market (美股)\n")
except Exception as e:
    print(f"   ❌ 函数导入失败: {e}\n")
    import traceback
    traceback.print_exc()

# 测试5: 检查TradingView适配器
print("5️⃣  检查TradingView适配器...")
print("-" * 40)

try:
    from tradingagents.dataflows.tradingview_adapter import get_tradingview_adapter

    adapter = get_tradingview_adapter()
    print(f"   ✅ TradingView适配器初始化成功")
    print(f"      类型: {type(adapter).__name__}")

    # 检查是否有必要的方法
    if hasattr(adapter, 'get_stock_data'):
        print("      ✅ 包含 get_stock_data() 方法")
    else:
        print("      ❌ 缺少 get_stock_data() 方法")

    print()

except Exception as e:
    print(f"   ❌ TradingView适配器测试失败: {e}\n")
    import traceback
    traceback.print_exc()

# 总结
print("=" * 80)
print("  测试总结")
print("=" * 80)
print()

print("✅ 检查完成！")
print()
print("📋 下一步操作:")
print("   1. 如果所有检查都通过，运行: ./verify_tradingview_integration.sh")
print("   2. 选择部署方式（Docker或Streamlit）")
print("   3. 重启后监控日志，验证TradingView是否被实际调用")
print()
print("📊 监控日志命令:")
print("   tail -f logs/tradingagents.log | grep --color=always -E 'TradingView|港股|美股'")
print()
print("🧪 实际测试命令（重启后执行）:")
print("   # A股")
print("   python -c 'from tradingagents.dataflows.interface import get_china_stock_data_unified; print(get_china_stock_data_unified(\"600519\", \"2025-10-01\", \"2025-10-16\"))'")
print()
print("   # 港股")
print("   python -c 'from tradingagents.dataflows.interface import get_hk_stock_data_unified; print(get_hk_stock_data_unified(\"0700.HK\", \"2025-10-01\", \"2025-10-16\"))'")
print()
print("   # 美股")
print("   python -c 'from tradingagents.dataflows.interface import get_stock_data_by_market; print(get_stock_data_by_market(\"AAPL\", \"2025-10-01\", \"2025-10-16\"))'")
print()
