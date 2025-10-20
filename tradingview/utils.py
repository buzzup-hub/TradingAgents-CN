"""
工具函数模块
"""
import random
import string

def gen_session_id(type='xs'):
    """
    生成会话ID
    
    Args:
        type: 会话类型
        
    Returns:
        str: 生成的会话ID
    """
    chars = string.ascii_letters + string.digits
    random_str = ''.join(random.choice(chars) for _ in range(12))
    return f"{type}_{random_str}"

def gen_auth_cookies(session_id='', signature=''):
    """
    生成认证cookie
    
    Args:
        session_id: 会话ID
        signature: 签名
        
    Returns:
        str: 认证cookie字符串
    """
    if not session_id:
        return ''
    if not signature:
        return f'sessionid={session_id}'
    return f'sessionid={session_id};sessionid_sign={signature}' 