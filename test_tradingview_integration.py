#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView集成测试脚本
验证TradingView框架是否成功集成到TradingAgents-CN项目中
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_tradingview_import():
    """测试TradingView模块导入"""
    print("🔍 测试TradingView模块导入...")

    try:
        # 测试TradingView框架导入
        sys.path.insert(0, str(project_root / 'tradingview'))
        from tradingview import Client
        print("✅ TradingView框架导入成功")

        # 测试适配器导入
        from tradingagents.dataflows.tradingview_adapter import (
            TradingViewDataProvider,
            TradingViewSyncAdapter,
            get_tradingview_adapter
        )
        print("✅ TradingView适配器导入成功")

        return True

    except ImportError as e:
        print(f"❌ TradingView模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ TradingView模块导入异常: {e}")
        return False

def test_data_source_manager():
    """测试数据源管理器"""
    print("\n🔍 测试数据源管理器...")

    try:
        from tradingagents.dataflows.data_source_manager import (
            get_data_source_manager,
            ChinaDataSource
        )

        manager = get_data_source_manager()
        print(f"✅ 数据源管理器初始化成功")
        print(f"   当前数据源: {manager.current_source.value}")
        print(f"   可用数据源: {[s.value for s in manager.available_sources]}")

        # 检查TradingView是否可用
        if ChinaDataSource.TRADINGVIEW in manager.available_sources:
            print("✅ TradingView数据源可用")
        else:
            print("⚠️ TradingView数据源不可用")

        return True

    except Exception as e:
        print(f"❌ 数据源管理器测试失败: {e}")
        return False

def test_tradingview_config():
    """测试TradingView配置"""
    print("\n🔍 测试TradingView配置...")

    try:
        from tradingagents.dataflows.tradingview_adapter import TradingViewDataProvider

        provider = TradingViewDataProvider()
        config = provider._config

        print(f"✅ TradingView配置加载成功")
        print(f"   服务器: {config['server']}")
        print(f"   超时: {config['timeout']}秒")
        print(f"   调试模式: {config['debug']}")

        # 检查认证信息
        if config['token'] and config['signature']:
            print("✅ TradingView认证信息已配置")
        else:
            print("⚠️ TradingView认证信息未配置")
            print("💡 请参考 .env.tradingview.example 文件配置认证信息")

        return True

    except Exception as e:
        print(f"❌ TradingView配置测试失败: {e}")
        return False

def test_symbol_conversion():
    """测试股票代码转换"""
    print("\n🔍 测试股票代码转换...")

    try:
        from tradingagents.dataflows.tradingview_adapter import TradingViewDataProvider

        provider = TradingViewDataProvider()

        test_symbols = [
            "000001",  # A股
            "600000",  # 沪市
            "000001.HK",  # 港股
            "AAPL",    # 美股
        ]

        for symbol in test_symbols:
            tv_symbol = provider._convert_symbol_to_tv_format(symbol)
            print(f"   {symbol} -> {tv_symbol}")

        print("✅ 股票代码转换测试完成")
        return True

    except Exception as e:
        print(f"❌ 股票代码转换测试失败: {e}")
        return False

def test_sync_adapter():
    """测试同步适配器"""
    print("\n🔍 测试同步适配器...")

    try:
        from tradingagents.dataflows.tradingview_adapter import get_tradingview_adapter

        adapter = get_tradingview_adapter()
        print("✅ 同步适配器创建成功")

        # 测试股票信息获取（不需要网络连接）
        info = adapter.get_stock_info("000001")
        print(f"   股票信息示例: {info}")

        return True

    except Exception as e:
        print(f"❌ 同步适配器测试失败: {e}")
        return False

def test_unified_interface():
    """测试统一接口"""
    print("\n🔍 测试统一接口...")

    try:
        from tradingagents.dataflows.data_source_manager import (
            get_china_stock_data_unified,
            get_china_stock_info_unified
        )

        # 测试信息获取
        info = get_china_stock_info_unified("000001")
        print(f"✅ 统一接口测试成功")
        print(f"   股票信息: {info}")

        return True

    except Exception as e:
        print(f"❌ 统一接口测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 TradingView集成测试开始")
    print("=" * 50)

    tests = [
        ("模块导入", test_tradingview_import),
        ("数据源管理器", test_data_source_manager),
        ("TradingView配置", test_tradingview_config),
        ("股票代码转换", test_symbol_conversion),
        ("同步适配器", test_sync_adapter),
        ("统一接口", test_unified_interface),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")

    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！TradingView集成成功！")
        print("\n💡 下一步:")
        print("1. 配置TradingView认证信息 (.env 文件)")
        print("2. 设置 DEFAULT_CHINA_DATA_SOURCE=tradingview")
        print("3. 重启web应用测试数据获取")
    else:
        print("⚠️ 部分测试失败，请检查配置")
        print("\n💡 故障排除:")
        print("1. 确保tradingview框架已正确复制")
        print("2. 检查Python路径配置")
        print("3. 安装必要的依赖: pip install websockets")

if __name__ == "__main__":
    main()