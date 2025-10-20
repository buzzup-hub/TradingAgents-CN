#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView与trading_core集成适配器
实现数据格式转换、实时数据适配和系统集成
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum, auto

from config.logging_config import get_logger

logger = get_logger(__name__)


class DataSourceStatus(Enum):
    """数据源状态"""
    INITIALIZING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()
    RECONNECTING = auto()


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = auto()  # 优秀
    GOOD = auto()       # 良好  
    FAIR = auto()       # 一般
    POOR = auto()       # 较差
    CRITICAL = auto()   # 危险


@dataclass
class MarketDataPoint:
    """标准化市场数据点"""
    symbol: str
    timeframe: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    # 数据质量信息
    quality_score: float = 1.0
    source: str = "tradingview"
    latency_ms: float = 0.0
    
    # 元数据
    is_complete: bool = True
    is_realtime: bool = False
    sequence_id: Optional[int] = None


@dataclass
class DataSourceMetrics:
    """数据源指标"""
    symbol: str
    connection_status: DataSourceStatus = DataSourceStatus.DISCONNECTED
    last_update_time: float = 0.0
    
    # 性能指标
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0
    
    # 数据质量指标
    data_quality: DataQuality = DataQuality.EXCELLENT
    missing_data_count: int = 0
    invalid_data_count: int = 0
    
    # 连接指标
    connection_uptime: float = 0.0
    reconnection_count: int = 0
    last_error: Optional[str] = None


