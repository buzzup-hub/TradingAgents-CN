# TradingView框架集成指南

## 📋 概述

本文档介绍如何将TradingView框架集成到TradingAgents-CN项目中，通过高级请求头伪装技术绕过网站请求次数限制。

## 🎯 集成目标

1. **绕过请求限制**: 使用TradingView的高级伪装技术
2. **数据源多样化**: 添加TradingView作为新的数据源
3. **保持兼容性**: 与现有数据结构完全兼容
4. **智能降级**: TradingView失败时自动降级到现有数据源

## 🏗️ 集成架构

### 现有数据源架构
```
DataSourceManager
├── AKShare (主要)
├── Tushare (备用)
└── BaoStock (降级)
```

### 集成后架构
```
DataSourceManager
├── TradingView (新增 - 高级伪装)
├── AKShare (主要)
├── Tushare (备用)
└── BaoStock (降级)
```

## 📁 文件结构

```
/data/code/TradingAgents-CN/
├── tradingagents/
│   └── dataflows/
│       ├── tradingview/                    # 新增TradingView框架
│       │   ├── __init__.py
│       │   ├── core.py                     # TradingView核心逻辑
│       │   ├── headers.py                  # 请求头管理
│       │   ├── session.py                  # 会话管理
│       │   └── data_parser.py              # 数据解析
│       ├── tradingview_utils.py            # 新增：TradingView适配器
│       ├── data_source_manager.py          # 修改：添加TradingView选项
│       └── ...
└── ...
```

## 🔧 集成步骤

### 步骤1: 复制TradingView框架代码

将你的TradingView框架代码复制到：
```
tradingagents/dataflows/tradingview/
```

### 步骤2: 创建TradingView适配器

参考已创建的 `tradingview_integration_example.py`

### 步骤3: 修改数据源管理器

在 `data_source_manager.py` 中添加TradingView选项：

```python
class ChinaDataSource(Enum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    BAOSTOCK = "baostock"
    TRADINGVIEW = "tradingview"  # 新增
```

### 步骤4: 数据格式统一

确保TradingView返回的数据与现有格式兼容：

```python
# 标准数据格式
{
    'Date': '2025-10-15',     # 日期
    'Open': 12.50,           # 开盘价
    'Close': 12.85,          # 收盘价
    'High': 12.90,           # 最高价
    'Low': 12.45,            # 最低价
    'Volume': 15000000,      # 成交量
    'Amount': 192750000,     # 成交额
    'Symbol': '000001'       # 股票代码
}
```

## 🚀 高级特性

### 1. 智能请求头轮换

```python
class HeaderRotator:
    """请求头轮换器"""
    def __init__(self):
        self.headers_pool = [
            # Chrome浏览器
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'},
            # Firefox浏览器
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'},
            # Safari浏览器
            {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'},
            # Edge浏览器
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/120.0.0.0'}
        ]

    def get_random_header(self):
        return random.choice(self.headers_pool)
```

### 2. 智能延迟策略

```python
class SmartDelay:
    """智能延迟策略"""
    def __init__(self):
        self.last_request_time = {}

    def wait_if_needed(self, domain: str, min_interval: float = 2.0):
        """根据域名智能延迟"""
        now = time.time()
        last_time = self.last_request_time.get(domain, 0)

        if now - last_time < min_interval:
            sleep_time = min_interval - (now - last_time) + random.uniform(0.5, 2.0)
            time.sleep(sleep_time)

        self.last_request_time[domain] = time.time()
```

### 3. 代理轮换

```python
class ProxyRotator:
    """代理轮换器"""
    def __init__(self, proxy_list: List[str]):
        self.proxy_list = proxy_list
        self.current_index = 0

    def get_proxy(self):
        """获取下一个代理"""
        if not self.proxy_list:
            return None

        proxy = self.proxy_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        return proxy
```

## 🔄 降级策略

### 1. 数据源优先级

```
1. TradingView (高级伪装，优先)
2. AKShare (稳定，次选)
3. Tushare (需要token，备用)
4. BaoStock (免费，降级)
```

### 2. 降级逻辑

```python
def get_stock_data_with_fallback(symbol: str, start_date: str, end_date: str) -> str:
    """带降级机制的数据获取"""

    # 尝试TradingView
    try:
        data = tradingview_provider.get_stock_data(symbol, start_date, end_date)
        if data and not data.empty:
            return format_data(data, "TradingView")
    except Exception as e:
        logger.warning(f"TradingView失败，降级到AKShare: {e}")

    # 降级到AKShare
    try:
        data = akshare_provider.get_stock_data(symbol, start_date, end_date)
        if data and not data.empty:
            return format_data(data, "AKShare")
    except Exception as e:
        logger.warning(f"AKShare失败，降级到Tushare: {e}")

    # 继续降级...
    return f"❌ 所有数据源都失败: {symbol}"
```

