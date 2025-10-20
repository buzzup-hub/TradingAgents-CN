"""
行情会话模块
"""
from typing import List, Dict, Any, Optional, Callable, Union
from ..utils import gen_session_id
from .market import QuoteMarket

def get_quote_fields(fields_type='all'):
    """
    获取行情字段列表
    
    Args:
        fields_type: 字段类型
        
    Returns:
        List[str]: 字段列表
    """
    if fields_type == 'price':
        return ['lp']
    
    return [
        'base-currency-logoid', 'ch', 'chp', 'currency-logoid',
        'currency_code', 'current_session', 'description',
        'exchange', 'format', 'fractional', 'is_tradable',
        'language', 'local_description', 'logoid', 'lp',
        'lp_time', 'minmov', 'minmove2', 'original_name',
        'pricescale', 'pro_name', 'short_name', 'type',
        'update_mode', 'volume', 'ask', 'bid', 'fundamentals',
        'high_price', 'low_price', 'open_price', 'prev_close_price',
        'rch', 'rchp', 'rtc', 'rtc_time', 'status', 'industry',
        'basic_eps_net_income', 'beta_1_year', 'market_cap_basic',
        'earnings_per_share_basic_ttm', 'price_earnings_ttm',
        'sector', 'dividends_yield', 'timezone', 'country_code',
        'provider_id',
    ]

class QuoteSession:
    """
    行情会话类
    """
    def __init__(self, client, options=None):
        """
        初始化行情会话
        
        Args:
            client: 客户端实例
            options: 会话选项
        """
        if options is None:
            options = {}
            
        self._session_id = gen_session_id('qs')
        self._client = client
        self._symbol_listeners = {}
        
        # 创建会话
        self._client.sessions[self._session_id] = {
            'type': 'quote',
            'on_data': self._on_session_data
        }
        
        # 设置字段
        fields = (options.get('custom_fields', []) 
                  if options.get('custom_fields') 
                  else get_quote_fields(options.get('fields')))
        
        # 发送创建会话请求
        self._client.send('quote_create_session', [self._session_id])
        self._client.send('quote_set_fields', [self._session_id, *fields])
        
        # 创建Market构造函数
        self.Market = lambda symbol, session='regular': QuoteMarket(
            self,
            symbol,
            session
        )
        
    def _on_session_data(self, packet):
        """
        处理会话数据
        
        Args:
            packet: 数据包
        """
        if packet['type'] == 'quote_completed':
            symbol_key = packet['data'][1]
            if symbol_key not in self._symbol_listeners:
                self._client.send('quote_remove_symbols', [self._session_id, symbol_key])
                return
                
            for handler in self._symbol_listeners[symbol_key]:
                if handler:
                    handler(packet)
        
        elif packet['type'] == 'qsd':
            symbol_key = packet['data'][1]['n']
            if symbol_key not in self._symbol_listeners:
                self._client.send('quote_remove_symbols', [self._session_id, symbol_key])
                return
                
            for handler in self._symbol_listeners[symbol_key]:
                if handler:
                    handler(packet)
    
    @property
    def session_id(self):
        """获取会话ID"""
        return self._session_id
    
    @property
    def symbol_listeners(self):
        """获取符号监听器"""
        return self._symbol_listeners
    
    def send(self, packet_type, packet_data):
        """
        发送数据包
        
        Args:
            packet_type: 数据包类型
            packet_data: 数据包内容
        """
        self._client.send(packet_type, packet_data)
    
    def delete(self):
        """删除会话"""
        self._client.send('quote_delete_session', [self._session_id])
        if self._session_id in self._client.sessions:
            del self._client.sessions[self._session_id] 