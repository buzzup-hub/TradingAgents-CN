#!/usr/bin/env python3
"""
此示例测试内置指标，如基于成交量的指标
"""
import asyncio
import os
import time

from ...tradingview import Client, BuiltInIndicator

async def main():
    """主函数"""
    # 创建成交量分布图指标
    volume_profile = BuiltInIndicator('VbPFixed@tv-basicstudies-241!')
    
    # 检查是否需要认证
    need_auth = volume_profile.type not in [
        'VbPFixed@tv-basicstudies-241',
        'VbPFixed@tv-basicstudies-241!',
        'Volume@tv-basicstudies-241',
    ]
    
    if need_auth and (not os.environ.get('TV_SESSION') or not os.environ.get('TV_SIGNATURE')):
        raise ValueError('请设置您的sessionid和signature环境变量')
    
    # 创建客户端
    client = Client(
        token=os.environ.get('TV_SESSION') if need_auth else None,
        signature=os.environ.get('TV_SIGNATURE') if need_auth else None
    )
    
    # 连接到TradingView
    await client.connect()
    
    # 创建图表
    chart = client.Session.Chart()
    
    # 设置市场
    chart.set_market('BINANCE:BTCEUR', {
        'timeframe': '60',
        'range': 1,
    })
    
    # 根据指标类型设置必要的选项
    volume_profile.set_option('first_bar_time', int(time.time()) - 10**8)
    # 对于某些指标，可能需要其他选项
    # volume_profile.set_option('first_visible_bar_time', int(time.time()) - 10**8)
    
    # 创建研究
    vol = chart.Study(volume_profile)
    
    # 处理更新
    def on_update():
        # 过滤并处理成交量分布图数据
        horiz_hists = [h for h in vol.graphic.horizHists if h.lastBarTime == 0]
        horiz_hists.sort(key=lambda h: h.priceHigh, reverse=True)
        
        for h in horiz_hists:
            # 计算价格中点并显示成交量条形图
            mid_price = round((h.priceHigh + h.priceLow) / 2)
            up_vol = '_' * int(h.rate[0] / 3)
            down_vol = '_' * int(h.rate[1] / 3)
            print(f"~ {mid_price} € : {up_vol}{down_vol}")
        
        # 任务完成，关闭连接
        asyncio.create_task(client.end())
    
    vol.on_update(on_update)
    
    # 设置超时，防止程序无限等待
    try:
        await asyncio.wait_for(asyncio.sleep(30), timeout=30)
    except asyncio.TimeoutError:
        print("操作超时，强制关闭连接")
        await client.end()

if __name__ == '__main__':
    asyncio.run(main()) 