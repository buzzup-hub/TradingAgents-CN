# TradingView模块外部集成指南

本文档详细介绍如何在不同场景下集成和使用TradingView数据源模块。

## 📋 目录

- [快速开始](#快速开始)
- [架构概览](#架构概览)
- [集成方式](#集成方式)
- [API接口](#api接口)
- [数据缓存](#数据缓存)
- [质量监控](#质量监控)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

## 🚀 快速开始

### 环境要求

```bash
# Python版本要求
Python >= 3.9

# 核心依赖
pip install asyncio websockets fastapi uvicorn aiohttp
pip install sqlite3 pandas numpy

# 可选依赖（用于高级功能）
pip install prometheus_client grafana-api redis
```

### 30秒快速体验

```python
import asyncio
from tradingview.api_server import TradingViewAPIServer

async def quick_start():
    # 启动API服务器
    server = TradingViewAPIServer({
        'cache_db_path': 'quick_demo.db',
        'max_memory_cache': 1000
    })
    
    await server.start_server(host="127.0.0.1", port=8000)

# 运行服务器
asyncio.run(quick_start())
```

访问 http://127.0.0.1:8000/api/v1/health 检查服务状态。

## 🏗️ 架构概览

TradingView模块采用**三层架构**设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部集成层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ RESTful API │  │ WebSocket   │  │ Python SDK  │            │
│  │   (HTTP)    │  │ (实时数据)   │  │  (直接集成)  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据处理层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ 缓存管理器   │  │ 质量监控器   │  │ 故障恢复器   │            │
│  │(双层缓存)   │  │(多维评估)   │  │(智能容错)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TradingView核心层                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ 增强客户端   │  │ 会话管理器   │  │ 协议处理器   │            │
│  │(智能重连)   │  │(多会话)     │  │(消息解析)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件说明

| 组件 | 职责 | 特性 |
|------|------|------|
| **API Server** | 提供RESTful和WebSocket接口 | 异步处理、CORS支持、自动文档 |
| **Cache Manager** | 双层缓存管理 | LRU内存缓存 + SQLite持久化 |
| **Quality Monitor** | 数据质量监控 | 六维质量评估、智能告警 |
| **Enhanced Client** | TradingView连接管理 | 自动重连、健康监控、性能优化 |

## 🔌 集成方式

### 方式1: RESTful API集成 (推荐)

适用于**跨语言**、**微服务**、**Web应用**等场景。

```python
import aiohttp
import asyncio

class TradingViewClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def get_data(self, symbol, timeframe, count=500):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/v1/data/historical"
            payload = {
                'symbol': symbol,
                'timeframe': timeframe,
                'count': count,
                'quality_check': True,
                'use_cache': True
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API请求失败: {response.status}")

# 使用示例
async def example():
    client = TradingViewClient()
    
    # 获取BTC 15分钟K线数据
    data = await client.get_data('BINANCE:BTCUSDT', '15', 1000)
    
    if data['status'] == 'success':
        klines = data['data']['klines']
        print(f"获取到 {len(klines)} 条K线数据")
        print(f"数据质量得分: {data['metadata']['quality_score']:.3f}")

asyncio.run(example())
```

#### API端点说明

| 端点 | 方法 | 说明 | 示例 |
|------|------|------|------|
| `/api/v1/health` | GET | 获取健康状态 | `curl http://localhost:8000/api/v1/health` |
| `/api/v1/data/historical` | POST | 获取历史数据 | 见上面示例 |
| `/api/v1/symbols` | GET | 获取支持的品种 | `curl http://localhost:8000/api/v1/symbols` |
| `/api/v1/cache/stats` | GET | 获取缓存统计 | `curl http://localhost:8000/api/v1/cache/stats` |
| `/api/v1/cache/clear` | DELETE | 清空缓存 | `curl -X DELETE http://localhost:8000/api/v1/cache/clear` |

### 方式2: WebSocket实时数据集成

适用于需要**实时推送**的场景。

```python
import asyncio
import websockets
import json

async def websocket_example():
    uri = "ws://localhost:8000/ws/realtime"
    
    async with websockets.connect(uri) as websocket:
        # 订阅实时数据
        subscribe_msg = {
            'type': 'subscribe',
            'symbols': ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'],
            'timeframes': ['1', '5', '15']
        }
        
        await websocket.send(json.dumps(subscribe_msg))
        
        # 接收数据
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'realtime_data':
                symbol = data['symbol']
                price = data['data']['price']
                print(f"实时价格: {symbol} = ${price}")
            
            elif data['type'] == 'subscribed':
                print(f"订阅成功: {data['symbols']}")

asyncio.run(websocket_example())
```

### 方式3: Python SDK直接集成

适用于**Python项目**内部集成。

```python
from tradingview.integration_examples import TradingViewDataSource

async def sdk_example():
    # 初始化数据源
    data_source = TradingViewDataSource({
        'cache_db_path': 'my_trading_app.db',
        'max_cache_size': 2000
    })
    
    if await data_source.initialize():
        # 获取历史数据
        market_data = await data_source.get_historical_data(
            'BINANCE:BTCUSDT', '15', count=1000
        )
        
        if market_data:
            print(f"获取到 {len(market_data.klines)} 条K线")
            
            # 订阅实时数据
            async def on_realtime_data(data):
                print(f"实时数据: {data}")
            
            await data_source.subscribe_realtime_data(
                ['BINANCE:BTCUSDT'], on_realtime_data
            )
        
        # 获取健康状态
        health = await data_source.get_health_status()
        print(f"数据源状态: {health['status']}")
        
        await data_source.shutdown()

asyncio.run(sdk_example())
```

## 🗄️ 数据缓存

### 双层缓存架构

TradingView模块实现了**内存+SQLite**的双层缓存架构：

```
┌─────────────────────────────────────────────────────────────────┐
│                       双层缓存架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🚀 L1: 内存缓存 (LRU)                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • 容量: 1000-5000条记录                                     │ │
│  │ • 延迟: < 1ms                                               │ │
│  │ • 命中率: 80-90%                                            │ │
│  │ • 策略: LRU淘汰                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼ (未命中)                         │
│  💾 L2: SQLite缓存 (持久化)                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ • 容量: 无限制                                               │ │
│  │ • 延迟: 5-10ms                                              │ │
│  │ • 命中率: 15-20%                                            │ │
│  │ • 特性: 跨会话持久化                                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 缓存使用示例

```python
from tradingview.data_cache_manager import DataCacheManager

async def cache_example():
    # 初始化缓存管理器
    cache_manager = DataCacheManager(
        db_path="my_cache.db",
        max_memory_size=2000
    )
    
    # 存储数据
    sample_data = {
        'symbol': 'BINANCE:BTCUSDT',
        'timeframe': '15',
        'klines': [
            {
                'timestamp': 1699123456,
                'open': 35000.0,
                'high': 35500.0,
                'low': 34800.0,
                'close': 35200.0,
                'volume': 123.45
            }
        ],
        'quality_score': 0.95
    }
    
    # 存储到缓存
    await cache_manager.store_historical_data(
        'BINANCE:BTCUSDT', '15', sample_data, expire_seconds=3600
    )
    
    # 从缓存获取
    cached_data = await cache_manager.get_historical_data(
        'BINANCE:BTCUSDT', '15', count=500
    )
    
    if cached_data:
        print("缓存命中!")
        print(f"质量得分: {cached_data['quality_score']}")
    
    # 获取缓存统计
    stats = await cache_manager.get_statistics()
    print(f"缓存命中率: {cache_manager.get_hit_rate():.2%}")
    print(f"缓存条目数: {stats.total_entries}")

asyncio.run(cache_example())
```

### 缓存优化配置

```python
# 推荐的缓存配置
cache_config = {
    # 内存缓存大小（条目数）
    'max_memory_size': 2000,
    
    # SQLite数据库路径
    'db_path': 'data/tradingview_cache.db',
    
    # 默认过期时间（秒）
    'default_expire_seconds': 3600,  # 1小时
    
    # 清理间隔（秒）
    'cleanup_interval': 300,  # 5分钟
    
    # 质量阈值（低于此值不缓存）
    'min_quality_for_cache': 0.8
}
```

## 🛡️ 质量监控

### 六维质量评估体系

系统实现了**完整性、准确性、一致性、及时性、有效性、唯一性**六个维度的数据质量评估：

```python
from tradingview.enhanced_data_quality_monitor import DataQualityMonitor

async def quality_monitor_example():
    # 初始化质量监控器
    monitor = DataQualityMonitor({
        'critical_quality_score': 0.6,
        'warning_quality_score': 0.8,
        'max_consecutive_failures': 3
    })
    
    # 注册告警处理器
    async def alert_handler(alert):
        print(f"质量告警: {alert.level.value} - {alert.message}")
        
        if alert.level.value == 'critical':
            # 关键告警处理逻辑
            print("触发应急响应机制")
    
    monitor.register_alert_handler(alert_handler)
    
    # 评估数据质量
    sample_data = {
        'symbol': 'BINANCE:BTCUSDT',
        'timeframe': '15',
        'klines': [
            # ... K线数据
        ]
    }
    
    result = await monitor.evaluate_data_quality(
        'BINANCE:BTCUSDT', '15', sample_data
    )
    
    print(f"质量评估结果:")
    print(f"  综合得分: {result.quality_score:.3f}")
    print(f"  质量等级: {result.metrics.quality_level.value}")
    print(f"  完整性: {result.metrics.completeness_score:.3f}")
    print(f"  准确性: {result.metrics.accuracy_score:.3f}")
    print(f"  一致性: {result.metrics.consistency_score:.3f}")
    
    # 获取改进建议
    if result.suggestions:
        print("改进建议:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")

asyncio.run(quality_monitor_example())
```

### 质量监控配置

```python
quality_config = {
    # 质量阈值
    'thresholds': {
        'min_completeness': 0.95,       # 最小完整性要求
        'min_accuracy': 0.90,           # 最小准确性要求
        'max_price_deviation': 0.20,    # 最大价格偏差 (20%)
        'max_volume_deviation': 5.0,    # 最大成交量偏差 (5倍)
        'max_timestamp_gap': 300,       # 最大时间戳间隔 (5分钟)
    },
    
    # 质量权重
    'weights': {
        'completeness': 0.25,
        'accuracy': 0.25,
        'consistency': 0.20,
        'timeliness': 0.15,
        'validity': 0.10,
        'uniqueness': 0.05
    },
    
    # 告警配置
    'alerts': {
        'critical_quality_score': 0.6,
        'warning_quality_score': 0.8,
        'max_consecutive_failures': 3
    }
}
```

## 📊 集成场景示例

### 场景1: 集成到trading_core

```python
# 在trading_core中使用TradingView作为数据源
from tradingview.integration_examples import TradingViewDataSource

class TradingSystem:
    def __init__(self):
        self.data_source = TradingViewDataSource({
            'cache_db_path': 'trading_system.db',
            'max_cache_size': 5000
        })
    
    async def initialize(self):
        await self.data_source.initialize()
    
    async def get_market_data(self, symbol, timeframe, count):
        return await self.data_source.get_historical_data(
            symbol, timeframe, count
        )
    
    async def start_realtime_monitoring(self, symbols):
        async def on_price_update(data):
            # 处理实时价格更新
            await self.process_price_update(data)
        
        await self.data_source.subscribe_realtime_data(
            symbols, on_price_update
        )
    
    async def process_price_update(self, data):
        # 实现你的交易逻辑
        symbol = data.get('symbol')
        price = data.get('price')
        print(f"处理价格更新: {symbol} = ${price}")
```

### 场景2: 集成到chanpy缠论分析

```python
from tradingview.integration_examples import ChanpyDataFeeder

async def chanpy_integration():
    # 初始化数据馈送器
    feeder = ChanpyDataFeeder()
    await feeder.initialize()
    
    # 为多个品种创建缠论分析
    symbols = ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT', 'BINANCE:ADAUSDT']
    timeframes = ['15', '60', '240']
    
    instances = {}
    
    for symbol in symbols:
        for tf in timeframes:
            instance_id = await feeder.create_chan_analysis(
                symbol, tf, 
                {'bi_strict': True, 'trigger_step': True}
            )
            
            if instance_id:
                instances[f"{symbol}_{tf}"] = instance_id
                print(f"创建缠论分析: {symbol} {tf}分钟")
    
    # 定期更新分析结果
    while True:
        for key, instance_id in instances.items():
            await feeder.update_chan_analysis(instance_id)
            
            result = feeder.get_chan_analysis_result(instance_id)
            if result:
                bsp_count = len(result.get('buy_sell_points', []))
                zs_count = len(result.get('zs_list', []))
                print(f"{key}: 买卖点={bsp_count}, 中枢={zs_count}")
        
        await asyncio.sleep(60)  # 每分钟更新一次

asyncio.run(chanpy_integration())
```

### 场景3: Web应用集成

```javascript
// 前端JavaScript集成示例
class TradingViewAPIClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.websocket = null;
    }
    
    // 获取历史数据
    async getHistoricalData(symbol, timeframe, count = 500) {
        const response = await fetch(`${this.baseUrl}/api/v1/data/historical`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                timeframe: timeframe,
                count: count,
                quality_check: true,
                use_cache: true
            })
        });
        
        return await response.json();
    }
    
    // 连接WebSocket
    connectWebSocket(onMessage) {
        this.websocket = new WebSocket(`ws://localhost:8000/ws/realtime`);
        
        this.websocket.onopen = () => {
            console.log('WebSocket连接成功');
        };
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onMessage(data);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }
    
    // 订阅实时数据
    subscribe(symbols, timeframes = ['1']) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'subscribe',
                symbols: symbols,
                timeframes: timeframes
            }));
        }
    }
}

