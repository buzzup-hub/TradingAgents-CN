"""
市场数据模块
"""
import json
from typing import Dict, Any, Callable, List

from config.logging_config import get_logger
logger = get_logger(__name__)

class QuoteMarket:
    """
    市场数据类
    """
    def __init__(self, quote_session, symbol, session='regular'):
        """
        初始化市场数据
        
        Args:
            quote_session: 行情会话
            symbol: 交易符号
            session: 市场会话类型
        """
        self._symbol = symbol
        self._session = session
        self._symbol_key = f"={json.dumps({'session': session, 'symbol': symbol})}"
        
        self._symbol_listeners = quote_session.symbol_listeners
        self._quote_session = quote_session
        
        if self._symbol_key not in self._symbol_listeners:
            self._symbol_listeners[self._symbol_key] = []
            quote_session.send('quote_add_symbols', [
                quote_session.session_id,
                self._symbol_key
            ])
        
        self._symbol_listener_id = len(self._symbol_listeners[self._symbol_key])
        self._symbol_listeners[self._symbol_key].append(self._handle_data)
        
        self._last_data = {}
        self._callbacks = {
            'loaded': [],
            'data': [],
            'event': [],
            'error': []
        }
        
    def _handle_event(self, event, *data):
        """
        处理事件
        
        Args:
            event: 事件类型
            data: 事件数据
        """
        for callback in self._callbacks[event]:
            callback(*data)
            
        for callback in self._callbacks['event']:
            callback(event, *data)
    
    def _handle_error(self, *msgs):
        """
        处理错误
        
        Args:
            msgs: 错误信息
        """
        if not self._callbacks['error']:
            # 修复格式化错误
            # 将msgs转换为字符串并合并
            error_msg = " ".join(str(msg) for msg in msgs)
            logger.error(f"ERROR: {error_msg}")
        else:
            self._handle_event('error', *msgs)
    
    def _handle_data(self, packet):
        """
        处理数据包
        
        Args:
            packet: 数据包
        """
        if packet['type'] == 'qsd' and packet['data'][1]['s'] == 'ok':
            self._last_data.update(packet['data'][1]['v'])
            self._handle_event('data', self._last_data)
            return
            
        if packet['type'] == 'quote_completed':
            self._handle_event('loaded')
            return
            
        if packet['type'] == 'qsd' and packet['data'][1]['s'] == 'error':
            self._handle_error('Market error', packet['data'])
            
    def on_loaded(self, callback):
        """
        添加加载完成回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['loaded'].append(callback)
        
    def on_data(self, callback):
        """
        添加数据回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['data'].append(callback)
        
    def on_event(self, callback):
        """
        添加事件回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['event'].append(callback)
        
    def on_error(self, callback):
        """
        添加错误回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['error'].append(callback)
        
    def close(self):
        """关闭市场数据连接"""
        if len(self._symbol_listeners[self._symbol_key]) <= 1:
            self._quote_session.send('quote_remove_symbols', [
                self._quote_session.session_id,
                self._symbol_key
            ])
            
        self._symbol_listeners[self._symbol_key][self._symbol_listener_id] = None 