class TradingViewDataConverter:
    """TradingView数据转换器"""
    
    def __init__(self):
        self.conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0
        }
        
    def convert_kline_to_market_data(self, tv_kline: Dict[str, Any], 
                                   symbol: str, timeframe: str = "15m") -> Optional[MarketDataPoint]:
        """
        将TradingView K线数据转换为MarketDataPoint
        
        Args:
            tv_kline: TradingView K线数据
            symbol: 交易品种
            timeframe: 时间框架
            
        Returns:
            MarketDataPoint: 标准化市场数据点
        """
        try:
            self.conversion_stats['total_conversions'] += 1
            
            # 验证必需字段
            required_fields = ['time', 'open', 'high', 'low', 'close']
            if not all(field in tv_kline for field in required_fields):
                logger.warning(f"TradingView数据缺少必需字段: {tv_kline}")
                return None
                
            # 数据类型转换和验证
            timestamp = float(tv_kline['time'])
            open_price = float(tv_kline['open'])
            high_price = float(tv_kline['high'])
            low_price = float(tv_kline['low'])
            close_price = float(tv_kline['close'])
            volume = float(tv_kline.get('volume', 0))
            
            # 基础数据验证
            if not self._validate_ohlc_data(open_price, high_price, low_price, close_price):
                logger.warning(f"TradingView数据OHLC验证失败: {tv_kline}")
                self.conversion_stats['failed_conversions'] += 1
                return None
            
            # 计算数据质量分数
            quality_score = self._calculate_quality_score(tv_kline)
            
            # 检查是否为实时数据 (时间戳在5分钟内)
            current_time = time.time()
            is_realtime = (current_time - timestamp) < 300
            
            market_data = MarketDataPoint(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                quality_score=quality_score,
                source="tradingview",
                is_realtime=is_realtime,
                is_complete=True
            )
            
            self.conversion_stats['successful_conversions'] += 1
            return market_data
            
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"TradingView数据转换失败: {e}, 原始数据: {tv_kline}")
            self.conversion_stats['failed_conversions'] += 1
            return None
        except Exception as e:
            logger.error(f"TradingView数据转换异常: {e}")
            self.conversion_stats['failed_conversions'] += 1
            return None
    
    def convert_to_chanpy_format(self, market_data_list: List[MarketDataPoint]) -> Dict[str, List]:
        """
        将MarketDataPoint列表转换为chanpy格式
        
        Args:
            market_data_list: MarketDataPoint列表
            
        Returns:
            Dict: chanpy格式数据
        """
        try:
            # 按时间框架分组
            timeframe_data = defaultdict(list)
            
            for data_point in market_data_list:
                # 转换为chanpy KLine_Unit格式
                kline_dict = {
                    'time': data_point.timestamp,
                    'open': data_point.open,
                    'high': data_point.high,
                    'low': data_point.low,
                    'close': data_point.close,
                    'volume': data_point.volume
                }
                
                # 根据时间框架分类
                timeframe_key = self._map_timeframe_to_chanpy(data_point.timeframe)
                timeframe_data[timeframe_key].append(kline_dict)
            
            # 按时间戳排序
            for timeframe in timeframe_data:
                timeframe_data[timeframe].sort(key=lambda x: x['time'])
            
            return dict(timeframe_data)
            
        except Exception as e:
            logger.error(f"chanpy格式转换失败: {e}")
            return {}
    
    def convert_to_trading_core_format(self, market_data: MarketDataPoint) -> Dict[str, Any]:
        """
        转换为trading_core标准格式
        
        Args:
            market_data: MarketDataPoint
            
        Returns:
            Dict: trading_core格式数据
        """
        try:
            return {
                'symbol': market_data.symbol,
                'timeframe': market_data.timeframe,
                'timestamp': market_data.timestamp,
                'datetime': datetime.fromtimestamp(market_data.timestamp).isoformat(),
                'ohlcv': {
                    'open': market_data.open,
                    'high': market_data.high,
                    'low': market_data.low,
                    'close': market_data.close,
                    'volume': market_data.volume
                },
                'metadata': {
                    'quality_score': market_data.quality_score,
                    'source': market_data.source,
                    'latency_ms': market_data.latency_ms,
                    'is_realtime': market_data.is_realtime,
                    'is_complete': market_data.is_complete
                }
            }
            
        except Exception as e:
            logger.error(f"trading_core格式转换失败: {e}")
            return {}
    
    def _validate_ohlc_data(self, open_price: float, high_price: float, 
                          low_price: float, close_price: float) -> bool:
        """验证OHLC数据逻辑关系"""
        try:
            # 检查价格为正数
            if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
                return False
            
            # 检查高低价关系
            if high_price < max(open_price, close_price):
                return False
            if low_price > min(open_price, close_price):
                return False
            
            # 检查价格变动是否过于极端
            price_range = high_price - low_price
            avg_price = (high_price + low_price) / 2
            if avg_price > 0 and (price_range / avg_price) > 0.5:  # 50%的价格变动
                logger.warning("价格变动过于极端")
                return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_quality_score(self, kline_data: Dict) -> float:
        """计算数据质量分数"""
        try:
            score = 1.0
            
            # 检查数据完整性
            required_fields = ['time', 'open', 'high', 'low', 'close']
            missing_fields = sum(1 for field in required_fields if field not in kline_data)
            score *= (1 - missing_fields * 0.2)
            
            # 检查成交量数据
            if 'volume' not in kline_data or kline_data['volume'] <= 0:
                score *= 0.9  # 缺少成交量数据扣10分
            
            # 检查时间戳新鲜度
            current_time = time.time()
            time_diff = current_time - float(kline_data.get('time', 0))
            if time_diff > 3600:  # 超过1小时
                score *= 0.8
            elif time_diff > 300:  # 超过5分钟
                score *= 0.95
            
            return max(0.0, min(1.0, score))
            
        except Exception:
            return 0.5  # 默认中等质量
    
    def _map_timeframe_to_chanpy(self, timeframe: str) -> str:
        """映射时间框架到chanpy格式"""
        mapping = {
            '1m': 'K_1M',
            '5m': 'K_5M', 
            '15m': 'K_15M',
            '30m': 'K_30M',
            '1h': 'K_1H',
            '4h': 'K_4H',
            '1d': 'K_DAY',
            '1w': 'K_WEEK'
        }
        return mapping.get(timeframe, 'K_15M')
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        total = self.conversion_stats['total_conversions']
        if total == 0:
            return {'success_rate': 0.0, **self.conversion_stats}
        
        success_rate = self.conversion_stats['successful_conversions'] / total
        return {
            'success_rate': success_rate,
            **self.conversion_stats
        }