// 使用示例
const client = new TradingViewAPIClient();

// 获取历史数据
client.getHistoricalData('BINANCE:BTCUSDT', '15', 1000)
    .then(data => {
        if (data.status === 'success') {
            console.log(`获取到 ${data.data.klines.length} 条K线`);
            // 在这里处理K线数据，比如绘制图表
        }
    });

// 连接实时数据
client.connectWebSocket((data) => {
    if (data.type === 'realtime_data') {
        console.log(`实时数据: ${data.symbol} = $${data.data.price}`);
        // 更新UI显示
    }
});

// 订阅实时数据
client.subscribe(['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT']);
```

## ⚙️ 配置参数

### API服务器配置

```python
api_server_config = {
    # 服务器配置
    'host': '0.0.0.0',
    'port': 8000,
    
    # 缓存配置
    'cache_db_path': 'data/tradingview_cache.db',
    'max_memory_cache': 5000,
    
    # TradingView客户端配置
    'tradingview_config': {
        'auto_reconnect': True,
        'health_monitoring': True,
        'performance_optimization': True,
        'max_reconnect_attempts': 10,
        'heartbeat_interval': 30,
        'connection_timeout': 10
    },
    
    # 质量监控配置
    'quality_config': {
        'critical_quality_score': 0.6,
        'warning_quality_score': 0.8,
        'enable_auto_correction': True
    },
    
    # 安全配置
    'cors_origins': ['*'],
    'rate_limit': {
        'requests_per_minute': 1000,
        'burst_size': 100
    }
}
```

### 数据源适配器配置

```python
data_source_config = {
    # 缓存配置
    'cache_db_path': 'trading_data.db',
    'max_cache_size': 2000,
    'cache_ttl': 3600,  # 1小时
    
    # 质量配置
    'min_quality_score': 0.8,
    'enable_quality_alerts': True,
    
    # 重试配置
    'max_retries': 3,
    'retry_delay': 1.0,
    'backoff_factor': 2.0,
    
    # 性能配置
    'request_timeout': 10.0,
    'concurrent_requests': 10,
    'batch_size': 100
}
```

## 🛠️ 最佳实践

### 1. 连接管理

```python
# ✅ 推荐做法
class ReliableDataSource:
    def __init__(self):
        self.client = None
        self.connection_pool = []
        
    async def initialize(self):
        # 使用连接池
        for i in range(3):
            client = EnhancedTradingViewClient({
                'auto_reconnect': True,
                'health_monitoring': True
            })
            await client.connect()
            self.connection_pool.append(client)
    
    async def get_data_with_fallback(self, symbol, timeframe):
        for client in self.connection_pool:
            try:
                return await client.get_data(symbol, timeframe)
            except Exception as e:
                print(f"客户端失败，尝试下一个: {e}")
                continue
        
        raise Exception("所有连接都失败了")
