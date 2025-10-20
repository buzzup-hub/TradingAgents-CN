#!/usr/bin/env python3
"""
此示例测试搜索功能，如搜索市场和指标
"""
import asyncio
import json
import sys
from pprint import pprint

from .. import search_market_v3, search_indicator

async def main():
    """主函数"""
    print("===== 测试搜索功能 =====")
    
    # 搜索市场
    print("\n搜索市场: BINANCE:")
    try:
        markets = await search_market_v3('BINANCE:')
        print(f"找到 {len(markets)} 个市场:")
        
        # 显示前5个结果
        for i, market in enumerate(markets[:5], 1):
            print(f"{i}. {market.id} - {market.description} ({market.type})")
        
        if len(markets) > 5:
            print(f"...以及更多 {len(markets) - 5} 个市场")
        
        # 搜索特定交易对
        if markets:
            market_name = 'BTCUSDT'
            print(f"\n搜索特定交易对: {market_name}")
            
            try:
                btc_markets = await search_market_v3(f'BINANCE:{market_name}')
                
                if btc_markets:
                    market = btc_markets[0]
                    print(f"找到交易对: {market.id}")
                    print(f"描述: {market.description}")
                    print(f"交易所: {market.exchange}")
                    print(f"类型: {market.type}")
                    
                    # 获取技术分析数据
                    print("\n获取技术分析数据...")
                    try:
                        ta_data = await market.get_ta()
                        if ta_data:
                            print("技术分析结果:")
                            pprint(ta_data)
                        else:
                            print("无法获取技术分析数据")
                    except Exception as e:
                        print(f"获取技术分析数据时出错: {str(e)}")
                else:
                    print(f"未找到匹配的交易对: {market_name}")
            except Exception as e:
                print(f"搜索特定交易对时出错: {str(e)}")
    except Exception as e:
        print(f"搜索市场时出错: {str(e)}")
    
    # 搜索指标
    print("\n搜索指标: RSI")
    try:
        indicators = await search_indicator('RSI')
        print(f"找到 {len(indicators)} 个指标:")
        
        # 显示前5个结果
        for i, indicator in enumerate(indicators[:5], 1):
            print(f"{i}. {indicator.name} - 作者: {indicator.author['username']} - 类型: {indicator.type}")
        
        if len(indicators) > 5:
            print(f"...以及更多 {len(indicators) - 5} 个指标")
        
        # 搜索其他类型的指标
        print("\n搜索指标: MACD")
        try:
            macd_indicators = await search_indicator('MACD')
            print(f"找到 {len(macd_indicators)} 个MACD相关指标")
            
            # 展示内置指标和自定义指标的区别
            print("\n指标分类:")
            builtin_count = sum(1 for ind in indicators if ind.author['username'] == '@TRADINGVIEW@')
            custom_count = len(indicators) - builtin_count
            print(f"内置指标: {builtin_count}")
            print(f"自定义指标: {custom_count}")
        except Exception as e:
            print(f"搜索MACD指标时出错: {str(e)}")
    except Exception as e:
        print(f"搜索RSI指标时出错: {str(e)}")
        print(f"错误类型: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n程序被中断')
        sys.exit(0)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 