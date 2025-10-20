#!/usr/bin/env python3
"""
杂项请求模块使用示例
"""
import asyncio
import json
from pprint import pprint

from ..misc import (
    get_ta,
    search_market_v3,
    search_indicator,
    get_indicator
)

async def main():
    """主函数"""
    print("========== 搜索市场 ==========")
    results = await search_market_v3("BINANCE:BTCUSDT")
    if results:
        market = results[0]
        print(f"找到市场: {market.id} - {market.description}")
        
        print("\n========== 获取技术分析 ==========")
        ta_data = await get_ta(market.id)
        pprint(ta_data)
    
    print("\n========== 搜索指标 ==========")
    indicators = await search_indicator("RSI")
    
    if indicators:
        indicator = indicators[0]
        print(f"找到指标: {indicator.name} 作者: {indicator.author['username']}")
        
        print("\n========== 获取指标详情 ==========")
        try:
            indicator_detail = await get_indicator(indicator.id, indicator.version)
            print(f"指标ID: {indicator_detail.pineId}")
            print(f"版本: {indicator_detail.pineVersion}")
            print(f"描述: {indicator_detail.description}")
            print(f"输入参数数量: {len(indicator_detail.inputs)}")
            print(f"绘图数量: {len(indicator_detail.plots)}")
        except Exception as e:
            print(f"获取指标详情失败: {e}")
    
if __name__ == "__main__":
    asyncio.run(main()) 