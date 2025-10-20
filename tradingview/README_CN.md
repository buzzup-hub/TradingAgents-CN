# TradingView API 客户端

这个Python库提供了一个非官方的TradingView API客户端，允许您：

- 连接到TradingView WebSocket服务器
- 获取实时和历史市场数据
- 使用内置和Pine指标进行技术分析
- 访问图表绘图
- 使用回放模式进行历史数据分析
- 搜索市场和指标
- 管理Pine指标权限

## 文档索引

本项目包含以下文档，帮助您了解和使用TradingView API客户端：

1. **[快速入门指南](快速入门指南.md)** - 新手必读，通过简单示例快速入门
2. **[TradingView功能文档](TradingView功能文档.md)** - 详细介绍所有功能和API使用方法
3. **[TradingView逻辑功能分析](TradingView逻辑功能分析.md)** - 深入分析内部实现原理和设计

## 基本使用

### 认证

要使用TradingView API，您需要提供会话令牌和签名：

1. 登录到TradingView网站
2. 在浏览器控制台中运行以下命令：
   ```js
   console.log(JSON.stringify({
     session: window.initData.user.session_token,
     signature: window.initData.user.auth_token
   }));
   ```

或者，您可以使用环境变量：

```bash
export TV_SESSION=your_session_token
export TV_SIGNATURE=your_signature
```

### 简单示例

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
    
    # 创建图表并获取数据
    chart = client.Session.Chart()
    chart.set_market('BINANCE:BTCUSDT', {
        'timeframe': '1D'
    })
    
    # 设置回调函数
    def on_error(err):
        print("错误:", err)
        asyncio.create_task(client.end())
    
    def on_symbol_loaded():
        print("图表已准备就绪!")
    
    def on_update():
        if not chart.periods:
            return
        print(f"获取到{len(chart.periods)}个K线数据")
        print(f"最新价格: {chart.periods[0].close}")
    
    chart.on_error = on_error
    chart.on_symbol_loaded = on_symbol_loaded
    chart.on_update = on_update
    
    # 等待30秒然后关闭
    await asyncio.sleep(30)
    chart.delete()
    await client.end()

if __name__ == '__main__':
    asyncio.run(main())
```

## 示例目录

在 `examples` 目录中有更多高级用法的示例：

- `simple_chart.py`: 基本图表数据获取
- `historical_klines.py`: 获取历史K线数据
- `builtin_indicator.py`: 使用内置指标
- `private_indicators.py`: 使用私有Pine指标
- 以及更多...

## 注意事项

- 这是一个非官方API客户端，不受TradingView官方支持
- 功能可能随时变化，取决于TradingView的API变更
- 使用此库时请遵守TradingView的服务条款

## 贡献

欢迎提交问题和拉取请求！

## 许可证

MIT许可证 