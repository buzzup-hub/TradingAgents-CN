#!/usr/bin/env python3
"""
用户登录示例
"""
import asyncio
import os
from getpass import getpass

from ..misc import (
    login_user,
    get_user,
    get_private_indicators
)



async def main():
    """
    获取用户信息示例

    如需登录获取更多数据，请提供token(SESSION)和signature

    sessionid
    b7dc5nugsk5td47u39wiolrj1iy0u544

    sessionid_sign
    v3:goGfCVtvE/NAUTmU4Kk+NhmPgfgIDk9mozUpMgUf77E=
    """
    print("TradingView 用户登录示例")
    print("------------------------")
    
    # 从环境变量或用户输入获取凭证
    username = os.environ.get('TV_USERNAME') or input("请输入用户名或邮箱: ")
    password = os.environ.get('TV_PASSWORD') or getpass("请输入密码: ")
    
    try:
        # 尝试登录
        print("\n登录中...")
        user = await login_user(username, password)
        
        print(f"\n登录成功!")
        print(f"用户名: {user.username}")
        print(f"用户ID: {user.id}")
        print(f"注册时间: {user.join_date}")
        print(f"粉丝数: {user.followers}")
        print(f"关注数: {user.following}")
        
        # 获取私有指标
        print("\n获取私有指标...")
        indicators = await get_private_indicators(user.session, user.signature)
        
        if indicators:
            print(f"\n找到 {len(indicators)} 个私有指标:")
            for i, ind in enumerate(indicators[:5], 1):
                print(f"{i}. {ind.name} (ID: {ind.id})")
            
            if len(indicators) > 5:
                print(f"...以及 {len(indicators) - 5} 个更多指标")
        else:
            print("\n没有找到私有指标")
            
        # 保存会话信息的示例
        print("\n会话信息:")
        print("如果要在其他地方使用这个会话，可以保存以下信息:")
        print(f"会话ID: {user.session}")
        print(f"会话签名: {user.signature}")
        
        # 演示使用已保存的会话获取用户信息
        print("\n使用会话ID获取用户信息...")
        user2 = await get_user(user.session, user.signature)
        print(f"验证成功: {user2.username} (ID: {user2.id})")
        
    except Exception as e:
        print(f"\n登录失败: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 