#!/usr/bin/env python3
"""
此示例同步获取3个指标的数据
"""
import asyncio
import os

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
    
    # 获取指标数据的函数
    async def get_indicator_data(indicator):
        """获取指标数据"""
        # 创建图表
        chart = client.Session.Chart()
        chart.set_market('BINANCE:DOTUSDT')
        
        # 创建指标研究
        study = chart.Study(indicator)
        
        print(f'获取 "{indicator.description}" 数据...')
        
        # 使用Future等待指标更新
        future = asyncio.Future()
        
        def on_update():
            if not future.done():
                future.set_result(study.periods)
                print(f'"{indicator.description}" 已完成!')
        
        study.on_update(on_update)
        
        # 等待指标数据更新
        return await future
    
    # 主程序
    print('获取所有指标...')
    
    # 定义要获取的指标ID
    indicator_ids = [
        'PUB;3lEKXjKWycY5fFZRYYujEy8fxzRRUyF3',
        'PUB;5nawr3gCESvSHQfOhrLPqQqT4zM23w3X',
        'PUB;vrOJcNRPULteowIsuP6iHn3GIxBJdXwT'
    ]
    
    # 获取指标数据
    indicators = []
    for indic_id in indicator_ids:
        try:
            # 获取指标定义
            indicator = await get_indicator(indic_id)
            indicators.append(indicator)
        except Exception as e:
            print(f'获取指标 {indic_id} 失败: {e}')
    
    # 同步获取所有指标数据
    indic_data = await asyncio.gather(*[get_indicator_data(indicator) for indicator in indicators])
    
    # 显示结果
    print('指标数据:')
    for i, data in enumerate(indic_data):
        print(f'指标 {i+1}: {len(data)} 条数据')
        if data:
            print(f'示例数据: {data[0]}')
    
    print('全部完成!')
    
    # 关闭客户端
    await client.end()

if __name__ == '__main__':
    asyncio.run(main()) 