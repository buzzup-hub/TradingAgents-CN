#!/usr/bin/env python3
"""
此示例用于获取历史K线数据
可以指定交易对、时间框架以及时间范围
"""
import asyncio
import json
import time
from datetime import datetime
import os
import sys

# 添加项目根目录到系统路径 - 必须在导入tradingview之前
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 导入dotenv和加载环境变量
from dotenv import load_dotenv
load_dotenv()
print('正在从 .env 加载配置...')

# 现在导入tradingview相关模块
from tradingview import Client
from tradingview.chart.session import ChartSession

# python -m tradingview.examples.historical_klines
async def main():
    """主函数"""
    # 创建一个新的TradingView客户端
    # 如需登录账户获取更多数据，请提供session和signat
    
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
    
    # 初始化Chart会话
    chart: ChartSession = client.Session.Chart()
    
    # 设置配置参数
    config = {
        'symbol': 'BINANCE:BTCUSDT',  # 交易对
        'timeframe': '60',           # 时间框架（以分钟为单位，也可以是'D'表示日线）
        'range': 500,                # 获取的K线数量
        'to': int(time.time()),      # 结束时间戳（默认为当前时间）
        # 'from': 1672531200,        # 起始时间戳（可选，如果设置了to和range则不需要）
        'save_to_file': True,        # 是否保存到文件
        'file_name': 'btcusdt_1h_data.json' # 保存的文件名
    }
    
    # 设置市场和参数
    chart.set_market(config['symbol'], {
        'timeframe': config['timeframe'],
        'range': config['range'],
        'to': config['to']
    })
    
    # 处理错误
    def on_error(*err):
        print('获取数据出错:', *err)
        asyncio.create_task(client.end())
    
    chart.on_error(on_error)
    
    # 当交易对加载成功时
    def on_symbol_loaded():
        print(f"交易对 \"{chart.infos.description}\" 已加载成功!")
        print(f"交易所: {chart.infos.exchange}")
        print(f"时间框架: {config['timeframe']}")
        print(f"请求K线数量: {config['range']}")
    
    chart.on_symbol_loaded(on_symbol_loaded)
    
    # 数据更新完成标记
    data_loaded = False
    
    # 当价格数据更新时
    def on_update():
        nonlocal data_loaded
        if data_loaded or not chart.periods or not chart.periods[0]:
            return
        
        print(f"成功获取 {len(chart.periods)} 条K线数据")
        
        # 处理和格式化数据
        kline_data = [{
            'time': period.time,
            'datetime': datetime.fromtimestamp(period.time).isoformat(),
            'open': period.open,
            'high': period.max,
            'low': period.min,
            'close': period.close,
            'volume': period.volume
        } for period in chart.periods]
        
        # 按时间排序（从早到晚）
        kline_data.sort(key=lambda x: x['time'])
        
        # 显示第一条和最后一条数据
        print('第一条数据:', kline_data[0])
        print('最后一条数据:', kline_data[-1])
        
        # 可选：保存到文件
        if config['save_to_file']:
            with open(config['file_name'], 'w', encoding='utf-8') as f:
                json.dump(kline_data, f, indent=2)
            print(f"数据已保存到文件: {config['file_name']}")
        
        # 标记数据已加载，避免重复处理
        data_loaded = True
        
        # 关闭连接
        print('数据获取完成，关闭连接...')
        asyncio.create_task(close_connection())
    
    chart.on_update(on_update)
    
    async def close_connection():
        """关闭连接"""
        await asyncio.sleep(1)
        chart.delete()
        await client.end()
    
    # 获取更长时间范围的数据（可选）
    async def fetch_more_historical_data():
        """获取更多历史数据"""
        print('获取更多历史数据...')
        chart.fetch_more(5)  # 获取更多5个时间段的数据
    
    # 高级用法：添加指标（可选）
    async def add_indicator():
        """添加指标数据"""
        from tradingview import get_indicator
        
        print('添加指标数据...')
        
        # 以EMA指标为例
        ema = await get_indicator('STD;EMA')
        ema.set_option('Length', 14)  # 设置EMA参数
        
        ema_study = chart.Study(ema)
        
        def on_ema_update():
            if not ema_study.periods or not ema_study.periods[0]:
                return
            print('EMA指标数据已更新')
            print('EMA数据示例:', ema_study.periods[0])
        
        ema_study.on_update(on_ema_update)
    
    # 如需获取更多历史数据或添加指标，取消下面的注释
    # await asyncio.sleep(3)
    # await fetch_more_historical_data()
    # await asyncio.sleep(2)
    # await add_indicator()
    
    # 等待连接关闭
    try:
        # 设置超时，防止程序无限等待
        await asyncio.wait_for(asyncio.sleep(60), timeout=60)
    except asyncio.TimeoutError:
        print("操作超时，强制关闭连接")
        chart.delete()
        await client.end()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n程序被中断') 