```

### 2. 缓存策略

```python
# ✅ 智能缓存策略
async def smart_cache_strategy(cache_manager, symbol, timeframe, count):
    # 1. 检查缓存
    cached_data = await cache_manager.get_historical_data(symbol, timeframe, count)
    
    if cached_data:
        # 2. 检查数据新鲜度
        last_timestamp = max(k['timestamp'] for k in cached_data['klines'])
        age_minutes = (time.time() - last_timestamp) / 60
        
        # 3. 根据时间框架决定是否需要更新
        update_intervals = {'1': 2, '5': 10, '15': 30, '60': 120}
        max_age = update_intervals.get(timeframe, 60)
        
        if age_minutes < max_age:
            return cached_data  # 使用缓存
    
    # 4. 获取新数据
    fresh_data = await get_fresh_data(symbol, timeframe, count)
    
    # 5. 更新缓存
    if fresh_data and fresh_data.get('quality_score', 0) >= 0.8:
        await cache_manager.store_historical_data(symbol, timeframe, fresh_data)
    
    return fresh_data
```

### 3. 错误处理

```python
# ✅ 完善的错误处理
async def robust_data_fetching(data_source, symbol, timeframe, max_retries=3):
    for attempt in range(max_retries):
        try:
            data = await data_source.get_historical_data(symbol, timeframe)
            
            if data and len(data.klines) > 0:
                return data
            else:
                raise ValueError("数据为空")
                
        except asyncio.TimeoutError:
            print(f"请求超时，重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(2 ** attempt)  # 指数退避
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"最终失败: {e}")
                return None
            else:
                print(f"尝试 {attempt + 1} 失败: {e}，重试中...")
                await asyncio.sleep(1)
    
    return None
