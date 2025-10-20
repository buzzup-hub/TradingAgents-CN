#!/usr/bin/env python3
"""
获取图表绘图示例
"""
import asyncio
import json
import os
from pprint import pprint

from ..misc import (
    get_chart_token,
    get_drawings,
    login_user
)

async def main():
    """主函数"""
    print("TradingView 图表绘图获取示例")
    print("-----------------------------")
    
    # 需要一个布局ID，可以从任何已保存的TradingView图表URL中获取
    # 例如：https://www.tradingview.com/chart/abcdefgh/ 中的 abcdefgh
    layout_id = input("请输入图表布局ID: ")
    if not layout_id:
        print("错误: 需要提供布局ID")
        return
    
    symbol = input("请输入市场符号 (可选，例如 BINANCE:BTCUSDT): ")
    
    # 决定是否使用认证
    use_auth = input("是否使用认证? (y/n): ").lower() == 'y'
    credentials = None
    
    if use_auth:
        # 从环境变量或用户输入获取凭证
        username = os.environ.get('TV_USERNAME') or input("请输入用户名或邮箱: ")
        password = os.environ.get('TV_PASSWORD') or input("请输入密码: ")
        
        try:
            # 登录
            print("\n登录中...")
            user = await login_user(username, password)
            print(f"登录成功: {user.username}")
            
            credentials = {
                'id': user.id,
                'session': user.session,
                'signature': user.signature
            }
        except Exception as e:
            print(f"登录失败: {e}")
            return
    
    try:
        # 获取图表token
        print("\n获取图表Token...")
        chart_token = await get_chart_token(layout_id, credentials)
        print(f"获取成功: {chart_token[:10]}...")
        
        # 获取绘图
        print("\n获取图表绘图...")
        drawings = await get_drawings(layout_id, symbol, credentials)
        
        print(f"\n找到 {len(drawings)} 个绘图:")
        
        # 按类型分组绘图
        drawing_types = {}
        for drawing in drawings:
            drawing_type = drawing.get('type', 'unknown')
            if drawing_type not in drawing_types:
                drawing_types[drawing_type] = 0
            drawing_types[drawing_type] += 1
        
        # 显示绘图类型统计
        print("\n绘图类型统计:")
        for drawing_type, count in drawing_types.items():
            print(f"{drawing_type}: {count}个")
        
        # 显示第一个绘图的详细信息
        if drawings:
            print("\n第一个绘图详细信息示例:")
            first_drawing = drawings[0]
            print(f"类型: {first_drawing.get('type', 'unknown')}")
            print(f"ID: {first_drawing.get('id', 'unknown')}")
            
            # 显示位置信息（如果有）
            if 'points' in first_drawing:
                print("\n位置点:")
                for i, point in enumerate(first_drawing['points']):
                    print(f"点 {i+1}: {point}")
                    
            # 显示样式信息（如果有）
            if 'style' in first_drawing:
                print("\n样式:")
                for key, value in first_drawing['style'].items():
                    print(f"{key}: {value}")
    
    except Exception as e:
        print(f"获取图表绘图失败: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 