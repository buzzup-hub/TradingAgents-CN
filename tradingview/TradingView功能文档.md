# TradingView API 客户端功能文档

## 1. 项目概述

这个Python库是一个非官方的TradingView API客户端，允许用户通过代码与TradingView平台进行交互。主要功能包括获取实时和历史市场数据、使用内置或Pine指标进行技术分析、访问图表绘图等。

### 1.1 功能特点

- 连接到TradingView WebSocket服务器
- 获取实时和历史K线数据
- 使用内置和自定义Pine指标进行技术分析
- 访问图表绘图和标记
- 使用回放模式进行历史数据分析
- 搜索市场和指标
- 管理Pine指标权限

## 2. 安装与配置

### 2.1 安装方法

目前通过源码安装（未来会发布到pip）：

```bash
# 克隆项目或直接使用当前目录
```

### 2.2 认证配置

使用TradingView API需要提供会话令牌和签名，可以通过以下方式获取：

1. 登录到TradingView网站
2. 在浏览器控制台中运行以下命令：
   ```js
   console.log(JSON.stringify({
     session: window.initData.user.session_token,
     signature: window.initData.user.auth_token
   }));
   ```

3. 通过环境变量设置：

```bash
export TV_SESSION=your_session_token
export TV_SIGNATURE=your_signature
```

## 3. 核心概念与组件

### 3.1 主要组件

- `Client`: 核心客户端，负责WebSocket连接管理
- `ChartSession`: 图表会话，处理K线数据和图表操作
- `Study`: 指标研究，用于添加和获取技术指标数据
- `BuiltInIndicator`: 内置指标类
- `PineIndicator`: Pine脚本指标类
- `QuoteSession`: 行情会话，处理实时报价

### 3.2 数据流程

1. 创建Client连接到TradingView服务器
2. 建立图表会话(ChartSession)
3. 设置交易市场和时间周期
4. 通过回调函数处理数据更新
5. 可选：添加技术指标研究(Study)

## 4. 基本使用方法

### 4.1 创建客户端并连接

```python
import asyncio
import os
from tradingview import Client

async def main():
    # 创建客户端并连接
    client = Client(
        token=os.environ.get('TV_SESSION'),
        signature=os.environ.get('TV_SIGNATURE')
    )
    
    await client.connect()
    
    # 使用完毕后关闭连接
    await client.end()

if __name__ == '__main__':
    asyncio.run(main())
```

### 4.2 获取实时K线数据

```python
# 创建图表会话
chart = client.Session.Chart()

# 设置市场和参数
chart.set_market('BINANCE:BTCUSDT', {
    'timeframe': '1D',  # 日线图表
})

# 处理数据更新
def on_update():
    if not chart.periods or not chart.periods[0]:
        return
    
    latest = chart.periods[0]
    print(f"最新价格: {latest.close}, 时间: {latest.time}")

# 注册更新回调
chart.on_update(on_update)
```

### 4.3 获取历史K线数据

```python
# 设置市场和参数
chart.set_market('BINANCE:BTCUSDT', {
    'timeframe': '60',  # 60分钟时间周期
    'range': 500,       # 获取500根K线
})

# 处理加载完成的数据
def on_update():
    klines = chart.periods
    print(f"获取到 {len(klines)} 条K线数据")
    
    # 处理K线数据
    for kline in klines:
        print(f"时间: {kline.time}, 开: {kline.open}, 高: {kline.high}, "
              f"低: {kline.low}, 收: {kline.close}, 成交量: {kline.volume}")

chart.on_update(on_update)
```

### 4.4 使用技术指标

```python
from tradingview import get_indicator

async def add_indicator():
    # 获取内置EMA指标
    ema = await get_indicator('STD;EMA')
    ema.set_option('Length', 14)  # 设置EMA参数长度为14
    
    # 创建指标研究
    ema_study = chart.Study(ema)
    
    # 处理指标数据更新
    def on_ema_update():
        if not ema_study.periods:
            return
        
        for period in ema_study.periods:
            print(f"时间: {period.time}, EMA值: {period.plot_0}")
    
    ema_study.on_update(on_ema_update)
```

### 4.5 使用回放模式

回放模式允许模拟历史数据的逐步加载：

```python
# 启动回放模式
await chart.replay_start(1000)  # 每1000毫秒前进一步

# 前进指定步数
await chart.replay_step(5)  # 前进5步

# 停止回放
await chart.replay_stop()
```