```

### 4. 监控告警

```python
# ✅ 完善的监控告警
class AlertManager:
    def __init__(self):
        self.alert_channels = []
    
    def add_channel(self, channel):
        self.alert_channels.append(channel)
    
    async def send_alert(self, level, message, details=None):
        alert_data = {
            'level': level,
            'message': message,
            'details': details or {},
            'timestamp': time.time()
        }
        
        for channel in self.alert_channels:
            try:
                await channel.send(alert_data)
            except Exception as e:
                print(f"告警发送失败: {e}")

# 邮件告警通道
class EmailAlertChannel:
    async def send(self, alert_data):
        # 实现邮件发送逻辑
        pass

# Webhook告警通道
class WebhookAlertChannel:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    async def send(self, alert_data):
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=alert_data)
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. 连接问题

**问题**: 无法连接到TradingView
```
错误: Connection failed: Cannot connect to host
```

**解决方案**:
```python
# 检查网络连接
import aiohttp

async def test_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.tradingview.com') as response:
                print(f"网络连接正常: {response.status}")
    except Exception as e:
        print(f"网络连接问题: {e}")

# 检查代理设置
client_config = {
    'proxy': 'http://proxy.example.com:8080',  # 如果需要代理
    'timeout': 30,  # 增加超时时间
    'retry_attempts': 5
}
```

