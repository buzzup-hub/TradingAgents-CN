#!/usr/bin/env python3
"""
测试数据库创建和位置验证
"""

import os
import sys
from pathlib import Path

print("=" * 80)
print("  TradingView 数据库位置测试")
print("=" * 80 + "\n")

# 测试1: 持久化管理器数据库
print("1️⃣  测试持久化管理器数据库创建...")
try:
    from tradingagents.dataflows.tradingview_persistence import get_persistence_manager

    persistence = get_persistence_manager()
    db_path = persistence.db_path

    print(f"   数据库路径: {db_path}")
    print(f"   绝对路径: {db_path.absolute()}")
    print(f"   文件存在: {'✅ 是' if db_path.exists() else '❌ 否'}")

    if db_path.exists():
        size = db_path.stat().st_size
        print(f"   文件大小: {size} 字节")

    # 查看统计
    stats = persistence.get_statistics()
    print(f"\n   数据库统计:")
    print(f"     - 股票数量: {stats.get('sqlite', {}).get('symbols', 0)}")
    print(f"     - 总记录数: {stats.get('sqlite', {}).get('records', 0)}")

    print("   ✅ 持久化管理器测试成功\n")

except Exception as e:
    print(f"   ❌ 测试失败: {e}\n")
    import traceback
    traceback.print_exc()

# 测试2: TradingView缓存数据库（如果API服务启动过）
print("\n2️⃣  检查TradingView缓存数据库...")
cache_paths = [
    "data/tradingview_cache.db",
    "/home/ceshi/code/TradingAgents-CN/tradingview/data/tradingview_cache.db",
    str(Path.home() / ".tradingview" / "kline_cache.db"),
    str(Path.home() / ".tradingview" / "tradingview_data.db")
]

found_any = False
for cache_path in cache_paths:
    p = Path(cache_path)
    if p.exists():
        found_any = True
        print(f"   ✅ 找到: {p.absolute()}")
        print(f"      大小: {p.stat().st_size} 字节")
    else:
        print(f"   ⚠️  不存在: {cache_path}")

if not found_any:
    print("\n   💡 提示: TradingView缓存数据库在首次运行API服务时创建")

# 测试3: 查看所有可能的数据目录
print("\n3️⃣  检查数据目录结构...")
data_dirs = [
    "data",
    "data/tradingview",
    str(Path.home() / ".tradingview")
]

for data_dir in data_dirs:
    p = Path(data_dir)
    if p.exists():
        print(f"   ✅ {p.absolute()}")
        # 列出该目录下的文件
        try:
            files = list(p.glob("*"))
            if files:
                print(f"      包含 {len(files)} 个文件/文件夹:")
                for f in files[:5]:  # 只显示前5个
                    print(f"        - {f.name}")
                if len(files) > 5:
                    print(f"        ... 还有 {len(files)-5} 个")
            else:
                print(f"      (空目录)")
        except Exception as e:
            print(f"      无法列出: {e}")
    else:
        print(f"   ⚠️  {data_dir} (不存在)")

print("\n" + "=" * 80)
print("  测试完成")
print("=" * 80 + "\n")

print("📋 总结:")
print("  1. 持久化管理器数据库会在 data/tradingview/ 目录下自动创建")
print("  2. TradingView API缓存会在首次启动服务时创建")
print("  3. 所有数据库都会在首次使用时自动初始化")
print()
