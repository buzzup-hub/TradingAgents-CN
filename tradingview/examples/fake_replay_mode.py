#!/usr/bin/env python3
"""
此示例演示如何使用模拟回放模式，通过过滤数据实现自定义回测

与真实回放模式不同，模拟回放不是使用TradingView的回放功能，
而是通过过滤接收到的数据，只处理特定日期之前的数据，从而模拟回放效果。
这使得您可以使用自己的数据进行回测，而不仅仅依赖于TradingView的回放。
"""
import asyncio
import os
import json
from datetime import datetime, timezone

from ...tradingview import Client

# 过滤器回放日期 - 2022年1月1日
FILTER_DATE = datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000

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
    
    # 创建图表
    chart = tv.create_chart('BINANCE:BTCUSDT', '1D', 10000)
    
    # 定义回调函数
    def on_error(err):
        """错误处理回调"""
        print("错误:", err)
        tv.close()
    
    def on_ready():
        """准备就绪回调"""
        print("图表已准备就绪!")
        print(f"使用模拟回放模式，过滤日期: {datetime.fromtimestamp(FILTER_DATE/1000, tz=timezone.utc).strftime('%Y-%m-%d')}")
    
    def on_update(data):
        """数据更新回调"""
        # 获取蜡烛图数据
        candles = data.get('candles', [])
        if not candles:
            return
            
        # 过滤数据 - 只保留过滤日期之前的数据
        filtered_candles = [
            candle for candle in candles 
            if candle.get('time', 0) <= FILTER_DATE
        ]
        
        if not filtered_candles:
            print("没有找到过滤日期之前的数据")
            return
            
        print(f"原始数据: {len(candles)}个蜡烛图, 过滤后: {len(filtered_candles)}个蜡烛图")
        
        # 显示过滤后的最新数据
        latest = filtered_candles[-1]
        dt = datetime.fromtimestamp(latest.get('time', 0) / 1000, tz=timezone.utc)
        
        print(f"\n模拟回放最新数据 ({dt.strftime('%Y-%m-%d')}):")
        print(f"开盘价: {latest.get('open')}")
        print(f"最高价: {latest.get('high')}")
        print(f"最低价: {latest.get('low')}")
        print(f"收盘价: {latest.get('close')}")
        print(f"成交量: {latest.get('volume')}")
        
        # 如果需要，可以在这里添加模拟交易逻辑
        # ...
        
        # 模拟策略信号示例
        if len(filtered_candles) >= 20:
            # 简单的移动平均线交叉策略示例
            short_ma = sum(c.get('close', 0) for c in filtered_candles[-10:]) / 10
            long_ma = sum(c.get('close', 0) for c in filtered_candles[-20:]) / 20
            
            print(f"10日均线: {short_ma:.2f}")
            print(f"20日均线: {long_ma:.2f}")
            
            # 信号逻辑
            if short_ma > long_ma:
                print("模拟信号: 买入")
            else:
                print("模拟信号: 卖出")
        
        # 演示完成，关闭连接
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