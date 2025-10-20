#!/usr/bin/env python3
"""
此示例创建一个图表并使用用户的所有私有指标
"""
import asyncio
import os
import sys

from ...tradingview import Client, get_private_indicators

async def main():
    """主函数"""
    # 检查是否设置了会话ID和签名
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    # 创建客户端并连接
    client = Client(token=session, signature=signature)
    await client.connect()
    
    # 创建图表
    chart = client.Session.Chart()
    
    # 设置市场
    chart.set_market('BINANCE:BTCEUR', {
        'timeframe': 'D',
    })
    
    # 获取所有私有指标
    print('获取私有指标...')
    indic_list = await get_private_indicators(session, signature)
    
    if not indic_list:
        print('您的账户中没有私有指标')
        await client.end()
        return
    
    print(f'找到 {len(indic_list)} 个私有指标')
    
    # 用于跟踪已加载的指标数量
    loaded_indicators = 0
    total_indicators = len(indic_list)
    
    # 处理每个指标
    for indic in indic_list:
        try:
            # 获取完整指标信息
            print(f'正在加载指标: {indic.name}...')
            private_indic = await indic.get()
            
            # 创建指标研究
            indicator = chart.Study(private_indic)
            
            # 当指标准备好时
            def on_ready():
                nonlocal loaded_indicators
                print(f'指标 {indic.name} 已加载!')
                loaded_indicators += 1
                
                # 当所有指标都加载完成时，退出程序
                if loaded_indicators == total_indicators:
                    print('所有指标已加载，正在关闭...')
                    asyncio.create_task(client.end())
            
            indicator.on_ready(on_ready)
            
            # 当指标数据更新时
            def on_update():
                # 检查是否有数据
                if not indicator.periods:
                    return
                
                print(f'指标 {indic.name} 的绘图值:', indicator.periods[0] if indicator.periods else None)
                
                # 显示策略报告（如果有）
                if indicator.strategy_report:
                    print(f'指标 {indic.name} 的策略报告:', indicator.strategy_report)
            
            indicator.on_update(on_update)
        
        except Exception as e:
            print(f'加载指标 {indic.name} 时出错: {e}')
            loaded_indicators += 1
    
    # 如果没有指标或加载失败，直接退出
    if loaded_indicators == total_indicators:
        await client.end()
    else:
        # 等待最多60秒
        try:
            await asyncio.wait_for(asyncio.sleep(60), timeout=60)
            print('等待超时，正在退出...')
            await client.end()
        except asyncio.CancelledError:
            pass

if __name__ == '__main__':
    asyncio.run(main()) 