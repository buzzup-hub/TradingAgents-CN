#!/usr/bin/env python3
"""
独立测试：数据库创建和位置
不依赖项目日志系统
"""

import sqlite3
from pathlib import Path

print("=" * 80)
print("  数据库位置和创建测试")
print("=" * 80 + "\n")

# 1. 创建测试数据库
print("1️⃣  创建测试数据库...")

base_dir = Path("data/tradingview")
base_dir.mkdir(parents=True, exist_ok=True)

db_path = base_dir / "tradingview_data.db"

print(f"   数据库路径: {db_path}")
print(f"   绝对路径: {db_path.absolute()}")

# 创建数据库和表
conn = sqlite3.connect(str(db_path))

conn.execute("""
    CREATE TABLE IF NOT EXISTS stock_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL NOT NULL,
        close REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        volume INTEGER NOT NULL,
        amount REAL,
        amplitude REAL,
        change_pct REAL,
        change_amount REAL,
        turnover_rate REAL,
        source TEXT DEFAULT 'tradingview',
        fetched_at TEXT NOT NULL,
        UNIQUE(symbol, date)
    )
""")

conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        data_json TEXT NOT NULL,
        quality_score REAL,
        fetched_at TEXT NOT NULL,
        count INTEGER NOT NULL
    )
""")

# 创建索引
conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_history(symbol, date)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON stock_history(date)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON stock_history(symbol)")

conn.commit()

# 查看表结构
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"\n   ✅ 数据库创建成功!")
print(f"   文件大小: {db_path.stat().st_size} 字节")
print(f"   数据表: {[t[0] for t in tables]}")

# 插入测试数据
from datetime import datetime
test_data = [
    ('600519', '2025-01-20', 1524.0, 1488.0, 1524.49, 1480.0, 50029,
     7490884000.0, 2.92, -2.36, -36.0, 0.40, 'tradingview', datetime.now().isoformat())
]

conn.execute("""
    INSERT OR REPLACE INTO stock_history
    (symbol, date, open, close, high, low, volume, amount,
     amplitude, change_pct, change_amount, turnover_rate, source, fetched_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", test_data[0])

conn.commit()

# 查询数据
cursor = conn.execute("SELECT COUNT(*) FROM stock_history")
count = cursor.fetchone()[0]
print(f"   测试数据: {count}条\n")

conn.close()

# 2. 列出目录结构
print("2️⃣  目录结构:")
print(f"   {base_dir.absolute()}/")
for item in sorted(base_dir.glob("**/*")):
    relative = item.relative_to(base_dir)
    indent = "   " + "  " * (len(relative.parts) - 1)
    if item.is_dir():
        print(f"{indent}📁 {relative}/")
    else:
        size = item.stat().st_size
        print(f"{indent}📄 {relative} ({size} 字节)")

# 3. 检查TradingView原有缓存位置
print("\n3️⃣  检查TradingView原有缓存位置:")
tradingview_paths = [
    Path("/home/ceshi/.tradingview"),
    Path("/home/ceshi/code/TradingAgents-CN/tradingview/data"),
]

for path in tradingview_paths:
    if path.exists():
        print(f"   ✅ {path}")
        db_files = list(path.glob("*.db"))
        if db_files:
            for db in db_files:
                print(f"      📄 {db.name} ({db.stat().st_size} 字节)")
        else:
            print(f"      (无.db文件)")
    else:
        print(f"   ⚠️  {path} (不存在)")

print("\n" + "=" * 80)
print("  测试完成")
print("=" * 80 + "\n")

print("📋 总结:")
print(f"  ✅ 持久化数据库已创建: {db_path.absolute()}")
print(f"  ✅ 包含2个表: stock_history (主数据), raw_data (原始数据)")
print(f"  ✅ 已插入测试数据: {count}条")
print()
print("🎯 你可以使用以下工具查看数据库:")
print(f"  1. DB Browser for SQLite: 打开 {db_path.absolute()}")
print(f"  2. 命令行: sqlite3 {db_path.absolute()}")
print(f"  3. Python代码读取")
print()
