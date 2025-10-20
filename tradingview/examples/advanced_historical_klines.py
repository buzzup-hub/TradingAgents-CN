#!/usr/bin/env python3
"""
高级历史K线数据获取工具
支持命令行参数、自定义时间范围和多种数据导出格式

使用示例：
python advanced_historical_klines.py --symbol=BINANCE:BTCUSDT --timeframe=60 --days=30
python advanced_historical_klines.py --symbol=NASDAQ:AAPL --timeframe=D --from=2023-01-01 --to=2023-12-31


python -m tradingview.examples.advanced_historical_klines --symbol=BINANCE:BTCUSDT --timeframe=60 --days=7 --debug
"""
import asyncio
import argparse
import json
import csv
import os
import sys
import time
from datetime import datetime
from pprint import pprint

# 添加项目根目录到系统路径 - 必须在导入tradingview之前
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 导入dotenv并加载环境变量
from dotenv import load_dotenv
load_dotenv()
print('正在从 .env 加载配置...')

# 导入tradingview模块
from tradingview import Client, get_indicator

# 调试模式
DEBUG = True

def debug_print(*args):
    """调试打印函数"""
    if DEBUG:
        print("[调试]", *args)

# 解析命令行参数
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='高级历史K线数据获取工具')
    parser.add_argument('--symbol', type=str, default='BINANCE:BTCUSDT', help='交易对 (例如: BINANCE:BTCUSDT)')
    parser.add_argument('--timeframe', type=str, default='60', help='时间框架 (例如: 60为1小时, D为日线)')
    parser.add_argument('--range', type=int, default=500, help='获取的K线数量')
    parser.add_argument('--output', type=str, default='data', help='输出目录')
    parser.add_argument('--format', type=str, default='json', choices=['json', 'csv'], help='输出格式')
    parser.add_argument('--file', type=str, help='输出文件名 (不包含扩展名)')
    parser.add_argument('--indicators', type=str, default='false', choices=['true', 'false'], help='是否包含指标数据')
    parser.add_argument('--days', type=int, help='获取最近多少天的数据')
    parser.add_argument('--from', dest='from_date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--to', dest='to_date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--token', type=str, help='TradingView会话ID')
    parser.add_argument('--signature', type=str, help='TradingView签名')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    return parser.parse_args()

# 处理日期参数
def process_date_params(args):
    """处理日期相关参数"""
    config = {}
    
    # 如果指定了天数
    if args.days:
        config['to'] = int(time.time())
        config['from'] = config['to'] - (args.days * 86400)
    else:
        # 如果指定了具体的开始/结束日期
        if args.from_date:
            config['from'] = int(datetime.strptime(args.from_date, '%Y-%m-%d').timestamp())
        
        if args.to_date:
            config['to'] = int(datetime.strptime(args.to_date, '%Y-%m-%d').timestamp())
        else:
            config['to'] = int(time.time())
    
    return config

