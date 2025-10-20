# TradingView K线API 快速启动指南

## 🚀 一分钟快速启动

### 第1步: 安装依赖

```bash
pip install fastapi uvicorn
```

### 第2步: 启动服务

```bash
cd /Users/zerone/code/trading/chan.py
python -m tradingview.kline_api_server
```

你会看到:

```
==========================================
🚀 TradingView K线数据HTTP API服务
==========================================

📡 服务地址: http://0.0.0.0:8000
📚 API文档: http://0.0.0.0:8000/docs
📊 ReDoc文档: http://0.0.0.0:8000/redoc

示例请求:
  curl "http://0.0.0.0:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"
  curl "http://0.0.0.0:8000/klines?symbol=BTCUSDT&timeframe=15m&count=50"
  curl "http://0.0.0.0:8000/health"
  curl "http://0.0.0.0:8000/stats"

==========================================
按 Ctrl+C 停止服务
```

### 第3步: 测试请求

打开新终端，执行测试:

```bash
# 测试1: 健康检查
curl "http://localhost:8000/health"

# 测试2: 获取黄金15分钟K线
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=10"

# 测试3: 获取BTC K线（简化格式）
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15m&count=5&format=simple"
```

或者使用测试脚本:

```bash
chmod +x test_kline_api.sh
./test_kline_api.sh
```

### 第4步: 浏览器访问

在浏览器中打开: http://localhost:8000/docs

你会看到交互式API文档，可以直接在浏览器中测试所有接口。

## 📝 常用命令

### 启动服务

```bash
# 默认端口8000
python -m tradingview.kline_api_server

# 指定端口
python -m tradingview.kline_api_server --port 8080

# 开发模式（自动重载）
python -m tradingview.kline_api_server --reload

# 多进程模式
python -m tradingview.kline_api_server --workers 4
```

### API请求示例

```bash
# 1. 获取黄金15分钟K线
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"

# 2. 获取比特币1小时K线
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=1h&count=50&format=simple"

# 3. 批量获取多个品种
curl "http://localhost:8000/batch_klines?symbols=BTCUSDT,ETHUSDT&timeframe=15&count=20"

# 4. 获取高质量数据
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100&quality=financial"

# 5. 健康检查
curl "http://localhost:8000/health"

# 6. 服务统计
curl "http://localhost:8000/stats"
```

## 🎯 核心功能

### 1. 单品种K线获取

**最简单的请求**:
```bash
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"
```

**完整参数**:
```bash
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100&quality=production&use_cache=true&format=simple"
```

### 2. 批量获取

**获取多个品种**:
```bash
curl "http://localhost:8000/batch_klines?symbols=BINANCE:BTCUSDT,BINANCE:ETHUSDT,OANDA:XAUUSD&timeframe=15&count=50"
```

### 3. 不同时间框架

```bash
# 1分钟
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=1m&count=60"

# 15分钟
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15m&count=100"

# 1小时
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=1h&count=24"

# 4小时
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=4h&count=30"

# 日线
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=1d&count=365"
```

## 🔧 配置说明

### 品种格式

| 输入格式 | 自动转换为 | 说明 |
|---------|-----------|------|
| `OANDA:XAUUSD` | `OANDA:XAUUSD` | 标准格式，保持不变 |
| `BTCUSDT` | `BINANCE:BTCUSDT` | 自动添加BINANCE前缀 |
| `ETHUSDT` | `BINANCE:ETHUSDT` | 自动添加BINANCE前缀 |

### 时间框架格式

| 输入格式 | 标准格式 | 说明 |
|---------|---------|------|
| `1`, `1m`, `1min` | `1` | 1分钟 |
| `5`, `5m` | `5` | 5分钟 |
| `15`, `15m` | `15` | 15分钟 |
| `30`, `30m` | `30` | 30分钟 |
| `60`, `1h` | `60` | 1小时 |
| `240`, `4h` | `240` | 4小时 |
| `1D`, `1d` | `1D` | 日线 |
| `1W`, `1w` | `1W` | 周线 |
| `1M` | `1M` | 月线 |

