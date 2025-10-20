#!/usr/bin/env python3
"""
此示例演示如何使用回放模式查看历史数据
"""
import asyncio
import os
import json
from datetime import datetime, timezone

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
    
    # 创建图表
    chart = tv.create_chart('BINANCE:BTCUSDT', '1D', 5000)
    
    # 定义回调函数
    def on_error(err):
        """错误处理回调"""
        print("错误:", err)
        tv.close()
    
    def on_ready():
        """准备就绪回调"""
        print("图表已准备就绪!")
        print("启用回放模式...")
        
        # 启用回放模式 - 设置为2021年1月1日
        target_time = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp())
        chart.set_replay_mode(True, target_time)
    
    def on_update(data):
        """数据更新回调"""
        # 获取蜡烛图数据
        candles = data.get('candles', [])
        if not candles:
            return
            
        # 获取回放状态
        replay_status = data.get('replay')
        if replay_status:
            print(f"\n回放状态: {json.dumps(replay_status, indent=2)}")
            
            # 是否在回放模式
            is_replay = replay_status.get('active', False)
            if is_replay:
                current_time = replay_status.get('ts')
                if current_time:
                    dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
                    print(f"当前回放时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 显示最新蜡烛图数据
        print(f"获取到{len(candles)}个蜡烛图数据")
        print("最新蜡烛图数据:")
        latest = candles[-1]
        dt = datetime.fromtimestamp(latest.get('time', 0) / 1000, tz=timezone.utc)
        print(f"时间: {dt.strftime('%Y-%m-%d')}")
        print(f"开盘价: {latest.get('open')}")
        print(f"最高价: {latest.get('high')}")
        print(f"最低价: {latest.get('low')}")
        print(f"收盘价: {latest.get('close')}")
        print(f"成交量: {latest.get('volume')}")
        
        # 回放动作 - 每3秒前进一步
        # 注意：这仅作为演示，实际应用中可能需要根据具体逻辑控制回放
        asyncio.create_task(replay_step(chart))
            
    # 设置回调函数
    chart.on_error = on_error
    chart.on_ready = on_ready
    chart.on_update = on_update
    
    # 创建图表
    chart.create()
    
    # 超时处理
    await asyncio.sleep(60)
    if tv.connected:
        print("操作超时")
        tv.close()

async def replay_step(chart):
    """执行回放步骤"""
    await asyncio.sleep(3)
    if chart.session and chart.session.client.connected:
        print("\n前进到下一个时间点...")
        chart.replay_step()

if __name__ == '__main__':
    asyncio.run(main()) 