#### 2. 数据质量问题

**问题**: 数据质量得分过低
```
质量得分: 0.45 (低于阈值 0.8)
```

**解决方案**:
```python
# 调整质量阈值
quality_config = {
    'critical_quality_score': 0.4,  # 降低阈值
    'warning_quality_score': 0.6,
    'enable_auto_correction': True   # 启用自动修复
}

# 或者使用数据清洗
async def clean_data(raw_data):
    cleaned_klines = []
    
    for kline in raw_data['klines']:
        # 修复价格逻辑错误
        if kline['high'] < max(kline['open'], kline['close']):
            kline['high'] = max(kline['open'], kline['close'])
        
        if kline['low'] > min(kline['open'], kline['close']):
            kline['low'] = min(kline['open'], kline['close'])
        
        cleaned_klines.append(kline)
    
    raw_data['klines'] = cleaned_klines
    return raw_data
```

#### 3. 缓存问题

**问题**: 缓存命中率过低
```
缓存命中率: 15% (期望 > 70%)
```

**解决方案**:
```python
# 优化缓存配置
cache_config = {
    'max_memory_size': 5000,  # 增加内存缓存大小
    'default_expire_seconds': 7200,  # 延长过期时间
    'enable_predictive_caching': True  # 启用预测性缓存
}

# 预热缓存
async def warm_cache(cache_manager, popular_symbols):
    for symbol in popular_symbols:
        for timeframe in ['1', '5', '15', '60']:
            await cache_manager.get_historical_data(symbol, timeframe, 500)
    
    print("缓存预热完成")
```

