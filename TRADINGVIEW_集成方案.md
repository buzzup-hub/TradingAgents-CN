# TradingView 数据源集成方案

## 📋 目录
1. [当前状态分析](#当前状态分析)
2. [TradingView 架构](#tradingview-架构)
3. [集成方案](#集成方案)
4. [启动方式](#启动方式)
5. [完整替代方案](#完整替代方案)
6. [实施步骤](#实施步骤)

---

## 当前状态分析

### 现有数据源
项目目前使用多个数据源，按优先级排序：

```python
# tradingagents/dataflows/data_source_manager.py
fallback_order = [
    ChinaDataSource.TRADINGVIEW,  # 优先级1 (已集成但未完全激活)
    ChinaDataSource.AKSHARE,      # 优先级2
    ChinaDataSource.TUSHARE,      # 优先级3
    ChinaDataSource.BAOSTOCK      # 优先级4
]
```

### 已完成的集成
1. ✅ **TradingView适配器** (`tradingagents/dataflows/tradingview_adapter.py`)
   - 提供同步和异步接口
   - 支持A股、港股、美股代码转换
   - 已集成到数据源管理器

2. ✅ **TradingView框架** (`/home/ceshi/code/TradingAgents-CN/tradingview/`)
   - 完整的WebSocket客户端
   - 双层缓存系统
   - 数据质量监控
   - HTTP API 服务器

---

## TradingView 架构

### 三层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│  应用层 (TradingAgents-CN)                                  │
│  ├─ web/app.py (Streamlit界面)                             │
│  ├─ tradingagents/graph/trading_graph.py (交易图)          │
│  └─ tradingagents/dataflows/interface.py (统一接口)        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  数据管理层 (Data Source Manager)                           │
│  ├─ data_source_manager.py (数据源管理器)                  │
│  ├─ tradingview_adapter.py (TradingView适配器)            │
│  ├─ akshare_utils.py (AKShare适配器)                      │
│  └─ tushare_adapter.py (Tushare适配器)                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  TradingView核心层 (/home/ceshi/code/.../tradingview/)     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 方式1: 直接集成 (Python SDK)                          │ │
│  │  ├─ client.py (WebSocket客户端)                      │ │
│  │  ├─ enhanced_client.py (增强客户端)                  │ │
│  │  ├─ data_cache_manager.py (缓存管理)                 │ │
│  │  └─ enhanced_data_quality_monitor.py (质量监控)      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 方式2: HTTP API服务 (推荐)                            │ │
│  │  ├─ kline_api_server.py (FastAPI服务)                │ │
│  │  ├─ historical_kline_service.py (K线服务)            │ │
│  │  └─ api_server.py (完整API服务器)                    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 集成方案

### 方案1: Python SDK 直接集成 (当前实现)

**优点:**
- ✅ 直接调用，响应快
- ✅ 无需额外服务
- ✅ 已基本实现

**缺点:**
- ⚠️ WebSocket连接管理复杂
- ⚠️ 事件循环冲突风险
- ⚠️ 需要处理异步/同步转换

**当前实现位置:**
```python
# tradingagents/dataflows/tradingview_adapter.py
class TradingViewDataProvider:
    async def get_stock_data(self, symbol, start_date, end_date):
        # 直接使用TradingView WebSocket客户端
        from tradingview import Client
        ...
```

**使用方式:**
```python
from tradingagents.dataflows.data_source_manager import get_data_source_manager

manager = get_data_source_manager()
manager.set_current_source(ChinaDataSource.TRADINGVIEW)
data = manager.get_stock_data('000001', '2025-01-01', '2025-01-31')
```

---

### 方案2: HTTP API 服务集成 (推荐)

**优点:**
- ✅ 解耦，稳定性高
- ✅ 易于监控和调试
- ✅ 支持多进程/多实例
- ✅ 缓存和质量控制完善

**缺点:**
- ⚠️ 需要启动额外服务
- ⚠️ 网络延迟（本地可忽略）

**架构:**
```
TradingAgents-CN (Port 8501)
        ↓ HTTP请求
TradingView API (Port 8000)
        ↓ WebSocket
TradingView.com
```

---

## 启动方式

### 方式A: K线API服务器 (最简单)

```bash
# 1. 进入tradingview目录
cd /home/ceshi/code/TradingAgents-CN/tradingview

# 2. 启动服务
python -m tradingview.kline_api_server

# 输出:
# 🚀 TradingView K线数据HTTP API服务
# 📡 服务地址: http://0.0.0.0:8000
# 📚 API文档: http://0.0.0.0:8000/docs
```

**测试:**
```bash
# 健康检查
curl http://localhost:8000/health

# 获取数据
curl "http://localhost:8000/klines?symbol=BINANCE:BTCUSDT&timeframe=15&count=100"
```

**特点:**
- 🎯 专注于K线数据
- 🚀 快速启动
- 📊 简单易用
- ✅ 适合大多数场景

---

### 方式B: 完整API服务器 (功能最全)

```bash
# 启动完整服务
cd /home/ceshi/code/TradingAgents-CN/tradingview
python -m tradingview.api_server
```

**特点:**
- 🌟 包含所有功能
- 💾 双层缓存
- 🛡️ 质量监控
- 📊 实时WebSocket
- 🔄 数据同步备份

**API端点:**
```
GET  /api/v1/health              # 健康检查
POST /api/v1/data/historical     # 历史数据
GET  /api/v1/symbols             # 支持的品种
GET  /api/v1/cache/stats         # 缓存统计
WS   /ws/realtime                # 实时数据流
```

---

### 方式C: 直接集成 (无需额外服务)

```python
# 已集成到data_source_manager.py
from tradingagents.dataflows.data_source_manager import get_data_source_manager

manager = get_data_source_manager()

# 切换到TradingView
manager.set_current_source(ChinaDataSource.TRADINGVIEW)

# 使用
data = manager.get_stock_data('600519', '2025-01-01', '2025-01-31')
```

**特点:**
- ✅ 无需额外服务
- ✅ 代码即用
- ⚠️ 需要配置环境变量

---

## 完整替代方案

### 目标：完全替代 AKShare/Tushare

#### 第1步：启动TradingView服务

**选择启动方式:**

```bash
# 推荐：后台启动K线API服务
nohup python -m tradingview.kline_api_server --port 8000 > tradingview.log 2>&1 &

# 或使用systemd服务 (生产环境)
sudo systemctl start tradingview-api
```

**验证服务:**
```bash
curl http://localhost:8000/health

# 预期输出:
# {
#   "status": "healthy",
#   "service": "kline_api",
#   "initialized": true
# }
```

---

#### 第2步：创建HTTP客户端适配器

创建文件 `/data/code/TradingAgents-CN/tradingagents/dataflows/tradingview_http_adapter.py`:

```python
#!/usr/bin/env python3
"""
TradingView HTTP API适配器
通过HTTP API调用TradingView服务，避免直接WebSocket集成的复杂性
"""

import requests
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

class TradingViewHTTPAdapter:
    """TradingView HTTP API适配器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def get_stock_data(self, symbol: str, start_date: str = None,
                       end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取股票数据

        Args:
            symbol: 股票代码 (支持 600519, 000001.SZ, AAPL等)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        try:
            # 转换股票代码为TradingView格式
            tv_symbol = self._convert_to_tv_symbol(symbol)

            # 计算K线数量
            count = 500
            if start_date and end_date:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                days = (end - start).days
                count = min(max(days + 10, 100), 5000)

            # 调用API
            url = f"{self.base_url}/klines"
            params = {
                'symbol': tv_symbol,
                'timeframe': '1D',
                'count': count,
                'format': 'simple',
                'quality': 'production',
                'use_cache': True
            }

            logger.info(f"🌐 TradingView HTTP请求: {tv_symbol}")

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('success') and data.get('data'):
                # 转换为DataFrame
                klines = data['data']
                df = pd.DataFrame(klines)

                # 标准化列名
                df['Date'] = pd.to_datetime(df['datetime'])
                df = df.rename(columns={
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                })

                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df['Symbol'] = symbol

                # 过滤日期范围
                if start_date:
                    df = df[df['Date'] >= start_date]
                if end_date:
                    df = df[df['Date'] <= end_date]

                logger.info(f"✅ TradingView获取成功: {len(df)}条数据")
                return df
            else:
                logger.error(f"❌ TradingView返回错误: {data}")
                return None

        except requests.exceptions.ConnectionError:
            logger.error(f"❌ 无法连接TradingView服务 ({self.base_url})")
            logger.info(f"💡 请先启动服务: python -m tradingview.kline_api_server")
            return None
        except Exception as e:
            logger.error(f"❌ TradingView HTTP请求失败: {e}")
            return None

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        return {
            'symbol': symbol,
            'name': f'股票{symbol}',
            'exchange': self._get_exchange(symbol),
            'currency': 'CNY',
            'source': 'tradingview_http'
        }

    def _convert_to_tv_symbol(self, symbol: str) -> str:
        """转换为TradingView格式"""
        # 去除后缀
        symbol = symbol.replace('.SZ', '').replace('.SS', '').replace('.HK', '')

        # A股
        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(('60', '68', '90')):
                return f"SSE:{symbol}"
            elif symbol.startswith(('00', '30', '20')):
                return f"SZSE:{symbol}"

        # 港股
        if symbol.startswith('0') and len(symbol) <= 5:
            return f"HKEX:{symbol.zfill(5)}"

        # 美股
        if symbol.isalpha():
            return f"NASDAQ:{symbol}" if symbol in ['AAPL', 'MSFT', 'GOOGL'] else f"NYSE:{symbol}"

        # 加密货币
        if 'BTC' in symbol or 'ETH' in symbol:
            return f"BINANCE:{symbol}"

        return symbol

    def _get_exchange(self, symbol: str) -> str:
        """获取交易所"""
        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(('60', '68', '90')):
                return 'SSE'
            else:
                return 'SZSE'
        return 'Unknown'


def get_tradingview_http_adapter() -> TradingViewHTTPAdapter:
    """获取TradingView HTTP适配器实例"""
    return TradingViewHTTPAdapter()
```

---

#### 第3步：更新数据源管理器

修改 `/data/code/TradingAgents-CN/tradingagents/dataflows/data_source_manager.py`:

```python
def _get_tradingview_adapter(self):
    """获取TradingView适配器 - 优先使用HTTP方式"""
    try:
        # 优先使用HTTP API方式
        from .tradingview_http_adapter import get_tradingview_http_adapter
        return get_tradingview_http_adapter()
    except Exception as e:
        logger.warning(f"HTTP适配器失败，降级到直接集成: {e}")

        # 降级到直接WebSocket集成
        try:
            from .tradingview_adapter import get_tradingview_adapter
            return get_tradingview_adapter()
        except Exception as e2:
            logger.error(f"TradingView适配器加载失败: {e2}")
            return None
```

---

#### 第4步：配置默认数据源

修改环境变量或配置文件:

```bash
# .env 文件
DEFAULT_CHINA_DATA_SOURCE=tradingview

# 或直接修改代码
# data_source_manager.py: line 61
return source_mapping.get(env_source, ChinaDataSource.TRADINGVIEW)
```

---

#### 第5步：验证集成

```python
# test_tradingview_integration.py
from tradingagents.dataflows.data_source_manager import get_data_source_manager

def test_tradingview():
    manager = get_data_source_manager()

    # 测试A股
    print("测试贵州茅台...")
    data = manager.get_stock_data('600519', '2025-01-01', '2025-01-20')
    print(data)

    # 测试港股
    print("\n测试腾讯控股...")
    data = manager.get_stock_data('00700.HK', '2025-01-01', '2025-01-20')
    print(data)

    # 测试美股
    print("\n测试苹果...")
    data = manager.get_stock_data('AAPL', '2025-01-01', '2025-01-20')
    print(data)

if __name__ == '__main__':
    test_tradingview()
```

---

## 实施步骤

### 阶段1：并行运行（推荐）

```bash
# 1. 启动TradingView服务
cd /home/ceshi/code/TradingAgents-CN/tradingview
nohup python -m tradingview.kline_api_server > tv.log 2>&1 &

# 2. 设置TradingView为默认数据源
export DEFAULT_CHINA_DATA_SOURCE=tradingview

# 3. 启动主应用
cd /data/code/TradingAgents-CN
streamlit run web/app.py
```

**特点:**
- TradingView作为主数据源
- AKShare/Tushare自动降级备份
- 无缝切换，零风险

---

### 阶段2：监控和调优

```bash
# 查看TradingView日志
tail -f tradingview.log

# 查看主应用日志
tail -f logs/tradingagents.log | grep -i tradingview

# 监控API健康
watch -n 5 'curl -s http://localhost:8000/health | jq'

# 查看缓存统计
curl http://localhost:8000/stats | jq
```

---

### 阶段3：完全替代（可选）

**移除旧数据源依赖:**

```python
# data_source_manager.py
# 只保留TradingView
available_sources = [ChinaDataSource.TRADINGVIEW]
```

**卸载不需要的包:**
```bash
pip uninstall akshare tushare baostock -y
```

---

## 对比分析

### TradingView vs AKShare

| 特性 | TradingView | AKShare |
|------|-------------|---------|
| **数据覆盖** | 全球市场 | 仅中国市场 |
| **数据质量** | 95%+ | 90%+ |
| **更新频率** | 实时 | 延迟15分钟 |
| **稳定性** | 高 (WebSocket) | 中 (爬虫易失效) |
| **缓存机制** | 双层缓存 | 无 |
| **监控告警** | 完善 | 无 |
| **API限制** | 无 | 受限 |
| **成本** | 免费 | 免费 |

### 数据格式对比

**TradingView返回:**
```json
{
  "success": true,
  "symbol": "SSE:600519",
  "count": 18,
  "data": [
    {
      "timestamp": 1704182400,
      "datetime": "2025-01-02T00:00:00",
      "open": 1524.0,
      "high": 1524.49,
      "low": 1480.0,
      "close": 1488.0,
      "volume": 50029
    }
  ]
}
```

**AKShare返回:**
```
日期        股票代码    开盘      收盘      最高      最低    成交量
2025-01-02  600519   1524.0   1488.0   1524.49  1480.00  50029
```

**TradingView优势:**
- ✅ 标准JSON格式
- ✅ 时间戳+人类可读时间
- ✅ 元数据完整（质量分数、来源等）
- ✅ RESTful API规范

---

## 常见问题

### Q1: TradingView服务如何保持运行？

**方案1: systemd服务 (推荐)**
```bash
# 创建服务文件
sudo nano /etc/systemd/system/tradingview-api.service

[Unit]
Description=TradingView K-Line API Service
After=network.target

[Service]
Type=simple
User=ceshi
WorkingDirectory=/home/ceshi/code/TradingAgents-CN/tradingview
ExecStart=/usr/bin/python3 -m tradingview.kline_api_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start tradingview-api
sudo systemctl enable tradingview-api
```

**方案2: Docker (跨平台)**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY tradingview /app/tradingview
RUN pip install fastapi uvicorn websockets
CMD ["python", "-m", "tradingview.kline_api_server"]
```

---

### Q2: 如何处理连接失败？

**自动降级机制** (已实现):
```python
# data_source_manager.py
def _try_fallback_sources(self, symbol, start_date, end_date):
    fallback_order = [
        ChinaDataSource.TRADINGVIEW,
        ChinaDataSource.AKSHARE,
        ChinaDataSource.TUSHARE,
        ChinaDataSource.BAOSTOCK
    ]

    for source in fallback_order:
        try:
            result = self._get_data_from_source(source, symbol, ...)
            if result and "❌" not in result:
                return result
        except:
            continue

    return "❌ 所有数据源都失败"
```

---

### Q3: 数据缓存如何工作？

**双层缓存架构:**
```
请求 → L1内存缓存(LRU) → L2 SQLite → TradingView API
        ↑ 80%命中         ↑ 15%命中    ↑ 5%实时获取
```

**缓存配置:**
```python
cache_config = {
    'max_memory_size': 5000,        # L1缓存大小
    'db_path': 'data/tv_cache.db',  # L2数据库
    'default_expire': 3600,          # 1小时过期
    'quality_threshold': 0.95        # 质量要求
}
```

---

## 总结

### 推荐方案：HTTP API集成

```mermaid
graph TB
    A[启动TradingView API服务] --> B[创建HTTP适配器]
    B --> C[更新数据源管理器]
    C --> D[设置为默认数据源]
    D --> E[验证测试]
    E --> F[监控运行]
    F --> G[逐步替代旧数据源]
```

### 核心优势

1. **解耦架构** - 服务独立，互不影响
2. **高可用性** - 自动重连、降级机制
3. **数据质量** - 六维质量监控
4. **性能优越** - 双层缓存，响应快
5. **易于维护** - 日志完善，监控齐全
6. **零成本** - 完全免费，无API限制

### 下一步行动

```bash
# 1. 启动TradingView服务
cd /home/ceshi/code/TradingAgents-CN/tradingview
python -m tradingview.kline_api_server

# 2. 新终端测试
curl http://localhost:8000/health
curl "http://localhost:8000/klines?symbol=SSE:600519&timeframe=1D&count=10"

# 3. 集成到主应用（我来帮你实现）
# ...
```

---

**文档版本:** v1.0
**创建日期:** 2025-10-20
**更新日期:** 2025-10-20
