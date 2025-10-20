"""
Pine权限管理器类
"""
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from ..utils import gen_auth_cookies

class PinePermManager:
    """
    Pine权限管理器类
    """
    def __init__(self, session_id: str, signature: str, pine_id: str):
        """
        初始化Pine权限管理器
        
        Args:
            session_id: SessionID
            signature: 签名
            pine_id: Pine指标ID
        """
        if not session_id:
            raise ValueError("请提供会话ID")
        if not signature:
            raise ValueError("请提供签名")
        if not pine_id:
            raise ValueError("请提供Pine ID")
            
        self.session_id = session_id
        self.signature = signature
        self.pine_id = pine_id
        
    async def get_users(self, limit: int = 10, order: str = '-created') -> List[Dict[str, Any]]:
        """
        获取授权用户列表
        
        Args:
            limit: 获取数量限制
            order: 排序方式
            
        Returns:
            List[Dict]: 用户列表
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://www.tradingview.com/pine_perm/list_users/?limit={limit}&order_by={order}",
                data=f"pine_id={self.pine_id.replace(';', '%3B')}",
                headers={
                    "origin": "https://www.tradingview.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "cookie": gen_auth_cookies(self.session_id, self.signature)
                }
            ) as resp:
                if resp.status >= 400:
                    error_data = await resp.json()
                    raise ValueError(error_data.get('detail', '凭证或Pine ID错误'))
                    
                data = await resp.json()
                return data.get('results', [])
                
    async def add_user(self, username: str, expiration: Optional[datetime] = None) -> str:
        """
        添加授权用户
        
        Args:
            username: 用户名
            expiration: 过期时间
            
        Returns:
            str: 状态
        """
        data = f"pine_id={self.pine_id.replace(';', '%3B')}&username_recip={username}"
        if expiration:
            data += f"&expiration={expiration.isoformat()}"
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.tradingview.com/pine_perm/add/",
                data=data,
                headers={
                    "origin": "https://www.tradingview.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "cookie": gen_auth_cookies(self.session_id, self.signature)
                }
            ) as resp:
                if resp.status >= 400:
                    error_data = await resp.json()
                    raise ValueError(error_data.get('detail', '凭证或Pine ID错误'))
                    
                data = await resp.json()
                return data.get('status', None)
                
    async def modify_expiration(self, username: str, expiration: Optional[datetime] = None) -> str:
        """
        修改授权过期时间
        
        Args:
            username: 用户名
            expiration: 新的过期时间
            
        Returns:
            str: 状态
        """
        data = f"pine_id={self.pine_id.replace(';', '%3B')}&username_recip={username}"
        if expiration:
            data += f"&expiration={expiration.isoformat()}"
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.tradingview.com/pine_perm/modify_user_expiration/",
                data=data,
                headers={
                    "origin": "https://www.tradingview.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "cookie": gen_auth_cookies(self.session_id, self.signature)
                }
            ) as resp:
                if resp.status >= 400:
                    error_data = await resp.json()
                    raise ValueError(error_data.get('detail', '凭证或Pine ID错误'))
                    
                data = await resp.json()
                return data.get('status', None)
                
    async def remove_user(self, username: str) -> str:
        """
        移除授权用户
        
        Args:
            username: 用户名
            
        Returns:
            str: 状态
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.tradingview.com/pine_perm/remove/",
                data=f"pine_id={self.pine_id.replace(';', '%3B')}&username_recip={username}",
                headers={
                    "origin": "https://www.tradingview.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "cookie": gen_auth_cookies(self.session_id, self.signature)
                }
            ) as resp:
                if resp.status >= 400:
                    error_data = await resp.json()
                    raise ValueError(error_data.get('detail', '凭证或Pine ID错误'))
                    
                data = await resp.json()
                return data.get('status', None) 