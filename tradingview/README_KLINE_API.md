# TradingView K线数据 HTTP API 服务

专业的TradingView历史K线数据HTTP API服务，提供RESTful接口获取实时和历史K线数据。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn
```

### 2. 启动服务

```bash
# 默认端口 8000
python -m tradingview.kline_api_server

# 指定端口
python -m tradingview.kline_api_server --port 8080

# 开发模式（热重载）
python -m tradingview.kline_api_server --reload
```

### 3. 访问API文档

服务启动后，访问以下地址查看交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API接口说明

### 1. 获取K线数据

**端点**: `GET /klines`

**参数**:
- `symbol` (必需): 交易品种
  - 格式: `交易所:品种`
  - 示例: `OANDA:XAUUSD`, `BINANCE:BTCUSDT`
  - 如果没有交易所前缀，默认为`BINANCE`

- `timeframe` (可选): 时间框架，默认`15`
  - 支持格式: `1`, `5`, `15`, `30`, `60`, `240`, `1D`, `1W`, `1M`
  - 也支持: `1m`, `5m`, `15m`, `1h`, `4h`, `1d` (自动转换)

- `count` (可选): K线数量，默认`100`，范围`1-5000`

- `quality` (可选): 质量等级，默认`production`
  - `development`: ≥90%质量
  - `production`: ≥95%质量
  - `financial`: ≥98%质量

- `use_cache` (可选): 是否使用缓存，默认`true`

- `format` (可选): 返回格式，默认`json`
  - `json`: 完整JSON格式（包含元数据）
  - `simple`: 简化格式（仅K线数据）

**请求示例**:

```bash
# 基础请求
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"

# 使用简化格式
curl "http://localhost:8000/klines?symbol=BINANCE:BTCUSDT&timeframe=15m&count=50&format=simple"

# 金融级质量
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=1h&count=200&quality=financial"

# 不使用缓存
curl "http://localhost:8000/klines?symbol=ETHUSDT&timeframe=5m&count=100&use_cache=false"
```

**响应示例** (simple格式):

```json
{
  "success": true,
  "symbol": "OANDA:XAUUSD",
  "timeframe": "15",
  "count": 3,
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
    },
    {
      "timestamp": 1699125256,
      "datetime": "2023-11-04T11:00:00",
      "open": 2649.20,
      "high": 2651.50,
      "low": 2648.00,
      "close": 2650.30,
      "volume": 3456.78
    }
  ]
}
```

**响应示例** (json格式):

```json
{
  "success": true,
  "request_id": "req_1699123456789",
  "symbol": "OANDA:XAUUSD",
  "timeframe": "15",
  "status": "completed",
  "klines": [...],
  "metadata": {
    "quality_metrics": {
      "completeness_rate": 1.0,
      "accuracy_rate": 1.0,
      "consistency_rate": 0.99,
      "overall_quality": 0.996
    },
    "source": "tradingview"
  },
  "quality_score": 0.996,
  "error_message": null,
  "fetch_time": "2023-11-04T10:30:00",
  "response_time_ms": 234.56
}
```

### 2. 批量获取K线数据

**端点**: `GET /batch_klines`

**参数**:
- `symbols` (必需): 品种列表，逗号分隔
  - 示例: `BINANCE:BTCUSDT,BINANCE:ETHUSDT,OANDA:XAUUSD`
  - 最多50个品种

- 其他参数同 `/klines` 接口

**请求示例**:

```bash
curl "http://localhost:8000/batch_klines?symbols=BINANCE:BTCUSDT,BINANCE:ETHUSDT,OANDA:XAUUSD&timeframe=15&count=50"
```

**响应示例**:

```json
{
  "success": true,
  "total": 3,
  "results": [
    {
      "symbol": "BINANCE:BTCUSDT",
      "timeframe": "15",
      "status": "completed",
      "count": 50,
      "quality_score": 0.98,
      "data": [...],
      "error": null
    },
    {
      "symbol": "BINANCE:ETHUSDT",
      "timeframe": "15",
      "status": "completed",
      "count": 50,
      "quality_score": 0.97,
      "data": [...],
      "error": null
    },
    {
      "symbol": "OANDA:XAUUSD",
      "timeframe": "15",
      "status": "completed",
      "count": 50,
      "quality_score": 0.99,
      "data": [...],
      "error": null
    }
  ]
}
```

### 3. 健康检查

**端点**: `GET /health`

**请求示例**:

```bash
curl "http://localhost:8000/health"
```

**响应示例**:

```json
{
  "status": "healthy",
  "service": "kline_api",
  "timestamp": "2023-11-04T10:30:00",
  "initialized": true
}
```

### 4. 服务统计

**端点**: `GET /stats`

**请求示例**:

```bash
curl "http://localhost:8000/stats"
```

**响应示例**:

```json
{
  "success": true,
  "stats": {
    "total_requests": 150,
    "successful_requests": 145,
    "failed_requests": 5,
    "cache_hits": 80,
    "cache_misses": 70,
    "success_rate": 0.967,
    "cache_hit_rate": 0.533,
    "avg_response_time_ms": 234.56,
    "p95_response_time_ms": 450.00,
    "p99_response_time_ms": 680.00
  },
  "timestamp": "2023-11-04T10:30:00"
}
```

## 🎯 使用场景

### 场景1: 获取黄金15分钟K线

```bash
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15m&count=100"
```

### 场景2: 获取BTC 1小时K线（简化格式）

```bash
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=1h&count=200&format=simple"
```

### 场景3: 批量获取多个加密货币

```bash
curl "http://localhost:8000/batch_klines?symbols=BTCUSDT,ETHUSDT,BNBUSDT&timeframe=15&count=50"
```

### 场景4: 获取高质量日线数据

```bash
curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=1d&count=365&quality=financial"
```

## 🔧 配置选项

### 启动参数

```bash
python -m tradingview.kline_api_server --help