### 质量等级

| 等级 | 质量要求 | 使用场景 |
|-----|---------|---------|
| `development` | ≥90% | 开发测试 |
| `production` | ≥95% | 生产环境（默认） |
| `financial` | ≥98% | 金融级交易 |

## 📊 响应格式

### Simple格式（推荐）

```json
{
  "success": true,
  "symbol": "OANDA:XAUUSD",
  "timeframe": "15",
  "count": 2,
  "data": [
    {
      "timestamp": 1699123456,
      "datetime": "2023-11-04T10:30:00",
      "open": 2645.50,
      "high": 2648.30,
      "low": 2644.20,
      "close": 2647.80,
      "volume": 1234.56
    },
    {
      "timestamp": 1699124356,
      "datetime": "2023-11-04T10:45:00",
      "open": 2647.80,
      "high": 2650.10,
      "low": 2646.50,
      "close": 2649.20,
      "volume": 2345.67
    }
  ]
}
```

### JSON格式（完整）

包含更多元数据，如质量指标、请求ID、响应时间等。

## 🐛 常见问题

### Q1: 服务启动失败

**问题**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**:
```bash
pip install fastapi uvicorn
```

### Q2: 端口被占用

**问题**: `Address already in use`

**解决**:
```bash
# 方法1: 使用其他端口
python -m tradingview.kline_api_server --port 8080

# 方法2: 停止占用8000端口的进程
lsof -i :8000
kill -9 <PID>
```

### Q3: 获取数据失败

**问题**: 返回500错误

**解决**:
```bash
# 1. 检查服务健康
curl "http://localhost:8000/health"

# 2. 查看服务日志
# 服务日志会显示详细错误信息

# 3. 检查TradingView连接
# 确保网络正常，TradingView可访问
```

### Q4: 数据质量低

**问题**: quality_score < 0.95

**解决**:
```bash
# 1. 不使用缓存，获取最新数据
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15&count=100&use_cache=false"

# 2. 降低质量要求
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15&count=100&quality=development"
```

## 🎓 进阶使用

### Python客户端示例

```python
import requests

# 获取K线数据
response = requests.get(
    "http://localhost:8000/klines",
    params={
        "symbol": "OANDA:XAUUSD",
        "timeframe": "15",
        "count": 100,
        "format": "simple"
    }
)

data = response.json()

if data["success"]:
    print(f"获取到 {data['count']} 条K线数据")
    for kline in data["data"][:5]:  # 打印前5条
        print(f"{kline['datetime']}: 开={kline['open']}, "
              f"高={kline['high']}, 低={kline['low']}, 收={kline['close']}")
else:
    print(f"获取失败: {data.get('error')}")
```

### JavaScript客户端示例

```javascript
// 使用fetch API
fetch('http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15&count=100&format=simple')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log(`获取到 ${data.count} 条K线数据`);
      data.data.forEach(kline => {
        console.log(`${kline.datetime}: ${kline.close}`);
      });
    }
  })
  .catch(error => console.error('Error:', error));
```

### 与缠论系统集成

```python
from tradingview.historical_kline_service import HistoricalKlineService
import requests

# 通过API获取数据
response = requests.get(
    "http://localhost:8000/klines",
    params={
        "symbol": "BINANCE:BTCUSDT",
        "timeframe": "15",
        "count": 500,
        "quality": "financial"
    }
)

klines = response.json()["data"]

# 转换为chanpy格式进行分析
# ... 后续缠论分析逻辑
```

## 📚 相关资源

- **详细文档**: [README_KLINE_API.md](./README_KLINE_API.md)
- **API交互文档**: http://localhost:8000/docs
- **源代码**: [kline_api_server.py](./kline_api_server.py)
- **服务层**: [historical_kline_service.py](./historical_kline_service.py)

## 🎉 开始使用

现在你已经了解了如何使用K线API服务，开始获取你需要的数据吧！

```bash
# 启动服务
python -m tradingview.kline_api_server

# 新终端测试
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"
```

祝你使用愉快！🚀