## 5. 高级用法

### 5.1 使用Pine指标

```python
from tradingview import get_indicator

async def use_pine_indicator():
    # 获取Pine指标（假设已有权限）
    pine = await get_indicator('PUB;YOUR_PINE_ID')
    
    # 设置指标参数
    pine.set_input('length', 20)
    
    # 创建指标研究
    pine_study = chart.Study(pine)
    
    # 处理指标数据
    def on_pine_update():
        if not pine_study.periods:
            return
            
        print("Pine指标数据已更新")
    
    pine_study.on_update(on_pine_update)
```

### 5.2 多图表同步获取

```python
async def fetch_multiple_symbols():
    # 创建多个图表会话
    btc_chart = client.Session.Chart()
    eth_chart = client.Session.Chart()
    
    # 设置不同的交易对
    btc_chart.set_market('BINANCE:BTCUSDT', {'timeframe': '1D'})
    eth_chart.set_market('BINANCE:ETHUSDT', {'timeframe': '1D'})
    
    # 等待数据加载
    await asyncio.sleep(5)
    
    # 获取并比较数据
    btc_price = btc_chart.periods[0].close if btc_chart.periods else None
    eth_price = eth_chart.periods[0].close if eth_chart.periods else None
    
    print(f"BTC价格: {btc_price}, ETH价格: {eth_price}")
```

### 5.3 保存数据到文件

```python
import json
from datetime import datetime

def save_klines_to_file(klines, filename):
    # 格式化K线数据
    data = [{
        'time': k.time,
        'datetime': datetime.fromtimestamp(k.time).isoformat(),
        'open': k.open,
        'high': k.max,
        'low': k.min,
        'close': k.close,
        'volume': k.volume
    } for k in klines]
    
    # 保存到JSON文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"数据已保存到文件: {filename}")
```

## 6. 错误处理与调试

### 6.1 常见错误处理

```python
# 注册错误处理回调
def on_error(*err):
    print('错误:', *err)
    # 可以根据错误类型进行不同处理
    if 'symbol_error' in str(err):
        print("交易对不存在或无法访问")
    elif 'auth' in str(err).lower():
        print("认证失败，请检查token和signature")

# 设置到图表会话
chart.on_error(on_error)

# 设置到客户端
client.on_error(on_error)
```

### 6.2 调试模式

```python
# 启用调试模式
client = Client(
    token=os.environ.get('TV_SESSION'),
    signature=os.environ.get('TV_SIGNATURE'),
    DEBUG=True  # 启用调试日志
)
```

## 7. 使用示例

项目包含多个示例脚本，可以在`examples`目录中查看：

- `simple_chart.py`: 基本图表数据获取
- `historical_klines.py`: 获取历史K线数据
- `builtin_indicator.py`: 使用内置指标
- `private_indicators.py`: 使用私有Pine指标
- `replay_mode.py`: 使用回放模式
- `search_example.py`: 搜索市场和指标
- `drawings_example.py`: 获取图表绘图

## 8. 注意事项

- 这是一个非官方API客户端，不受TradingView官方支持
- 功能可能随时变化，取决于TradingView平台的API变更
- 使用时请遵守TradingView的服务条款
- 获取大量历史数据可能需要登录账户并有适当的权限

## 9. 故障排除

### 9.1 无法连接到服务器

- 检查网络连接
- 确认TradingView服务是否可访问
- 验证令牌和签名是否正确设置

### 9.2 数据获取失败

- 确认交易对符号格式正确（如`BINANCE:BTCUSDT`）
- 检查时间周期是否有效
- 检查是否有权限访问所请求的数据

### 9.3 指标添加失败

- 确认指标ID是否正确
- 检查是否有权限使用该指标
- 验证指标参数是否正确设置

## 10. 进阶开发

如需扩展或修改此库的功能，以下是主要的模块结构：

- `client.py`: WebSocket客户端核心
- `chart.py`: 图表会话和研究模块导出
- `chart/session.py`: 图表会话实现
- `chart/study.py`: 指标研究实现
- `protocol.py`: WebSocket协议处理
- `utils.py`: 工具函数
- `types.py`: 类型定义
- `misc_requests.py`: 辅助HTTP请求

通过理解这些模块的功能和交互方式，开发者可以根据需要进行功能扩展或定制。 