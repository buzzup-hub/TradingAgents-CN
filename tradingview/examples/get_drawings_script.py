#!/usr/bin/env python3
"""
此示例测试getDrawings函数
用法: python get_drawings_script.py <layout_id> [user_id]
"""
import asyncio
import sys
import os
from pprint import pprint

from chanlun.tradingview.misc_requests import get_drawings

async def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("错误: 请指定一个layoutID")
        print("用法: python get_drawings_script.py <layout_id> [user_id]")
        return
    
    layout_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 从环境变量获取认证信息
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    # 创建凭证字典
    credentials = None
    if session or signature:
        credentials = {
            'session': session,
            'signature': signature,
            'id': user_id
        }
    
    try:
        # 获取绘图
        drawings = await get_drawings(layout_id, None, credentials)
        
        # 打印结果
        print(f"找到 {len(drawings)} 个绘图:", [
            {
                'id': d.get('id'),
                'symbol': d.get('symbol'),
                'type': d.get('type'),
                'text': d.get('state', {}).get('text')
            }
            for d in drawings
        ])
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 