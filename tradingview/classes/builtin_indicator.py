"""
内置指标类
"""
from typing import Dict, Any, Optional

# 默认值配置
DEFAULT_VALUES = {
    'Volume@tv-basicstudies-241': {
        'length': 20,
        'col_prev_close': False,
    },
    'VbPFixed@tv-basicstudies-241': {
        'rowsLayout': 'Number Of Rows',
        'rows': 24,
        'volume': 'Up/Down',
        'vaVolume': 70,
        'subscribeRealtime': False,
        'first_bar_time': None,
        'last_bar_time': None,
        'extendToRight': False,
        'mapRightBoundaryToBarStartTime': True,
    },
    'VbPFixed@tv-basicstudies-241!': {
        'rowsLayout': 'Number Of Rows',
        'rows': 24,
        'volume': 'Up/Down',
        'vaVolume': 70,
        'subscribeRealtime': False,
        'first_bar_time': None,
        'last_bar_time': None,
    },
    'VbPFixed@tv-volumebyprice-53!': {
        'rowsLayout': 'Number Of Rows',
        'rows': 24,
        'volume': 'Up/Down',
        'vaVolume': 70,
        'subscribeRealtime': False,
        'first_bar_time': None,
        'last_bar_time': None,
    },
    'VbPSessions@tv-volumebyprice-53': {
        'rowsLayout': 'Number Of Rows',
        'rows': 24,
        'volume': 'Up/Down',
        'vaVolume': 70,
        'extendPocRight': False,
    },
    'VbPSessionsRough@tv-volumebyprice-53!': {
        'volume': 'Up/Down',
        'vaVolume': 70,
    },
    'VbPSessionsDetailed@tv-volumebyprice-53!': {
        'volume': 'Up/Down',
        'vaVolume': 70,
        'subscribeRealtime': False,
        'first_visible_bar_time': None,
        'last_visible_bar_time': None,
    },
    'VbPVisible@tv-volumebyprice-53': {
        'rowsLayout': 'Number Of Rows',
        'rows': 24,
        'volume': 'Up/Down',
        'vaVolume': 70,
        'subscribeRealtime': False,
        'first_visible_bar_time': None,
        'last_visible_bar_time': None,
    },
}

class BuiltInIndicator:
    """
    内置指标类
    """
    def __init__(self, type: str = ''):
        """
        初始化内置指标
        
        Args:
            type: 指标类型
        """
        if not type:
            raise ValueError(f"Wrong built-in indicator type '{type}'.")
            
        self._type = type
        self._options = DEFAULT_VALUES.get(type, {}).copy()
        
    @property
    def type(self) -> str:
        """获取指标类型"""
        return self._type
        
    @property
    def options(self) -> Dict[str, Any]:
        """获取指标选项"""
        return self._options
        
    def set_option(self, key: str, value: Any, force: bool = False) -> None:
        """
        设置指标选项
        
        Args:
            key: 选项键
            value: 选项值
            force: 是否强制设置
        """
        if force:
            self._options[key] = value
            return
            
        if self._type in DEFAULT_VALUES:
            default_value = DEFAULT_VALUES[self._type].get(key)
            
            if default_value is not None:
                # 类型检查
                required_type = type(default_value)
                if not isinstance(value, required_type):
                    raise TypeError(f"Wrong '{key}' value type '{type(value).__name__}' (must be '{required_type.__name__}')")
                    
            elif not force:
                raise KeyError(f"Option '{key}' is denied with '{self._type}' indicator")
                
        self._options[key] = value 