## 📊 性能优化

### 1. 缓存机制

```python
class TradingViewCache:
    """TradingView专用缓存"""
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None

    def set(self, key: str, data: Any):
        """设置缓存"""
        self.cache[key] = (data, time.time())
```

### 2. 并发请求

```python
import asyncio
import aiohttp

async def get_multiple_stocks(symbols: List[str]) -> Dict[str, Any]:
    """并发获取多个股票数据"""
    async with aiohttp.ClientSession() as session:
        tasks = [get_stock_data_async(session, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return dict(zip(symbols, results))
```

## 🛡️ 安全考虑

### 1. 请求频率控制

```python
class RateLimiter:
    """请求频率限制器"""
    def __init__(self, max_requests_per_minute: int = 30):
        self.max_requests = max_requests_per_minute
        self.requests = []

    def can_request(self) -> bool:
        """检查是否可以发送请求"""
        now = time.time()
        # 清理超过1分钟的请求记录
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
```

### 2. 错误处理

```python
class ErrorHandler:
    """统一错误处理"""
    @staticmethod
    def handle_request_error(error: Exception, url: str) -> str:
        """处理请求错误"""
        if isinstance(error, requests.exceptions.ConnectionError):
            return f"❌ 网络连接失败: {url}"
        elif isinstance(error, requests.exceptions.Timeout):
            return f"❌ 请求超时: {url}"
        elif isinstance(error, requests.exceptions.HTTPError):
            if error.response.status_code == 429:
                return f"❌ 请求被限制，请稍后重试: {url}"
            elif error.response.status_code == 403:
                return f"❌ 访问被拒绝，可能需要更新请求头: {url}"
        return f"❌ 未知错误: {error}"
```

## 📈 监控和日志

### 1. 性能监控

```python
class PerformanceMonitor:
    """性能监控器"""
    def __init__(self):
        self.request_times = []
        self.success_count = 0
        self.error_count = 0

    def record_request(self, duration: float, success: bool):
        """记录请求性能"""
        self.request_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.request_times:
            return {}

        return {
            'avg_response_time': sum(self.request_times) / len(self.request_times),
            'success_rate': self.success_count / (self.success_count + self.error_count),
            'total_requests': len(self.request_times)
        }
```

## 🧪 测试

### 1. 单元测试

```python
import unittest

class TestTradingViewIntegration(unittest.TestCase):
    def setUp(self):
        self.provider = TradingViewDataProvider()

    def test_get_stock_data(self):
        """测试股票数据获取"""
        data = self.provider.get_stock_data("000001", "2025-10-01", "2025-10-16")
        self.assertIsNotNone(data)
        self.assertFalse(data.empty)

    def test_data_format_compatibility(self):
        """测试数据格式兼容性"""
        data = self.provider.get_stock_data("000001", "2025-10-01", "2025-10-16")
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            self.assertIn(col, data.columns)
```

### 2. 集成测试

```python
def test_integration_with_existing_system():
    """测试与现有系统的集成"""
    # 使用数据源管理器测试TradingView集成
    manager = get_data_source_manager()
    manager.set_current_source(ChinaDataSource.TRADINGVIEW)

    result = manager.get_stock_data("000001", "2025-10-01", "2025-10-16")
    assert result and "❌" not in result
```

## 🚀 部署建议

### 1. 配置管理

```python
# config/tradingview_config.py
TRADINGVIEW_CONFIG = {
    'enabled': True,
    'priority': 1,  # 最高优先级
    'timeout': 30,
    'retry_attempts': 3,
    'min_delay': 2.0,
    'max_delay': 6.0,
    'cache_ttl': 300,
    'proxy_list': [],  # 可选的代理列表
    'headers_rotation': True
}
```

### 2. 环境变量

```bash
# .env文件
TRADINGVIEW_ENABLED=true
TRADINGVIEW_TIMEOUT=30
TRADINGVIEW_CACHE_TTL=300
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
```

## 📝 总结

通过集成TradingView框架，你可以：

1. ✅ **绕过请求限制** - 使用高级伪装技术
2. ✅ **提高数据质量** - 获取更实时准确的数据
3. ✅ **保持系统稳定** - 智能降级机制
4. ✅ **易于维护** - 模块化设计
5. ✅ **性能监控** - 完整的监控体系

这个集成方案既解决了你的核心问题（绕过限制），又保持了与现有系统的完全兼容性。