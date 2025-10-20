#!/usr/bin/env python3
"""
此示例演示如何处理TradingView API客户端中的各种错误
"""
import asyncio
import os
from pprint import pprint

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
    
    print("=== 示例1: 无效的交易对符号 ===")
    
    # 创建图表（无效的交易对）
    chart1 = tv.create_chart('INVALID_SYMBOL', '1D', 1000)
    
    # 定义回调函数
    def on_error1(err):
        """错误处理回调"""
        print("错误示例1:", err)
        print("成功捕获无效交易对错误")
        # 不关闭连接，继续下一个示例
    
    def on_ready1():
        """准备就绪回调"""
        print("图表1已准备就绪 (这不应该发生，因为交易对无效)")
    
    # 设置回调函数
    chart1.on_error = on_error1
    chart1.on_ready = on_ready1
    
    # 创建图表
    chart1.create()
    
    # 等待错误发生
    await asyncio.sleep(3)
    
    print("\n=== 示例2: 无效的指标 ===")
    
    # 创建图表（有效的交易对）
    chart2 = tv.create_chart('BINANCE:BTCUSDT', '1D', 1000)
    
    # 定义回调函数
    def on_error2(err):
        """错误处理回调"""
        print("错误示例2:", err)
        print("成功捕获无效指标错误")
        # 不关闭连接，继续下一个示例
    
    def on_ready2():
        """准备就绪回调"""
        print("图表2已准备就绪")
        
        # 尝试使用无效的指标
        try:
            chart2.add_indicator("INVALID_INDICATOR")
        except Exception as e:
            print(f"添加指标时发生异常: {e}")
    
    # 设置回调函数
    chart2.on_error = on_error2
    chart2.on_ready = on_ready2
    
    # 创建图表
    chart2.create()
    
    # 等待指标错误发生
    await asyncio.sleep(3)
    
    print("\n=== 示例3: 身份验证错误 ===")
    
    # 创建一个无效凭证的客户端
    invalid_client = Client("invalid_session", "invalid_signature")
    
    try:
        # 连接到TradingView（预期会失败）
        await invalid_client.connect()
        print("连接成功 (这不应该发生，因为凭证无效)")
    except Exception as e:
        print(f"认证错误示例: {e}")
        print("成功捕获身份验证错误")
    
    # 关闭所有连接
    print("\n关闭连接...")
    tv.close()

if __name__ == '__main__':
    asyncio.run(main()) 