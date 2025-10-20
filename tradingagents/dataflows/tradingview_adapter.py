#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView适配器 - 集成TradingView框架到TradingAgents-CN项目
提供高级请求伪装和实时数据获取能力
"""

import asyncio
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
import sys
import time
import random
import json

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 添加TradingView框架路径
tv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'tradingview')
if tv_path not in sys.path:
    sys.path.insert(0, tv_path)

try:
    from tradingview import Client
    TRADINGVIEW_AVAILABLE = True
    logger.info("✅ TradingView框架导入成功")
except ImportError as e:
    logger.warning(f"⚠️ TradingView框架导入失败: {e}")
    TRADINGVIEW_AVAILABLE = False

class TradingViewDataProvider:
    """
    TradingView数据提供器
    使用TradingView WebSocket API获取实时和历史数据
    """

    def __init__(self):
        """初始化TradingView数据提供器"""
        self.client = None
        self.connected = False
        self.chart = None
        self.last_data = None
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载TradingView配置"""
        return {
            'token': os.getenv('TV_SESSION', ''),
            'signature': os.getenv('TV_SIGNATURE', ''),
            'server': os.getenv('TV_SERVER', 'data'),
            'location': os.getenv('TV_LOCATION', 'https://tradingview.com'),
            'timeout': int(os.getenv('TV_TIMEOUT', '30')),
            'max_retries': int(os.getenv('TV_MAX_RETRIES', '3')),
            'debug': os.getenv('TV_DEBUG', 'false').lower() == 'true'
        }

    async def _ensure_connection(self) -> bool:
        """确保连接已建立"""
        if not TRADINGVIEW_AVAILABLE:
            logger.error("❌ TradingView框架不可用")
            return False

        if not self.client or not self.connected:
            try:
                self.client = Client(
                    token=self._config['token'],
                    signature=self._config['signature'],
                    server=self._config['server'],
                    location=self._config['location'],
                    DEBUG=self._config['debug']
                )

                await self.client.connect()
                self.connected = True
                logger.info("✅ TradingView连接成功")
                return True

            except Exception as e:
                logger.error(f"❌ TradingView连接失败: {e}")
                self.connected = False
                return False

        return self.connected

    async def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取股票数据（TradingView方式）

        Args:
            symbol: 股票代码 (如: '000001', '600000', 'AAPL')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame: 标准格式的股票数据
        """
        if not await self._ensure_connection():
            return None

        try:
            # 转换股票代码为TradingView格式
            tv_symbol = self._convert_symbol_to_tv_format(symbol)
            if not tv_symbol:
                logger.error(f"❌ 无法转换股票代码: {symbol}")
                return None

            # 创建图表会话
            self.chart = self.client.Session.Chart()

            # 设置市场参数
            config = {
                'symbol': tv_symbol,
                'timeframe': 'D',  # 日线数据
                'range': 500,      # 获取500条数据
                'to': int(time.time()) if end_date else int(time.time())
            }

            # 如果指定了日期范围，计算range
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                days_diff = (end_dt - start_dt).days
                config['range'] = max(days_diff + 10, 30)  # 多获取一些数据确保覆盖
                config['to'] = int(end_dt.timestamp())

            logger.info(f"🔍 TradingView获取数据: {tv_symbol} ({start_date} 到 {end_date})")

            # 使用事件循环等待数据
            data = await self._fetch_data_with_timeout(config, timeout=self._config['timeout'])

            if data is not None and not data.empty:
                logger.info(f"✅ TradingView数据获取成功: {symbol}, {len(data)}条记录")
                return data
            else:
                logger.warning(f"⚠️ TradingView数据为空: {symbol}")
                return None

        except Exception as e:
            logger.error(f"❌ TradingView数据获取失败: {e}")
            return None

    async def _fetch_data_with_timeout(self, config: Dict, timeout: int = 30) -> Optional[pd.DataFrame]:
        """带超时的数据获取"""
        data_received = asyncio.Event()
        result_data = None

        def on_error(*err):
            logger.error(f"图表错误: {err}")
            data_received.set()

        def on_symbol_loaded():
            logger.info(f"市场 '{self.chart.infos.description}' 已加载")

        def on_update():
            nonlocal result_data
            if not self.chart.periods or not self.chart.periods[0]:
                return

            try:
                # 转换TradingView数据为标准格式
                df_data = []
                for period in self.chart.periods:
                    df_data.append({
                        'Date': datetime.fromtimestamp(period.time),
                        'Open': period.open,
                        'High': period.max,
                        'Low': period.min,
                        'Close': period.close,
                        'Volume': period.volume if hasattr(period, 'volume') else 0,
                        'Symbol': self._extract_symbol_from_tv_symbol(config['symbol'])
                    })

                if df_data:
                    df = pd.DataFrame(df_data)
                    df = df.sort_values('Date').reset_index(drop=True)

                    # 如果指定了日期范围，进行过滤
                    if 'range' in config and 'to' in config:
                        end_time = datetime.fromtimestamp(config['to'])
                        start_time = end_time - timedelta(days=config['range'])
                        df = df[(df['Date'] >= start_time) & (df['Date'] <= end_time)]

                    result_data = df
                    logger.info(f"TradingView获取到 {len(df)} 条K线数据")

                data_received.set()

            except Exception as e:
                logger.error(f"处理TradingView数据失败: {e}")
                data_received.set()

        # 设置回调
        self.chart.on_error = on_error
        self.chart.on_symbol_loaded = on_symbol_loaded
        self.chart.on_update = on_update

        # 设置市场
        self.chart.set_market(config['symbol'], {
            'timeframe': config['timeframe'],
            'range': config['range'],
            'to': config['to']
        })

        try:
            # 等待数据接收或超时
            await asyncio.wait_for(data_received.wait(), timeout=timeout)
            return result_data
        except asyncio.TimeoutError:
            logger.error(f"TradingView数据获取超时: {timeout}秒")
            return None
        finally:
            # 清理图表
            if self.chart:
                self.chart.delete()
                self.chart = None

    def _convert_symbol_to_tv_format(self, symbol: str) -> Optional[str]:
        """
        将股票代码转换为TradingView格式

        Args:
            symbol: 标准股票代码

        Returns:
            TradingView格式的股票代码
        """
        try:
            # A股代码转换
            if len(symbol) == 6 and symbol.isdigit():
                if symbol.startswith(('60', '68', '90')):
                    return f"SSE:{symbol}"
                elif symbol.startswith(('00', '30', '20')):
                    return f"SZSE:{symbol}"
                else:
                    return f"SSE:{symbol}"  # 默认上海

            # 港股代码转换
            elif symbol.endswith('.HK') or symbol.endswith('.hk'):
                clean_code = symbol.replace('.HK', '').replace('.hk', '').zfill(5)
                return f"HKEX:{clean_code}"

            # 美股代码
            elif symbol.replace('.', '').isalpha():
                # 检查是否已经在其他交易所格式
                if ':' in symbol:
                    return symbol
                else:
                    return f"NASDAQ:{symbol}" if symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META'] else f"NYSE:{symbol}"

            # 已经是TradingView格式
            elif ':' in symbol:
                return symbol

            else:
                logger.warning(f"未知的股票代码格式: {symbol}")
                return None

        except Exception as e:
            logger.error(f"股票代码转换失败: {e}")
            return None

    def _extract_symbol_from_tv_symbol(self, tv_symbol: str) -> str:
        """从TradingView格式提取标准股票代码"""
        try:
            if ':' in tv_symbol:
                return tv_symbol.split(':')[1]
            else:
                return tv_symbol
        except:
            return tv_symbol

    async def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        if not await self._ensure_connection():
            return {
                'symbol': symbol,
                'name': f'股票{symbol}',
                'exchange': '未知',
                'currency': 'CNY',
                'source': 'tradingview',
                'error': '连接失败'
            }

        try:
            tv_symbol = self._convert_symbol_to_tv_format(symbol)
            if not tv_symbol:
                return {
                    'symbol': symbol,
                    'name': f'股票{symbol}',
                    'exchange': '未知',
                    'currency': 'CNY',
                    'source': 'tradingview',
                    'error': '代码格式不支持'
                }

            # 创建临时图表获取信息
            chart = self.client.Session.Chart()

            info_received = asyncio.Event()
            stock_info = {}

            def on_error(*err):
                logger.error(f"获取股票信息错误: {err}")
                info_received.set()

            def on_symbol_loaded():
                try:
                    stock_info = {
                        'symbol': symbol,
                        'name': getattr(chart.infos, 'description', f'股票{symbol}'),
                        'exchange': getattr(chart.infos, 'exchange', '未知'),
                        'currency': getattr(chart.infos, 'currency_id', 'CNY'),
                        'source': 'tradingview',
                        'tv_symbol': tv_symbol
                    }
                except Exception as e:
                    logger.error(f"解析股票信息失败: {e}")
                    stock_info = {
                        'symbol': symbol,
                        'name': f'股票{symbol}',
                        'exchange': '未知',
                        'currency': 'CNY',
                        'source': 'tradingview',
                        'error': str(e)
                    }
                info_received.set()

            chart.on_error = on_error
            chart.on_symbol_loaded = on_symbol_loaded

            chart.set_market(tv_symbol, {'timeframe': 'D'})

            try:
                await asyncio.wait_for(info_received.wait(), timeout=10)
                return stock_info
            except asyncio.TimeoutError:
                logger.error(f"获取股票信息超时: {symbol}")
                return {
                    'symbol': symbol,
                    'name': f'股票{symbol}',
                    'exchange': '未知',
                    'currency': 'CNY',
                    'source': 'tradingview',
                    'error': '获取超时'
                }
            finally:
                chart.delete()

        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return {
                'symbol': symbol,
                'name': f'股票{symbol}',
                'exchange': '未知',
                'currency': 'CNY',
                'source': 'tradingview',
                'error': str(e)
            }

    async def close_connection(self):
        """关闭连接"""
        try:
            if self.chart:
                self.chart.delete()
                self.chart = None

            if self.client:
                await self.client.end()
                self.client = None
                self.connected = False
                logger.info("✅ TradingView连接已关闭")

        except Exception as e:
            logger.error(f"关闭TradingView连接失败: {e}")

# 同步适配器，兼容现有接口
class TradingViewSyncAdapter:
    """
    TradingView同步适配器
    提供同步接口，兼容现有的数据源管理器
    """

    def __init__(self):
        self.async_provider = TradingViewDataProvider()

    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> str:
        """
        获取股票数据（同步接口）

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的股票数据报告
        """
        try:
            # 运行异步函数
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            data = loop.run_until_complete(
                self.async_provider.get_stock_data(symbol, start_date, end_date)
            )

            if data is not None and not data.empty:
                return self._format_data_report(symbol, data, start_date, end_date)
            else:
                return f"❌ TradingView无法获取股票 {symbol} 的数据"

        except Exception as e:
            logger.error(f"TradingView同步数据获取失败: {e}")
            return f"❌ TradingView数据获取失败: {e}"

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息（同步接口）

        Args:
            symbol: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        try:
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(
                self.async_provider.get_stock_info(symbol)
            )

        except Exception as e:
            logger.error(f"TradingView同步信息获取失败: {e}")
            return {
                'symbol': symbol,
                'name': f'股票{symbol}',
                'exchange': '未知',
                'currency': 'CNY',
                'source': 'tradingview',
                'error': str(e)
            }

    def _format_data_report(self, symbol: str, data: pd.DataFrame, start_date: str, end_date: str) -> str:
        """
        格式化数据报告

        Args:
            symbol: 股票代码
            data: 股票数据
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的报告
        """
        try:
            if data.empty:
                return f"❌ 股票 {symbol} 无可用数据"

            # 计算统计信息
            latest_data = data.iloc[-1]
            first_data = data.iloc[0]

            latest_price = latest_data['Close']
            price_change = latest_price - first_data['Close']
            price_change_pct = (price_change / first_data['Close']) * 100 if first_data['Close'] != 0 else 0

            avg_volume = data['Volume'].mean() if 'Volume' in data.columns else 0
            max_price = data['High'].max()
            min_price = data['Low'].min()

            # 格式化输出
            report = f"""
