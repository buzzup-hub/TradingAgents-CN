#!/usr/bin/env python3
"""
测试AKShare数据格式
打印出AKShare获取的各种数据的详细结构
"""

import pandas as pd
import sys
import os

# 直接导入akshare，避免日志权限问题
try:
    import akshare as ak
    print("✅ AKShare导入成功")
except ImportError:
    print("❌ AKShare未安装，请运行: pip install akshare")
    sys.exit(1)

def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_dataframe_info(df, name):
    """打印DataFrame的详细信息"""
    if df is None:
        print(f"❌ {name}: 数据为 None")
        return

    if df.empty:
        print(f"⚠️  {name}: 数据为空")
        return

    print(f"✅ {name}:")
    print(f"   数据行数: {len(df)}")
    print(f"   列数: {len(df.columns)}")
    print(f"\n   列名列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"     {i}. {col} (类型: {df[col].dtype})")

    print(f"\n   数据预览 (前3行):")
    print(df.head(3).to_string())

    print(f"\n   数据类型:")
    print(df.dtypes.to_string())

    print(f"\n   数据统计 (数值列):")
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        print(df[numeric_cols].describe().to_string())
    else:
        print("     无数值列")

def test_akshare_stock_data():
    """测试A股历史数据"""
    print_separator("测试 A股历史数据")

    # 测试贵州茅台
    symbol = "600519"
    start_date = "20250101"
    end_date = "20250131"

    print(f"获取股票: {symbol}")
    print(f"日期范围: {start_date} 至 {end_date}\n")

    try:
        data = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )
        print_dataframe_info(data, "A股历史数据")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def test_akshare_hk_stock_data():
    """测试港股历史数据"""
    print_separator("测试 港股历史数据")

    # 测试腾讯控股
    symbol = "00700"
    start_date = "20250101"
    end_date = "20250131"

    print(f"获取股票: {symbol}")
    print(f"日期范围: {start_date} 至 {end_date}\n")

    try:
        data = ak.stock_hk_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )
        print_dataframe_info(data, "港股历史数据")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def test_akshare_stock_info():
    """测试股票基本信息"""
    print_separator("测试 A股基本信息")

    symbol = "600519"
    print(f"获取股票信息: {symbol}\n")

    try:
        stock_list = ak.stock_info_a_code_name()
        stock_info = stock_list[stock_list['code'] == symbol]

        if not stock_info.empty:
            print(f"✅ 股票基本信息:")
            print(f"   symbol: {symbol}")
            print(f"   name: {stock_info.iloc[0]['name']}")
            print(f"\n完整数据:")
            print_dataframe_info(stock_info, "A股基本信息")
        else:
            print(f"❌ 未找到股票信息")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def test_akshare_hk_stock_info():
    """测试港股基本信息"""
    print_separator("测试 港股基本信息")

    symbol = "00700"
    print(f"获取港股信息: {symbol}\n")

    try:
        spot_data = ak.stock_hk_spot_em()
        matching_stocks = spot_data[spot_data['代码'].str.contains(symbol, na=False)]

        if not matching_stocks.empty:
            stock_info = matching_stocks.iloc[0]
            print(f"✅ 港股基本信息:")
            print(f"   代码: {stock_info.get('代码', 'N/A')}")
            print(f"   名称: {stock_info.get('名称', 'N/A')}")
            print(f"   最新价: {stock_info.get('最新价', 'N/A')}")
            print(f"\n完整数据:")
            print_dataframe_info(matching_stocks, "港股基本信息")
        else:
            print(f"❌ 未找到港股信息")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def test_akshare_financial_data():
    """测试财务数据"""
    print_separator("测试 财务数据")

    symbol = "600519"
    print(f"获取财务数据: {symbol}\n")

    financial_data = {}

    # 1. 主要财务指标
    try:
        print("获取主要财务指标...")
        main_indicators = ak.stock_financial_abstract(symbol=symbol)
        if main_indicators is not None and not main_indicators.empty:
            financial_data['main_indicators'] = main_indicators
            print(f"✅ 成功获取主要财务指标")
    except Exception as e:
        print(f"❌ 主要财务指标获取失败: {e}")

    # 2. 资产负债表
    try:
        print("获取资产负债表...")
        balance_sheet = ak.stock_balance_sheet_by_report_em(symbol=symbol)
        if balance_sheet is not None and not balance_sheet.empty:
            financial_data['balance_sheet'] = balance_sheet
            print(f"✅ 成功获取资产负债表")
    except Exception as e:
        print(f"❌ 资产负债表获取失败: {e}")

    # 3. 利润表
    try:
        print("获取利润表...")
        income_statement = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        if income_statement is not None and not income_statement.empty:
            financial_data['income_statement'] = income_statement
            print(f"✅ 成功获取利润表")
    except Exception as e:
        print(f"❌ 利润表获取失败: {e}")

    # 4. 现金流量表
    try:
        print("获取现金流量表...")
        cash_flow = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        if cash_flow is not None and not cash_flow.empty:
            financial_data['cash_flow'] = cash_flow
            print(f"✅ 成功获取现金流量表")
    except Exception as e:
        print(f"❌ 现金流量表获取失败: {e}")

    # 详细打印每个数据集
    print(f"\n财务数据包含 {len(financial_data)} 个数据集:")
    for key, df in financial_data.items():
        print(f"\n{'─' * 80}")
        print_dataframe_info(df, f"财务数据 - {key}")

def test_akshare_news():
    """测试新闻数据"""
    print_separator("测试 新闻数据")

    symbol = "600519"
    print(f"获取新闻: {symbol}\n")

    try:
        news_df = ak.stock_news_em(symbol=symbol)
        if news_df is not None and not news_df.empty:
            # 限制前5条
            news_df = news_df.head(5)
            print_dataframe_info(news_df, "东方财富新闻")
        else:
            print(f"❌ 未获取到新闻数据")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def main():
    """主函数"""
    print("\n" + "█" * 80)
    print("  AKShare 数据格式测试")
    print("█" * 80)

    # 测试各种数据类型
    try:
        test_akshare_stock_data()
    except Exception as e:
        print(f"❌ A股历史数据测试失败: {e}")

    try:
        test_akshare_hk_stock_data()
    except Exception as e:
        print(f"❌ 港股历史数据测试失败: {e}")

    try:
        test_akshare_stock_info()
    except Exception as e:
        print(f"❌ A股信息测试失败: {e}")

    try:
        test_akshare_hk_stock_info()
    except Exception as e:
        print(f"❌ 港股信息测试失败: {e}")

    try:
        test_akshare_financial_data()
    except Exception as e:
        print(f"❌ 财务数据测试失败: {e}")

    try:
        test_akshare_news()
    except Exception as e:
        print(f"❌ 新闻数据测试失败: {e}")

    print("\n" + "█" * 80)
    print("  测试完成")
    print("█" * 80 + "\n")

if __name__ == "__main__":
    main()
