"""
TradingView API Client 主模块

这个模块提供对TradingView API的访问，可以获取市场数据、图表数据和技术指标。
"""

# 客户端核心
from .client import Client

# 图表模块
from .chart import ChartSession, Study

# 行情模块
from .quote import QuoteSession, QuoteMarket

# 指标和技术分析
from .classes.builtin_indicator import BuiltInIndicator
from .classes.pine_indicator import PineIndicator
from .classes.pine_perm_manager import PinePermManager

# 工具和辅助函数
from .misc_requests import (
    fetch_scan_data,
    get_ta,
    search_market,
    search_market_v3,
    search_indicator,
    get_indicator,
    login_user,
    get_private_indicators,
    get_chart_token,
    get_drawings
)

# 工具模块
from . import utils
from . import protocol
from . import tradingview_types as types

# 版本信息
__version__ = '1.0.0'

__all__ = [
    'Client',
    'ChartSession', 'Study',
    'QuoteSession', 'QuoteMarket',
    'BuiltInIndicator', 'PineIndicator', 'PinePermManager',
    'fetch_scan_data', 'get_ta', 'search_market', 'search_market_v3',
    'search_indicator', 'get_indicator', 'login_user',
    'get_private_indicators', 'get_chart_token', 'get_drawings',
    'utils', 'protocol', 'types'
] 