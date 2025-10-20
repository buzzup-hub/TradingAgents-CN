#!/usr/bin/env python3
"""
此示例创建Pine权限管理器并测试所有可用功能
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

from ...tradingview import PinePermManager

async def main():
    """主函数"""
    # 检查环境变量
    session = os.environ.get('TV_SESSION')
    signature = os.environ.get('TV_SIGNATURE')
    
    if not session or not signature:
        raise ValueError('请设置TV_SESSION和TV_SIGNATURE环境变量')
    
    # 获取Pine ID
    if len(sys.argv) < 2:
        raise ValueError('请指定Pine ID作为第一个参数')
    
    pine_id = sys.argv[1]
    print('Pine ID:', pine_id)
    
    # 创建Pine权限管理器
    manager = PinePermManager(
        session,
        signature,
        pine_id
    )
    
    # 获取已授权用户
    users = await manager.get_users()
    print('已授权用户:', users)
    
    # 添加用户'TradingView'
    print("添加用户'TradingView'...")
    
    status = await manager.add_user('TradingView')
    if status == 'ok':
        print('添加成功!')
    elif status == 'exists':
        print('该用户已经被授权')
    else:
        print('未知错误...')
    
    # 再次获取已授权用户
    users = await manager.get_users()
    print('已授权用户:', users)
    
    # 修改过期日期
    print('修改过期日期...')
    
    # 添加一天
    new_date = datetime.now() + timedelta(days=1)
    status = await manager.modify_expiration('TradingView', new_date)
    
    if status == 'ok':
        print('修改成功!')
    else:
        print('未知错误...')
    
    # 再次获取已授权用户
    users = await manager.get_users()
    print('已授权用户:', users)
    
    # 移除过期日期
    print('移除过期日期...')
    
    status = await manager.modify_expiration('TradingView')
    
    if status == 'ok':
        print('移除成功!')
    else:
        print('未知错误...')
    
    # 再次获取已授权用户
    users = await manager.get_users()
    print('已授权用户:', users)
    
    # 移除用户'TradingView'
    print("移除用户'TradingView'...")
    
    status = await manager.remove_user('TradingView')
    
    if status == 'ok':
        print('移除成功!')
    else:
        print('未知错误...')
    
    # 再次获取已授权用户
    users = await manager.get_users()
    print('已授权用户:', users)

if __name__ == '__main__':
    asyncio.run(main()) 