📊 TradingView股票数据报告
==============================

股票信息:
- 代码: {symbol}
- 数据期间: {start_date or data['Date'].min().strftime('%Y-%m-%d')} 至 {end_date or data['Date'].max().strftime('%Y-%m-%d')}
- 交易天数: {len(data)}天

价格信息:
- 最新价格: ¥{latest_price:.2f}
- 期间涨跌: ¥{price_change:+.2f} ({price_change_pct:+.2f}%)
- 期间最高: ¥{max_price:.2f}
- 期间最低: ¥{min_price:.2f}

交易信息:
- 平均成交量: {avg_volume:,.0f}股
- 数据来源: TradingView

最近5个交易日:
"""

            # 添加最近5天的数据
            recent_data = data.tail(5)
            for _, row in recent_data.iterrows():
                date_str = row['Date'].strftime('%Y-%m-%d')
                volume = row.get('Volume', 0)
                report += f"- {date_str}: 开盘¥{row['Open']:.2f}, 收盘¥{row['Close']:.2f}, 成交量{volume:,.0f}\n"

            report += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += "数据来源: TradingView实时数据\n"

            return report

        except Exception as e:
            logger.error(f"格式化TradingView数据报告失败: {e}")
            return f"❌ 数据格式化失败: {e}"

# 便捷函数
def get_tradingview_adapter() -> TradingViewSyncAdapter:
    """获取TradingView适配器实例"""
    return TradingViewSyncAdapter()

# 测试函数
async def test_tradingview_integration():
    """测试TradingView集成"""
    if not TRADINGVIEW_AVAILABLE:
        print("❌ TradingView框架不可用，跳过测试")
        return

    print("🚀 TradingView集成测试开始")

    provider = TradingViewDataProvider()

    # 测试获取股票数据
    symbol = "000001"  # 平安银行
    start_date = "2025-09-01"
    end_date = "2025-10-16"

    print(f"📊 测试获取 {symbol} 数据...")
    data = await provider.get_stock_data(symbol, start_date, end_date)

    if data is not None and not data.empty:
        print(f"✅ 成功获取 {len(data)} 条数据")
        print(data.head())
    else:
        print("❌ 数据获取失败")

    # 测试获取股票信息
    print(f"\n📋 测试获取 {symbol} 信息...")
    info = await provider.get_stock_info(symbol)
    print(f"股票信息: {info}")

    # 关闭连接
    await provider.close_connection()
    print("✅ 测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_tradingview_integration())