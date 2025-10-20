#!/usr/bin/env python3
"""
此示例演示如何获取特定时间范围的K线数据
"""
import asyncio
import os
import json
from datetime import datetime, timezone, timedelta

from tradingview import Client


async def main():
    """主函数"""
    # 检查环境变量
    session = os.environ.get('TV_SESSION', "b7dc5nugsk5td47u39wiolrj1iy0u544")
    signature = os.environ.get('TV_SIGNATURE', "v3:goGfCVtvE/NAUTmU4Kk+NhmPgfgIDk9mozUpMgUf77E=")
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    # 创建客户端 - 修正初始化方式
    client = Client(token=session, signature=signature)
    
    # 连接到TradingView
    await client.connect()
    
    # 定义时间范围 - 2022年1月1日到2022年1月31日
    # 时间戳（秒）
    from_date = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp())
    to_date = int(datetime(2022, 1, 31, tzinfo=timezone.utc).timestamp())
    
    print(f"获取数据范围: ")
    print(f"  从: {datetime.fromtimestamp(from_date, tz=timezone.utc).strftime('%Y-%m-%d')}")
    print(f"  到: {datetime.fromtimestamp(to_date, tz=timezone.utc).strftime('%Y-%m-%d')}")
    
    # 创建图表 - 使用Session.Chart方式
    chart = client.Session.Chart()
    
    # 设置市场和参数
    chart.set_market('BINANCE:BTCUSDT', {
        'timeframe': '1D',
        'range': 5000,
        'from': from_date,
        'to': to_date
    })
    
    # 数据加载完成标记
    data_loaded = False
    
    # 定义回调函数
    def on_error(*err):
        """错误处理回调"""
        print("错误:", *err)
        asyncio.create_task(client.end())
    
    def on_symbol_loaded():
        """准备就绪回调"""
        print("图表已准备就绪!")
        print(f"交易对: {chart.infos.description}")
    
    def on_update():
        """数据更新回调"""
        nonlocal data_loaded
        if data_loaded or not chart.periods:
            return
            
        candles = chart.periods
        print(f"获取: {(candles)}")
        print(f"获取到{len(candles)}个K线数据")
        
        # 检查数据时间范围
        if candles:
            first_candle = candles[0]
            last_candle = candles[-1]
            
            first_time = datetime.fromtimestamp(first_candle.time, tz=timezone.utc)
            last_time = datetime.fromtimestamp(last_candle.time, tz=timezone.utc)
            
            print(f"\n数据时间范围:")
            print(f"  第一个K线: {first_time.strftime('%Y-%m-%d')}")
            print(f"  最后一个K线: {last_time.strftime('%Y-%m-%d')}")
            
            # 验证数据是否在请求的时间范围内
            is_in_range = (
                first_candle.time >= from_date and 
                last_candle.time <= to_date
            )
            
            if is_in_range:
                print("数据在请求的时间范围内")
            else:
                print("警告: 数据不完全在请求的时间范围内")
        
        # 数据处理示例 - 计算周期内最高价和最低价
        if candles:
            highs = [candle.high for candle in candles]
            lows = [candle.low for candle in candles]
            
            max_price = max(highs) if highs else 0
            min_price = min(lows) if lows else 0
            
            print(f"\n周期内最高价: {max_price}")
            print(f"周期内最低价: {min_price}")
            print(f"价格波动范围: {max_price - min_price}")
            print(f"波动百分比: {((max_price - min_price) / min_price * 100):.2f}%")
        
        # 标记数据已加载
        data_loaded = True
        
        # 关闭连接
        asyncio.create_task(client.end())
            
    # 设置回调函数
    chart.on_error(on_error)
    chart.on_symbol_loaded(on_symbol_loaded)
    chart.on_update(on_update)
    
    # 超时处理
    try:
        await asyncio.wait_for(asyncio.sleep(30), timeout=30)
        if not data_loaded:
            print("操作超时")
            await client.end()
    except asyncio.TimeoutError:
        print("操作超时")
        await client.end()

if __name__ == '__main__':
    asyncio.run(main()) 