#!/usr/bin/env python3
"""
此示例测试发送图形数据的指标，如'线条'、'标签'、'矩形'、'表格'、'多边形'等
"""
import asyncio
import os
from pprint import pprint

from ...tradingview import Client, get_indicator

async def main():
    """主函数"""
    # 检查环境变量
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    # 创建客户端
    client = Client(
        token=session,
        signature=signature
    )
    
    # 连接到TradingView
    await client.connect()
    
    # 创建图表
    chart = client.Session.Chart()
    
    # 设置市场
    chart.set_market('BINANCE:BTCEUR', {
        'timeframe': '5',
        'range': 10000,
    })
    
    # 加载指标 - 可以选择内置的Zig_Zag指标或自定义指标
    # 自定义指标例子:
    # indicator = await get_indicator('USER;01efac32df544348810bc843a7515f36')
    # indicator = await get_indicator('PUB;5xi4DbWeuIQrU0Fx6ZKiI2odDvIW9q2j')
    
    # 这里使用内置的Zig_Zag指标
    indicator = await get_indicator('STD;Zig_Zag')
    
    # 创建指标研究
    std = chart.Study(indicator)
    
    # 处理错误
    def on_error(*err):
        print('指标错误:', *err)
    
    std.on_error(on_error)
    
    # 当指标准备好时
    def on_ready():
        print(f"指标 '{std.instance.description}' 已加载！")
    
    std.on_ready(on_ready)
    
    # 当指标数据更新时
    def on_update():
        print('图形数据:')
        pprint(std.graphic)
        
        # 如果有表格数据，可以显示表格信息
        if hasattr(std.graphic, 'tables') and std.graphic.tables:
            print('表格:')
            pprint(std.graphic.tables)
            
            # 如果有单元格数据，可以显示单元格信息
            if hasattr(std.graphic.tables[0], 'cells') and callable(std.graphic.tables[0].cells):
                print('单元格:')
                pprint(std.graphic.tables[0].cells())
        
        # 任务完成，关闭连接
        asyncio.create_task(client.end())
    
    std.on_update(on_update)
    
    # 设置超时，防止程序无限等待
    try:
        await asyncio.wait_for(asyncio.sleep(30), timeout=30)
    except asyncio.TimeoutError:
        print("操作超时，关闭连接")
        await client.end()

if __name__ == '__main__':
    asyncio.run(main()) 