async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置调试模式
    global DEBUG
    DEBUG = args.debug
    
    # 处理日期参数
    date_config = process_date_params(args)
    
    # 合并所有配置
    config = {
        'symbol': args.symbol,
        'timeframe': args.timeframe,
        'range': args.range,
        'output_dir': args.output,
        'format': args.format,
        'include_indicators': args.indicators.lower() == 'true',
        'file_name': args.file,
        'token': args.token,
        'signature': args.signature,
        **date_config
    }
    
    # 如果未指定文件名，生成一个默认文件名
    if not config['file_name']:
        symbol = config['symbol'].replace(':', '_')
        timeframe = config['timeframe']
        date_str = datetime.now().strftime('%Y-%m-%d')
        config['file_name'] = f"{symbol}_{timeframe}_{date_str}"
    
    # 确保输出目录存在
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # 显示配置信息
    print('=== 历史K线数据获取工具 ===')
    print('配置信息:')
    print(f"交易对: {config['symbol']}")
    print(f"时间框架: {config['timeframe']}")
    if 'from' in config:
        print(f"开始时间: {datetime.fromtimestamp(config['from']).strftime('%Y-%m-%d %H:%M:%S')}")
    if 'to' in config:
        print(f"结束时间: {datetime.fromtimestamp(config['to']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"输出格式: {config['format']}")
    print(f"输出文件: {os.path.join(config['output_dir'], config['file_name'] + '.' + config['format'])}")
    print('============================')

    # 从环境变量或参数获取认证信息
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    # 如果环境变量中没有，则使用命令行参数
    if not session and config['token']:
        session = config['token']
    if not signature and config['signature']:
        signature = config['signature']
    
    # 检查是否有足够的认证信息
    if not session or not signature:
        print("错误: 需要提供TradingView的认证信息。")
        print("请设置环境变量TV_SESSION和TV_SIGNATURE，或者使用--token和--signature参数。")
        return
    
    print(f"使用Token: {session}")
    print(f"使用Signature: {signature}")
    
    try:
        # 创建客户端 - 修改为使用命名参数
        debug_print("正在创建TradingView客户端...")
        client = Client(
            token=session,
            signature=signature,
            DEBUG=DEBUG
        )
        
        # 连接到TradingView
        debug_print("正在连接到TradingView服务器...")
        await client.connect()
        debug_print("连接成功！")
        
        # 创建Chart会话
        debug_print("创建Chart会话...")
        chart = client.Session.Chart()
        
        # 指标数据存储
        indicators_data = {}
        
        # 处理错误
        def on_error(*err):
            print('错误:', *err)
            asyncio.create_task(client.end())
            
        chart.on_error(on_error)
        
        # 设置超时任务 - 减少超时时间以便更快发现问题
        timeout_task = asyncio.create_task(
            asyncio.sleep(90)  # 减少超时时间为90秒
        )
        
        # 确保WebSocket连接已经建立
        debug_print("等待WebSocket连接稳定...")
        await asyncio.sleep(2)
        
        # 设置市场
        market_params = {
            'timeframe': config['timeframe'],
            'range': config['range']
        }
        
        # 添加时间范围参数
        if 'to' in config:
            market_params['to'] = config['to']
        if 'from' in config:
            market_params['from'] = config['from']
        
        debug_print(f"设置市场参数: {market_params}")
        
        # 使用set_market方法 - 修改为使用market_params
        debug_print(f"设置交易对: {config['symbol']}")
        chart.set_market(config['symbol'], market_params)
        
        # 确保有足够的时间给set_market创建异步任务
        await asyncio.sleep(1)
        
        # 数据加载完成标记
        data_loaded = False
        
        # 当交易对成功加载时
        def on_symbol_loaded():
            debug_print("交易对加载成功！")
            print(f"交易对 \"{chart.infos.description}\" 数据加载中...")
            
            # 如果需要添加指标
            if config['include_indicators']:
                asyncio.create_task(add_indicators())
        
        chart.on_symbol_loaded(on_symbol_loaded)
        
        # 当数据更新时
        def on_update():
            nonlocal data_loaded
            if data_loaded:
                return
                
            # 检查数据有效性
            if not hasattr(chart, 'periods') or not chart.periods:
                debug_print("等待数据...")
                return
                
            print(f"获取到 {len(chart.periods)} 条K线数据")
            
            try:
                # 处理数据，增加异常处理
                kline_data = []
                for period in chart.periods:
                    try:
                        # 确保所有必要属性存在
                        candle = {
                            'time': getattr(period, 'time', 0),
                            'datetime': datetime.fromtimestamp(getattr(period, 'time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                            'open': getattr(period, 'open', 0),
                            'high': getattr(period, 'max', 0),
                            'low': getattr(period, 'min', 0),
                            'close': getattr(period, 'close', 0),
                            'volume': getattr(period, 'volume', 0)
                        }
                        kline_data.append(candle)
                    except Exception as e:
                        print(f"处理K线数据时出错: {e}")
                        continue
                        
                # 如果没有有效数据，返回
                if not kline_data:
                    print("没有获取到有效数据，继续等待...")
                    return
                    
                # 按时间排序（从早到晚）
                kline_data.sort(key=lambda x: x['time'])
                
                # 显示第一条和最后条数据的时间范围
                if kline_data:
                    print(f"数据时间范围: {kline_data[0]['datetime']} 至 {kline_data[-1]['datetime']}")
                
                # 如果有指标数据，合并到K线数据中
                if indicators_data:
                    for candle in kline_data:
                        for indicator_name, indicator_values in indicators_data.items():
                            # 查找对应时间点的指标数据
                            for ind_data in indicator_values:
                                if ind_data['time'] == candle['time']:
                                    candle[indicator_name] = ind_data['value']
                                    break
                
                # 导出数据
                export_data(kline_data)
                
                # 标记数据已加载
                data_loaded = True
                
                # 取消超时任务
                try:
                    timeout_task.cancel()
                except Exception:
                    pass
                
                # 关闭连接
                print('数据获取完成，关闭连接...')
                asyncio.create_task(close_connection())
            except Exception as e:
                print(f"处理更新时出错: {e}")
                import traceback
                traceback.print_exc()
        
        chart.on_update(on_update)
        
        async def close_connection():
            """关闭连接"""
            print("正在关闭连接...")
            await asyncio.sleep(1)
            # 使用异步方法删除chart
            if hasattr(chart, 'remove'):
                await chart.remove()
            elif hasattr(chart, 'delete'):
                chart.delete()
            else:
                print("警告：无法找到chart的删除方法")
                
            await client.end()
            print("连接已关闭")
        
        # 导出数据到文件
        def export_data(data):
            """导出数据到文件"""
            file_path = os.path.join(config['output_dir'], config['file_name'] + '.' + config['format'])
            
            try:
                if config['format'] == 'json':
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                elif config['format'] == 'csv':
                    # 创建CSV内容
                    if not data:
                        return
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        # 获取所有字段名
                        headers = list(data[0].keys())
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(data)
                else:
                    raise ValueError(f"不支持的输出格式: {config['format']}")
                
                print(f"数据已保存到: {file_path}")
            except Exception as e:
                print('保存数据出错:', e)
        
        # 添加技术指标
        async def add_indicators():
            """添加技术指标"""
            print('添加技术指标...')
            
            try:
                # 添加移动平均线指标
                indicators = [
                    {'name': 'EMA20', 'type': 'STD;EMA', 'options': {'Length': 20}},
                    {'name': 'SMA50', 'type': 'STD;SMA', 'options': {'Length': 50}},
                    {'name': 'RSI14', 'type': 'STD;RSI', 'options': {'Length': 14}}
                ]
                
                for indicator in indicators:
                    indic = await get_indicator(indicator['type'])
                    
                    # 设置指标参数
                    for option_name, option_value in indicator['options'].items():
                        indic.set_option(option_name, option_value)
                    
                    # 创建指标研究
                    study = chart.Study(indic)
                    
                    # 初始化指标数据存储
                    indicators_data[indicator['name']] = []
                    
                    # 监听指标更新
                    def create_update_handler(indicator_name):
                        def on_indicator_update():
                            nonlocal study
                            if not study.periods:
                                return
                            
                            # 存储指标数据
                            indicators_data[indicator_name] = [
                                {'time': period.time, 'value': period.plot_0}
                                for period in study.periods
                            ]
                            
                            print(f"{indicator_name} 指标数据已更新, 共 {len(indicators_data[indicator_name])} 条")
                        
                        return on_indicator_update
                    
                    study.on_update(create_update_handler(indicator['name']))
                    
                    # 等待study创建完成
                    await asyncio.sleep(0.5)
            
            except Exception as e:
                print('添加指标失败:', e)
                import traceback
                traceback.print_exc()
        
        # 添加定期状态检查
        async def status_check():
            """定期检查连接状态和数据加载进度"""
            while not data_loaded:
                debug_print(f"连接状态: {'已连接' if client.is_open else '未连接'}, 登录状态: {'已登录' if client.is_logged else '未登录'}")
                if hasattr(chart, 'periods') and chart.periods:
                    debug_print(f"已加载K线数据: {len(chart.periods)}条")
                else:
                    debug_print("尚未收到K线数据")
                await asyncio.sleep(5)
        
        # 启动状态检查
        status_check_task = asyncio.create_task(status_check())
        
        try:
            # 等待数据加载或超时
            await timeout_task
            print("操作超时，可能是交易对不存在或网络问题")
            status_check_task.cancel()  # 取消状态检查任务
            await client.end()
        except asyncio.CancelledError:
            # 超时任务被取消，说明数据已加载完成
            status_check_task.cancel()  # 取消状态检查任务
    
    except Exception as e:
        print(f"程序出现异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n程序被中断')
        sys.exit(0) 