参数:
  --host HOST         监听地址 (默认: 0.0.0.0)
  --port PORT         监听端口 (默认: 8000)
  --reload            启用热重载（开发模式）
  --workers WORKERS   工作进程数 (默认: 1)
```

### 生产环境部署

```bash
# 多进程模式
python -m tradingview.kline_api_server --host 0.0.0.0 --port 8000 --workers 4

# 使用Gunicorn（推荐生产环境）
pip install gunicorn
gunicorn tradingview.kline_api_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info
```

## 🐳 Docker部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "tradingview.kline_api_server", "--host", "0.0.0.0", "--port", "8000"]
```

构建和运行:

```bash
# 构建镜像
docker build -t tradingview-kline-api .

# 运行容器
docker run -d -p 8000:8000 --name kline-api tradingview-kline-api
```

## 📊 性能特性

### 缓存机制
- **智能缓存**: 自动缓存历史数据，大幅提升响应速度
- **缓存命中**: 缓存命中的请求响应时间 < 10ms
- **自动更新**: 缓存数据自动过期和刷新

### 质量保证
- **四级验证**: 完整性、准确性、一致性、及时性
- **质量评分**: 每个响应包含质量评分指标
- **自动过滤**: 自动过滤异常数据

### 并发控制
- **请求限流**: 自动控制并发请求数
- **批量优化**: 批量请求自动合并处理
- **超时保护**: 请求超时自动重试

## 🔍 监控和日志

### 日志级别

服务使用标准Python logging，日志级别:
- `INFO`: 正常请求和响应
- `WARNING`: 数据质量警告
- `ERROR`: 请求失败和错误

### 监控指标

通过 `/stats` 接口获取:
- 请求总数、成功率、失败率
- 缓存命中率
- 平均响应时间、P95、P99
- 数据质量统计

## ⚠️ 注意事项

### 1. TradingView认证

服务需要TradingView认证信息，请确保:
- 已配置TradingView账号（参考 `tradingview/auth_config.py`）
- 或使用匿名模式（功能受限）

### 2. 品种格式

品种符号格式要求:
- 标准格式: `交易所:品种` (例如: `OANDA:XAUUSD`)
- 简化格式: `品种` (自动添加`BINANCE:`前缀)

### 3. 时间框架

支持的时间框架:
- 分钟: `1`, `5`, `15`, `30`, `60` (或 `1m`, `5m`, `15m`, `30m`, `1h`)
- 小时: `120`, `180`, `240` (或 `2h`, `3h`, `4h`)
- 日周月: `1D`, `1W`, `1M` (或 `1d`, `1w`, `1M`)

### 4. 数据限制

- 单次请求: 最多5000条K线
- 批量请求: 最多50个品种
- 请求频率: 建议控制在每秒10次以内

## 🐛 故障排除

### 问题1: 服务启动失败

```bash
# 检查依赖
pip install fastapi uvicorn

# 检查端口占用
lsof -i :8000
```

### 问题2: 数据获取失败

```bash
# 检查TradingView连接
curl "http://localhost:8000/health"

# 查看详细日志
python -m tradingview.kline_api_server --reload
```

### 问题3: 响应慢

```bash
# 启用缓存
curl "http://localhost:8000/klines?symbol=BTCUSDT&timeframe=15&use_cache=true"

# 查看统计信息
curl "http://localhost:8000/stats"
```

## 📚 相关文档

- [TradingView模块架构](./CLAUDE.md)
- [历史K线服务源码](./historical_kline_service.py)
- [使用示例](./examples/historical_kline_example.py)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

## 📝 开发计划

- [x] 基础K线数据API
- [x] 批量获取接口
- [x] 数据质量验证
- [x] 智能缓存机制
- [ ] WebSocket实时推送
- [ ] 数据订阅机制
- [ ] 认证和权限控制
- [ ] API限流和配额
- [ ] 数据导出功能

---

**🎯 核心特性**: 专业、高性能、高质量的TradingView K线数据HTTP API服务