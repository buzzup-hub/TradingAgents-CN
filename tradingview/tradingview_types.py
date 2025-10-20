"""
类型定义模块
"""
from enum import Enum
from typing import List, Dict, Any, Union, Callable, Optional

# 市场符号类型
MarketSymbol = str  # 'BTCEUR' 或 'KRAKEN:BTCEUR'

# 时区类型
Timezone = str  # 'Etc/UTC', 'exchange', 'Europe/Moscow' 等

# 时间周期常量
VALID_TIMEFRAMES = {
    "1", "3", "5", "15", "30", "45", 
    "60", "120", "180", "240", 
    "1D", "1W", "1M", "D", "W", "M"
}

# 时间周期类型，仍定义为字符串
TimeFrame = str  # 但应该是VALID_TIMEFRAMES中的一个值

def validate_timeframe(timeframe: TimeFrame) -> bool:
    """验证给定的时间周期是否有效"""
    return timeframe in VALID_TIMEFRAMES

class TimeFrame(str, Enum):
    """时间周期枚举类型"""
    MIN_1 = "1"      # 1分钟
    MIN_3 = "3"      # 3分钟
    MIN_5 = "5"      # 5分钟
    MIN_15 = "15"    # 15分钟
    MIN_30 = "30"    # 30分钟
    MIN_45 = "45"    # 45分钟
    MIN_60 = "60"    # 1小时
    MIN_120 = "120"  # 2小时
    MIN_180 = "180"  # 3小时
    MIN_240 = "240"  # 4小时
    DAY = "1D"       # 日线
    WEEK = "1W"      # 周线
    MONTH = "1M"     # 月线
    DAY_ALT = "D"    # 日线(替代表示)
    WEEK_ALT = "W"   # 周线(替代表示)
    MONTH_ALT = "M"  # 月线(替代表示)

# 时间周期类型
TimeFrame = str  # '1', '5', '15', '30', '60', '240', '1D', '1W', '1M'

# 指标类型
IndicatorType = str  # 'Script@tv-scripting-101!', 'StrategyScript@tv-scripting-101!'

# 内置指标类型
BuiltInIndicatorType = str  # 'Volume@tv-basicstudies-241', 等

# 内置指标选项类型
BuiltInIndicatorOption = str  # 'rowsLayout', 'rows', 'volume', 等

# 图形绘制扩展类型
ExtendValue = str  # 'right', 'left', 'both', 'none'

# Y轴定位类型
YLocValue = str  # 'price', 'abovebar', 'belowbar'

# 标签样式类型
LabelStyleValue = str  # 'none', 'xcross', 'cross', 等

# 线条样式类型
LineStyleValue = str  # 'solid', 'dotted', 'dashed', 等

# 方框样式类型
BoxStyleValue = str  # 'solid', 'dotted', 'dashed'

# 大小值类型
SizeValue = str  # 'auto', 'huge', 'large', 'normal', 'small', 'tiny'

# 垂直对齐类型
VAlignValue = str  # 'top', 'center', 'bottom'

# 水平对齐类型
HAlignValue = str  # 'left', 'center', 'right'

# 文本包装类型
TextWrapValue = str  # 'none', 'auto'

# 表格位置类型
TablePositionValue = str  # 'top_left', 'top_center', 等

# 事件类型
ClientEvent = str  # 'connected', 'disconnected', 等

# 市场事件类型
MarketEvent = str  # 'loaded', 'data', 'error'

# 更新变化类型
UpdateChangeType = str  # 'plots', 'report.currency', 等 