#!/usr/bin/env python3
"""
此示例演示如何使用自定义时间框架
"""
import asyncio
import os
import json
from pprint import pprint

from ...tradingview import Client

async def main():
    """主函数"""
    # 检查环境变量
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    # 创建客户端
    tv = Client(session, signature)
    
    # 连接到TradingView
    await tv.connect()
    
    # 创建图表并使用自定义时间框架
    chart = tv.create_chart(
        'BINANCE:BTCUSDT',
        # 使用自定义时间框架：10分钟
        'S10', 
        5000
    )
    
    # 定义回调函数
    def on_error(err):
        """错误处理回调"""
        print("错误:", err)
        tv.close()
    
    def on_ready():
        """准备就绪回调"""
        print("图表已准备就绪!")
        
        # 打印可用的自定义时间框架
        print("\n可用的自定义时间框架:")
        print("- 秒级: S5 (5秒), S10 (10秒), S15 (15秒), etc.")
        print("- 分钟级: 1 (1分钟), 3, 5, 10, 15, 30, 45, etc.")
        print("- 小时级: 60 (1小时), 120 (2小时), 180 (3小时), 240 (4小时), etc.")
        print("- 天级: 1D (1天), 2D, 3D, etc.")
        print("- 周级: 1W (1周), 2W, etc.")
        print("- 月级: 1M (1月), etc.")
        print("- 年级: 12M (1年), etc.")
    
    def on_update(data):
        """数据更新回调"""
        # 获取蜡烛图数据
        candles = data.get('candles', [])
        if candles:
            # 显示最后3个蜡烛图数据
            print(f"获取到{len(candles)}个蜡烛图数据(10分钟时间框架)")
            print("最后3个蜡烛图数据:")
            for candle in candles[-3:]:
                print(json.dumps(candle, indent=2))
            # 关闭连接
            tv.close()
            
    # 设置回调函数
    chart.on_error = on_error
    chart.on_ready = on_ready
    chart.on_update = on_update
    
    # 创建图表
    chart.create()
    
    # 超时处理
    await asyncio.sleep(30)
    if tv.connected:
        print("操作超时")
        tv.close()

if __name__ == '__main__':
    asyncio.run(main()) 