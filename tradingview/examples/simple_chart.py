#!/usr/bin/env python3
"""
此示例创建一个BTCEUR日线图表
"""
import asyncio
import os
import time

from ...tradingview import Client

# export TV_SESSION=b7dc5nugsk5td47u39wiolrj1iy0u544
# export TV_SIGNATURE=v3:goGfCVtvE/NAUTmU4Kk+NhmPgfgIDk9mozUpMgUf77E=

async def main():
    """主函数"""
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    client = Client(
        # 取消注释并设置环境变量以使用用户登录
        token=session,
        signature=signature
    )
    
    # 连接到TradingView
    await client.connect()
    
    chart = client.Session.Chart()  # 初始化Chart会话
    
    # 设置市场
    chart.set_market('BINANCE:BTCEUR', {
        'timeframe': 'D',
    })
    
    # 监听错误（可以避免崩溃）
    def on_error(*err):
        print('图表错误:', *err)
        # 做一些处理...
    
    chart.on_error(on_error)
    
    # 当交易对成功加载时
    def on_symbol_loaded():
        print(f'市场 "{chart.infos.description}" 已加载!')
    
    chart.on_symbol_loaded(on_symbol_loaded)
    
    # 当价格变化时
    def on_update():
        if not chart.periods or not chart.periods[0]:
            return
        print(f'[{chart.infos.description}]: {chart.periods[0].close} {chart.infos.currency_id}')
        # 做一些处理...
    
    chart.on_update(on_update)
    
    # 等待5秒并将市场设置为BINANCE:ETHEUR
    print('\n5秒后将市场设置为BINANCE:ETHEUR...')
    await asyncio.sleep(5)
    
    print('设置市场为BINANCE:ETHEUR...')
    chart.set_market('BINANCE:ETHEUR', {
        'timeframe': 'D',
    })
    
    # 等待10秒并将时间框架设置为15分钟
    print('\n5秒后将时间框架设置为15分钟...')
    await asyncio.sleep(5)
    
    print('设置时间框架为15分钟...')
    chart.set_series('15')
    
    # 等待5秒并将图表类型设置为"Heikin Ashi"
    print('\n5秒后将图表类型设置为"Heikin Ashi"...')
    await asyncio.sleep(5)
    
    # print('设置图表类型为"Heikin Ashi"...')
    # chart.set_market('BINANCE:ETHEUR', {
    #     'timeframe': 'D',
    #     'type': 'HeikinAshi',
    # })
    print('设置图表类型为 OANDA:XAUUSD...')
    chart.set_market('OANDA:XAUUSD', {
        'timeframe': 'D',
    })
    
    # 等待5秒并关闭图表
    print('\n5秒后关闭图表...')
    await asyncio.sleep(5)
    
    print('关闭图表...')
    chart.delete()
    
    # 等待5秒并关闭客户端
    print('\n5秒后关闭客户端...')
    await asyncio.sleep(5)
    
    print('关闭客户端...')
    await client.end()

if __name__ == '__main__':
    asyncio.run(main()) 