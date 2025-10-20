#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试股票API返回数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_stock_api():
    """测试股票API并显示完整的返回数据"""

    print("=" * 60)
    print("🔍 股票API完整返回数据测试")
    print("=" * 60)

    try:
        # 尝试导入API
        from tradingagents.api.stock_api import get_stock_info, get_all_stocks, check_service_status

        print("✅ 成功导入股票API")
        print()

        # 1. 检查服务状态
        print("📊 1. 服务状态:")
        status = check_service_status()
        print(f"   服务状态: {status}")
        print()

        # 2. 测试单个股票查询
        print("🔍 2. 单个股票查询 (000001):")
        print("-" * 40)
        result = get_stock_info('000001')
        print("完整返回数据:")
        print(result)
        print()
        print("数据类型:", type(result))
        print("数据长度:", len(str(result)))
        print()

        # 3. 测试股票搜索
        print("🔍 3. 股票搜索 ('平安'):")
        print("-" * 40)
        search_results = search_stocks('平安')
        print("完整返回数据:")
        print(search_results)
        print()
        print("结果类型:", type(search_results))
        if isinstance(search_results, list):
            print("结果数量:", len(search_results))
        print()

        # 4. 测试获取所有股票 (只取前2个)
        print("🔍 4. 获取所有股票 (前2个):")
        print("-" * 40)
        all_stocks = get_all_stocks()
        if isinstance(all_stocks, list) and len(all_stocks) > 0:
            print("完整返回数据 (前2个):")
            for i, stock in enumerate(all_stocks[:2], 1):
                print(f"  股票 {i}:")
                print(f"    {stock}")
                print()
        else:
            print("返回数据:", all_stocks)

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("尝试使用备用方法...")

        # 备用方法：直接调用数据服务
        try:
            from tradingagents.dataflows.stock_data_service import get_stock_data_service

            service = get_stock_data_service()
            print("✅ 成功创建股票数据服务")

            result = service.get_stock_basic_info('000001')
            print("🔍 股票000001的完整返回数据:")
            print(result)
            print()
            print("数据类型:", type(result))

        except Exception as e2:
            print(f"❌ 备用方法也失败: {e2}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stock_api()