#### 4. 性能问题

**问题**: 响应时间过长
```
平均响应时间: 2.5秒 (期望 < 500ms)
```

**解决方案**:
```python
# 启用并发处理
async def parallel_data_fetching(symbols, timeframe):
    tasks = []
    
    for symbol in symbols:
        task = asyncio.create_task(
            get_data_with_timeout(symbol, timeframe, timeout=1.0)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 过滤成功的结果
    valid_results = [r for r in results if not isinstance(r, Exception)]
    return valid_results

# 启用连接复用
client_config = {
    'connection_pool_size': 20,
    'keep_alive_timeout': 60,
    'enable_compression': True
}
```

### 调试工具

#### 1. 健康检查工具

```python
async def health_check():
    """全面的健康检查"""
    
    # 检查API服务器
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/api/v1/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API服务器: {data.get('status')}")
                else:
                    print(f"❌ API服务器: HTTP {response.status}")
    except Exception as e:
        print(f"❌ API服务器: {e}")
    
    # 检查缓存
    try:
        cache_manager = DataCacheManager('test_cache.db')
        await cache_manager.store_historical_data('TEST', '1', {'klines': []})
        cached = await cache_manager.get_historical_data('TEST', '1')
        if cached is not None:
            print("✅ 缓存系统: 正常")
        else:
            print("❌ 缓存系统: 异常")
    except Exception as e:
        print(f"❌ 缓存系统: {e}")
    
    # 检查TradingView连接
    try:
        client = EnhancedTradingViewClient()
        if await client.connect():
            print("✅ TradingView连接: 正常")
            await client.disconnect()
        else:
            print("❌ TradingView连接: 失败")
    except Exception as e:
        print(f"❌ TradingView连接: {e}")

# 运行健康检查
asyncio.run(health_check())
```

#### 2. 性能分析工具

```python
import time
from functools import wraps

def timing_decorator(func):
    """性能计时装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        print(f"{func.__name__} 执行时间: {end_time - start_time:.3f}秒")
        return result
    
    return wrapper

# 使用示例
@timing_decorator
async def timed_data_fetch(symbol, timeframe):
    return await data_source.get_historical_data(symbol, timeframe)
```

#### 3. 日志分析工具