class RealtimeDataAdapter:
    """实时数据适配器"""
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.data_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=buffer_size))
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.metrics: Dict[str, DataSourceMetrics] = {}
        self.converter = TradingViewDataConverter()
        
        # 实时数据统计
        self.realtime_stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_dropped': 0,
            'average_processing_time_ms': 0.0
        }
        
    async def process_realtime_update(self, symbol: str, tv_data: Dict[str, Any]) -> bool:
        """
        处理实时数据更新
        
        Args:
            symbol: 交易品种
            tv_data: TradingView原始数据
            
        Returns:
            bool: 处理是否成功
        """
        try:
            start_time = time.perf_counter()
            self.realtime_stats['messages_received'] += 1
            
            # 初始化或更新指标
            if symbol not in self.metrics:
                self.metrics[symbol] = DataSourceMetrics(symbol=symbol)
            
            metrics = self.metrics[symbol]
            metrics.total_requests += 1
            
            # 转换数据格式
            market_data = self.converter.convert_kline_to_market_data(tv_data, symbol)
            
            if not market_data:
                metrics.failed_requests += 1
                metrics.invalid_data_count += 1
                self.realtime_stats['messages_dropped'] += 1
                return False
            
            # 设置延迟信息
            processing_time = (time.perf_counter() - start_time) * 1000
            market_data.latency_ms = processing_time
            
            # 更新指标
            metrics.successful_requests += 1
            metrics.last_update_time = time.time()
            metrics.connection_status = DataSourceStatus.CONNECTED
            
            # 计算平均延迟
            if metrics.successful_requests > 0:
                metrics.average_latency_ms = (
                    (metrics.average_latency_ms * (metrics.successful_requests - 1) + processing_time) 
                    / metrics.successful_requests
                )
            
            # 更新数据质量评级
            self._update_data_quality(metrics, market_data.quality_score)
            
            # 添加到缓冲区
            self.data_buffers[symbol].append(market_data)
            
            # 通知订阅者
            await self._notify_subscribers(symbol, market_data)
            
            # 更新统计
            self.realtime_stats['messages_processed'] += 1
            self._update_processing_time_stats(processing_time)
            
            logger.debug(f"处理实时数据成功: {symbol}, 延迟: {processing_time:.2f}ms")
            return True
            
        except Exception as e:
            logger.error(f"处理实时数据失败 {symbol}: {e}")
            if symbol in self.metrics:
                self.metrics[symbol].failed_requests += 1
                self.metrics[symbol].last_error = str(e)
            
            self.realtime_stats['messages_dropped'] += 1
            return False
    
    def subscribe_to_symbol(self, symbol: str, callback: Callable[[MarketDataPoint], None]) -> bool:
        """
        订阅品种数据更新
        
        Args:
            symbol: 交易品种
            callback: 数据回调函数
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            self.subscribers[symbol].append(callback)
            logger.info(f"订阅品种数据成功: {symbol}, 当前订阅者: {len(self.subscribers[symbol])}")
            return True
            
        except Exception as e:
            logger.error(f"订阅品种数据失败 {symbol}: {e}")
            return False
    
    def unsubscribe_from_symbol(self, symbol: str, callback: Callable[[MarketDataPoint], None]) -> bool:
        """
        取消订阅品种数据
        
        Args:
            symbol: 交易品种
            callback: 数据回调函数
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            if symbol in self.subscribers and callback in self.subscribers[symbol]:
                self.subscribers[symbol].remove(callback)
                logger.info(f"取消订阅成功: {symbol}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"取消订阅失败 {symbol}: {e}")
            return False
    
    async def _notify_subscribers(self, symbol: str, market_data: MarketDataPoint) -> None:
        """通知订阅者"""
        try:
            callbacks = self.subscribers.get(symbol, [])
            
            if callbacks:
                # 并发通知所有订阅者
                tasks = []
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            tasks.append(asyncio.create_task(callback(market_data)))
                        else:
                            # 同步回调在线程池中执行
                            tasks.append(asyncio.create_task(
                                asyncio.get_event_loop().run_in_executor(None, callback, market_data)
                            ))
                    except Exception as e:
                        logger.error(f"创建回调任务失败: {e}")
                
                # 等待所有回调完成
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
        except Exception as e:
            logger.error(f"通知订阅者失败: {e}")
    
    def _update_data_quality(self, metrics: DataSourceMetrics, quality_score: float) -> None:
        """更新数据质量评级"""
        try:
            if quality_score >= 0.95:
                metrics.data_quality = DataQuality.EXCELLENT
            elif quality_score >= 0.85:
                metrics.data_quality = DataQuality.GOOD
            elif quality_score >= 0.70:
                metrics.data_quality = DataQuality.FAIR
            elif quality_score >= 0.50:
                metrics.data_quality = DataQuality.POOR
            else:
                metrics.data_quality = DataQuality.CRITICAL
                
        except Exception as e:
            logger.error(f"更新数据质量评级失败: {e}")
    
    def _update_processing_time_stats(self, processing_time: float) -> None:
        """更新处理时间统计"""
        try:
            processed_count = self.realtime_stats['messages_processed']
            if processed_count > 0:
                current_avg = self.realtime_stats['average_processing_time_ms']
                new_avg = ((current_avg * (processed_count - 1)) + processing_time) / processed_count
                self.realtime_stats['average_processing_time_ms'] = new_avg
                
        except Exception as e:
            logger.error(f"更新处理时间统计失败: {e}")
    
    def get_latest_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """获取最新数据"""
        try:
            buffer = self.data_buffers.get(symbol)
            if buffer and len(buffer) > 0:
                return buffer[-1]
            return None
            
        except Exception as e:
            logger.error(f"获取最新数据失败 {symbol}: {e}")
            return None
    
    def get_historical_buffer(self, symbol: str, count: int = 100) -> List[MarketDataPoint]:
        """获取历史缓冲数据"""
        try:
            buffer = self.data_buffers.get(symbol, deque())
            return list(buffer)[-count:] if buffer else []
            
        except Exception as e:
            logger.error(f"获取历史缓冲数据失败 {symbol}: {e}")
            return []
    
    def get_symbol_metrics(self, symbol: str) -> Optional[DataSourceMetrics]:
        """获取品种指标"""
        return self.metrics.get(symbol)
    
    def get_all_metrics(self) -> Dict[str, DataSourceMetrics]:
        """获取所有指标"""
        return self.metrics.copy()
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """获取实时数据统计"""
        stats = self.realtime_stats.copy()
        
        # 计算成功率
        total_received = stats['messages_received']
        if total_received > 0:
            stats['success_rate'] = stats['messages_processed'] / total_received
            stats['drop_rate'] = stats['messages_dropped'] / total_received
        else:
            stats['success_rate'] = 0.0
            stats['drop_rate'] = 0.0
        
        return stats


class TradingCoreIntegrationManager:
    """trading_core集成管理器"""
    
    def __init__(self):
        self.converter = TradingViewDataConverter()
        self.realtime_adapter = RealtimeDataAdapter()
        self.integration_status = DataSourceStatus.INITIALIZING
        
        # 数据管道
        self.data_pipeline: List[Callable] = []
        self.error_handlers: List[Callable] = []
        
        # 集成统计
        self.integration_stats = {
            'data_throughput': 0,
            'processing_errors': 0,
            'pipeline_latency_ms': 0.0,
            'active_subscriptions': 0
        }
        
    async def initialize_integration(self) -> bool:
        """初始化集成"""
        try:
            self.integration_status = DataSourceStatus.INITIALIZING
            
            # 初始化数据转换器
            logger.info("初始化数据转换器...")
            
            # 初始化实时适配器
            logger.info("初始化实时数据适配器...")
            
            self.integration_status = DataSourceStatus.CONNECTED
            logger.info("✅ trading_core集成初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ trading_core集成初始化失败: {e}")
            self.integration_status = DataSourceStatus.ERROR
            return False
    
    def add_data_pipeline_stage(self, processor: Callable[[MarketDataPoint], MarketDataPoint]) -> None:
        """添加数据管道阶段"""
        self.data_pipeline.append(processor)
        logger.info(f"添加数据管道阶段: {processor.__name__}")
    
    def add_error_handler(self, handler: Callable[[Exception, str], None]) -> None:
        """添加错误处理器"""
        self.error_handlers.append(handler)
        logger.info(f"添加错误处理器: {handler.__name__}")
    
    async def process_data_through_pipeline(self, market_data: MarketDataPoint) -> Optional[MarketDataPoint]:
        """通过数据管道处理数据"""
        try:
            start_time = time.perf_counter()
            processed_data = market_data
            
            # 依次通过所有管道阶段
            for stage in self.data_pipeline:
                try:
                    if asyncio.iscoroutinefunction(stage):
                        processed_data = await stage(processed_data)
                    else:
                        processed_data = stage(processed_data)
                        
                    if processed_data is None:
                        logger.warning("数据在管道阶段被过滤")
                        return None
                        
                except Exception as e:
                    logger.error(f"数据管道阶段失败: {stage.__name__}: {e}")
                    await self._handle_pipeline_error(e, stage.__name__)
                    return None
            
            # 更新管道延迟统计
            pipeline_time = (time.perf_counter() - start_time) * 1000
            self._update_pipeline_stats(pipeline_time)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"数据管道处理失败: {e}")
            await self._handle_pipeline_error(e, "pipeline")
            return None
    
    async def _handle_pipeline_error(self, error: Exception, stage_name: str) -> None:
        """处理管道错误"""
        try:
            self.integration_stats['processing_errors'] += 1
            
            for handler in self.error_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(error, stage_name)
                    else:
                        handler(error, stage_name)
                except Exception as e:
                    logger.error(f"错误处理器失败: {e}")
                    
        except Exception as e:
            logger.error(f"处理管道错误失败: {e}")
    
    def _update_pipeline_stats(self, processing_time: float) -> None:
        """更新管道统计"""
        try:
            self.integration_stats['data_throughput'] += 1
            
            # 更新平均处理延迟
            current_latency = self.integration_stats['pipeline_latency_ms']
            throughput = self.integration_stats['data_throughput']
            
            if throughput > 0:
                new_latency = ((current_latency * (throughput - 1)) + processing_time) / throughput
                self.integration_stats['pipeline_latency_ms'] = new_latency
                
        except Exception as e:
            logger.error(f"更新管道统计失败: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        return {
            'status': self.integration_status.name,
            'converter_stats': self.converter.get_conversion_stats(),
            'realtime_stats': self.realtime_adapter.get_realtime_stats(),
            'integration_stats': self.integration_stats,
            'pipeline_stages': len(self.data_pipeline),
            'error_handlers': len(self.error_handlers)
        }
    
    def get_symbol_summary(self) -> Dict[str, Any]:
        """获取品种摘要"""
        all_metrics = self.realtime_adapter.get_all_metrics()
        
        summary = {
            'total_symbols': len(all_metrics),
            'connected_symbols': sum(1 for m in all_metrics.values() 
                                   if m.connection_status == DataSourceStatus.CONNECTED),
            'quality_distribution': defaultdict(int),
            'average_latency_ms': 0.0,
            'total_throughput': 0
        }
        
        # 统计质量分布和平均延迟
        total_latency = 0
        total_requests = 0
        
        for metrics in all_metrics.values():
            summary['quality_distribution'][metrics.data_quality.name] += 1
            total_latency += metrics.average_latency_ms * metrics.successful_requests
            total_requests += metrics.successful_requests
            summary['total_throughput'] += metrics.successful_requests
        
        if total_requests > 0:
            summary['average_latency_ms'] = total_latency / total_requests
        
        summary['quality_distribution'] = dict(summary['quality_distribution'])
        
        return summary


# 便捷函数
def create_tradingview_integration() -> TradingCoreIntegrationManager:
    """创建TradingView集成管理器"""
    return TradingCoreIntegrationManager()


async def test_data_conversion():
    """测试数据转换功能"""
    converter = TradingViewDataConverter()
    
    # 模拟TradingView数据
    tv_data = {
        'time': time.time(),
        'open': 50000.0,
        'high': 51000.0,
        'low': 49500.0,
        'close': 50500.0,
        'volume': 1000.0
    }
    
    # 转换数据
    market_data = converter.convert_kline_to_market_data(tv_data, "BTC/USDT")
    
    if market_data:
        print(f"✅ 数据转换成功: {market_data.symbol} {market_data.close}")
        
        # 转换为trading_core格式
        tc_format = converter.convert_to_trading_core_format(market_data)
        print(f"trading_core格式: {tc_format}")
        
        # 转换为chanpy格式
        chanpy_format = converter.convert_to_chanpy_format([market_data])
        print(f"chanpy格式: {chanpy_format}")
    else:
        print("❌ 数据转换失败")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_data_conversion())