```python
import logging
from collections import defaultdict

class PerformanceLogger:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    def log_request(self, symbol, timeframe, response_time, cache_hit):
        self.metrics['response_times'].append(response_time)
        self.metrics['cache_hits'].append(cache_hit)
        
        self.logger.info(f"请求: {symbol}:{timeframe}, "
                        f"响应时间: {response_time:.3f}s, "
                        f"缓存命中: {cache_hit}")
    
    def get_statistics(self):
        if not self.metrics['response_times']:
            return {}
        
        response_times = self.metrics['response_times']
        cache_hits = self.metrics['cache_hits']
        
        return {
            'avg_response_time': sum(response_times) / len(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'cache_hit_rate': sum(cache_hits) / len(cache_hits),
            'total_requests': len(response_times)
        }

# 使用示例
perf_logger = PerformanceLogger()

# 在数据获取时记录性能
async def monitored_data_fetch(symbol, timeframe):
    start_time = time.time()
    
    # 检查缓存
    cached_data = await cache_manager.get_historical_data(symbol, timeframe)
    cache_hit = cached_data is not None
    
    if not cache_hit:
        # 从API获取
        data = await api_client.get_data(symbol, timeframe)
    else:
        data = cached_data
    
    response_time = time.time() - start_time
    perf_logger.log_request(symbol, timeframe, response_time, cache_hit)
    
    return data

# 定期输出统计信息
async def print_statistics():
    while True:
        await asyncio.sleep(60)  # 每分钟输出一次
        stats = perf_logger.get_statistics()
        if stats:
            print(f"性能统计: {stats}")
```

## 📈 监控和告警

### Prometheus集成

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 定义指标
request_count = Counter('tradingview_requests_total', 'Total requests', ['symbol', 'timeframe'])
request_duration = Histogram('tradingview_request_duration_seconds', 'Request duration')
cache_hit_rate = Gauge('tradingview_cache_hit_rate', 'Cache hit rate')
data_quality_score = Gauge('tradingview_data_quality', 'Data quality score', ['symbol'])

class PrometheusMonitor:
    def __init__(self, port=9090):
        self.port = port
        start_http_server(port)
        print(f"Prometheus监控端口: {port}")
    
    def record_request(self, symbol, timeframe, duration, cache_hit):
        request_count.labels(symbol=symbol, timeframe=timeframe).inc()
        request_duration.observe(duration)
        
        # 更新缓存命中率（简化计算）
        current_rate = cache_hit_rate._value.get() or 0
        new_rate = (current_rate * 0.9) + (1.0 if cache_hit else 0.0) * 0.1
        cache_hit_rate.set(new_rate)
    
    def record_quality_score(self, symbol, score):
        data_quality_score.labels(symbol=symbol).set(score)

# 使用示例
monitor = PrometheusMonitor()

async def monitored_request(symbol, timeframe):
    start_time = time.time()
    
    # 执行请求
    cache_hit, data = await get_data_with_cache(symbol, timeframe)
    
    # 记录指标
    duration = time.time() - start_time
    monitor.record_request(symbol, timeframe, duration, cache_hit)
    
    # 记录质量得分
    if data and 'quality_score' in data:
        monitor.record_quality_score(symbol, data['quality_score'])
    
    return data
```

---

## 🎯 总结

TradingView模块外部集成指南提供了完整的集成方案，包括：

- **🔌 多种集成方式**: RESTful API、WebSocket、Python SDK
- **🗄️ 双层缓存架构**: 内存+SQLite，提供高性能数据访问
- **🛡️ 六维质量监控**: 全面的数据质量评估和告警机制
- **📊 完整示例代码**: 涵盖各种使用场景的示例
- **🛠️ 最佳实践指南**: 连接管理、缓存策略、错误处理
- **🔧 故障排除工具**: 健康检查、性能分析、日志监控

通过遵循本指南，您可以快速、可靠地将TradingView数据源集成到您的交易系统中，获得专业级的数据服务支持。