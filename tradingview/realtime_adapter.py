#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView实时数据适配器
专门处理实时数据流、缓存管理和事件分发
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum, auto
import threading
from concurrent.futures import ThreadPoolExecutor

from config.logging_config import get_logger

logger = get_logger(__name__)


class SubscriptionType(Enum):
    """订阅类型"""
    KLINE_1M = "1m"
    KLINE_5M = "5m"
    KLINE_15M = "15m"
    KLINE_1H = "1h"
    KLINE_1D = "1d"
    QUOTE_REALTIME = "quote"
    ORDER_BOOK = "orderbook"


class EventType(Enum):
    """事件类型"""
    DATA_UPDATE = auto()
    CONNECTION_STATUS = auto()
    SUBSCRIPTION_STATUS = auto()
    DATA_QUALITY_ALERT = auto()
    PERFORMANCE_ALERT = auto()


@dataclass
class SubscriptionInfo:
    """订阅信息"""
    symbol: str
    subscription_type: SubscriptionType
    callback: Callable
    created_time: float = field(default_factory=time.time)
    is_active: bool = True
    error_count: int = 0
    last_update_time: float = 0.0


@dataclass
class RealtimeEvent:
    """实时事件"""
    event_type: EventType
    symbol: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealtimeDataBuffer:
    """实时数据缓冲器"""
    
    def __init__(self, max_size: int = 1000, max_age_seconds: int = 3600):
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self.data_buffer: deque = deque(maxlen=max_size)
        self.index_by_timestamp: Dict[int, int] = {}
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'total_added': 0,
            'total_expired': 0,
            'current_size': 0,
            'oldest_timestamp': 0,
            'newest_timestamp': 0
        }
    
    def add_data(self, data: Any, timestamp: Optional[float] = None) -> bool:
        """添加数据到缓冲区"""
        try:
            with self.lock:
                if timestamp is None:
                    timestamp = time.time()
                
                # 检查数据是否过期
                if time.time() - timestamp > self.max_age_seconds:
                    return False
                
                # 添加数据
                self.data_buffer.append((timestamp, data))
                self.stats['total_added'] += 1
                self.stats['current_size'] = len(self.data_buffer)
                
                # 更新时间戳范围
                if self.stats['oldest_timestamp'] == 0:
                    self.stats['oldest_timestamp'] = timestamp
                self.stats['newest_timestamp'] = timestamp
                
                # 清理过期数据
                self._cleanup_expired_data()
                
                return True
                
        except Exception as e:
            logger.error(f"添加数据到缓冲区失败: {e}")
            return False
    
    def get_latest_data(self, count: int = 1) -> List[Tuple[float, Any]]:
        """获取最新数据"""
        try:
            with self.lock:
                if not self.data_buffer:
                    return []
                
                # 返回最新的count条数据
                return list(self.data_buffer)[-count:]
                
        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            return []
    
    def get_data_in_range(self, start_time: float, end_time: float) -> List[Tuple[float, Any]]:
        """获取时间范围内的数据"""
        try:
            with self.lock:
                result = []
                for timestamp, data in self.data_buffer:
                    if start_time <= timestamp <= end_time:
                        result.append((timestamp, data))
                
                return result
                
        except Exception as e:
            logger.error(f"获取范围数据失败: {e}")
            return []
    
    def _cleanup_expired_data(self) -> None:
        """清理过期数据"""
        try:
            current_time = time.time()
            expired_count = 0
            
            # 从左侧移除过期数据
            while (self.data_buffer and 
                   current_time - self.data_buffer[0][0] > self.max_age_seconds):
                self.data_buffer.popleft()
                expired_count += 1
            
            self.stats['total_expired'] += expired_count
            self.stats['current_size'] = len(self.data_buffer)
            
            # 更新最旧时间戳
            if self.data_buffer:
                self.stats['oldest_timestamp'] = self.data_buffer[0][0]
            else:
                self.stats['oldest_timestamp'] = 0
                
        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """获取缓冲区统计"""
        with self.lock:
            stats = self.stats.copy()
            if stats['current_size'] > 0:
                stats['data_age_seconds'] = time.time() - stats['oldest_timestamp']
            else:
                stats['data_age_seconds'] = 0
            
            return stats


class EventDispatcher:
    """事件分发器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.is_running = False
        self.dispatch_task: Optional[asyncio.Task] = None
        
        # 事件统计
        self.event_stats = {
            'events_received': 0,
            'events_dispatched': 0,
            'events_failed': 0,
            'queue_size': 0,
            'average_dispatch_time_ms': 0.0
        }
    
    async def start(self) -> None:
        """启动事件分发器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("事件分发器已启动")
    
    async def stop(self) -> None:
        """停止事件分发器"""
        self.is_running = False
        
        if self.dispatch_task:
            self.dispatch_task.cancel()
            try:
                await self.dispatch_task
            except asyncio.CancelledError:
                pass
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        logger.info("事件分发器已停止")
    
    def register_handler(self, event_type: EventType, handler: Callable[[RealtimeEvent], None]) -> None:
        """注册事件处理器"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"注册事件处理器: {event_type.name}")
    
    def unregister_handler(self, event_type: EventType, handler: Callable) -> bool:
        """取消注册事件处理器"""
        try:
            self.event_handlers[event_type].remove(handler)
            logger.info(f"取消注册事件处理器: {event_type.name}")
            return True
        except ValueError:
            logger.warning(f"未找到要取消的事件处理器: {event_type.name}")
            return False
    
    async def dispatch_event(self, event: RealtimeEvent) -> bool:
        """分发事件"""
        try:
            if not self.is_running:
                return False
            
            # 添加到事件队列
            await self.event_queue.put(event)
            self.event_stats['events_received'] += 1
            self.event_stats['queue_size'] = self.event_queue.qsize()
            
            return True
            
        except asyncio.QueueFull:
            logger.warning("事件队列已满，丢弃事件")
            self.event_stats['events_failed'] += 1
            return False
        except Exception as e:
            logger.error(f"分发事件失败: {e}")
            self.event_stats['events_failed'] += 1
            return False
    
    async def _dispatch_loop(self) -> None:
        """事件分发主循环"""
        while self.is_running:
            try:
                # 获取事件
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                
                start_time = time.perf_counter()
                
                # 获取对应的处理器
                handlers = self.event_handlers.get(event.event_type, [])
                
                if handlers:
                    # 并发执行所有处理器
                    tasks = []
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                tasks.append(asyncio.create_task(handler(event)))
                            else:
                                # 同步处理器在线程池中执行
                                tasks.append(asyncio.create_task(
                                    asyncio.get_event_loop().run_in_executor(
                                        self.executor, handler, event
                                    )
                                ))
                        except Exception as e:
                            logger.error(f"创建事件处理任务失败: {e}")
                    
                    # 等待所有处理器完成
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # 检查处理结果
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"事件处理器 {i} 执行失败: {result}")
                
                # 更新统计
                dispatch_time = (time.perf_counter() - start_time) * 1000
                self.event_stats['events_dispatched'] += 1
                self._update_dispatch_time_stats(dispatch_time)
                self.event_stats['queue_size'] = self.event_queue.qsize()
                
            except asyncio.TimeoutError:
                # 超时继续循环
                continue
            except Exception as e:
                logger.error(f"事件分发循环异常: {e}")
                self.event_stats['events_failed'] += 1
                await asyncio.sleep(0.01)
    
    def _update_dispatch_time_stats(self, dispatch_time: float) -> None:
        """更新分发时间统计"""
        try:
            dispatched_count = self.event_stats['events_dispatched']
            if dispatched_count > 0:
                current_avg = self.event_stats['average_dispatch_time_ms']
                new_avg = ((current_avg * (dispatched_count - 1)) + dispatch_time) / dispatched_count
                self.event_stats['average_dispatch_time_ms'] = new_avg
        except Exception as e:
            logger.error(f"更新分发时间统计失败: {e}")
    
    def get_event_stats(self) -> Dict[str, Any]:
        """获取事件统计"""
        stats = self.event_stats.copy()
        stats['handler_counts'] = {
            event_type.name: len(handlers) 
            for event_type, handlers in self.event_handlers.items()
        }
        return stats


class AdvancedRealtimeAdapter:
    """高级实时数据适配器"""
    
    def __init__(self, buffer_size: int = 1000, max_workers: int = 4):
        # 核心组件
        self.subscriptions: Dict[str, SubscriptionInfo] = {}
        self.data_buffers: Dict[str, RealtimeDataBuffer] = {}
        self.event_dispatcher = EventDispatcher(max_workers=max_workers)
        
        # 配置
        self.buffer_size = buffer_size
        self.is_running = False
        
        # 性能监控
        self.performance_monitor = PerformanceMonitor()
        
        # 数据质量监控
        self.quality_monitor = DataQualityMonitor()
        
        # 连接状态
        self.connection_status = defaultdict(lambda: False)
        
    async def initialize(self) -> bool:
        """初始化适配器"""
        try:
            # 启动事件分发器
            await self.event_dispatcher.start()
            
            # 启动性能监控
            await self.performance_monitor.start()
            
            # 启动质量监控
            await self.quality_monitor.start()
            
            self.is_running = True
            logger.info("✅ 高级实时数据适配器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 高级实时数据适配器初始化失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭适配器"""
        try:
            self.is_running = False
            
            # 停止监控组件
            await self.performance_monitor.stop()
            await self.quality_monitor.stop()
            
            # 停止事件分发器
            await self.event_dispatcher.stop()
            
            # 清理订阅
            self.subscriptions.clear()
            self.data_buffers.clear()
            
            logger.info("高级实时数据适配器已关闭")
            
        except Exception as e:
            logger.error(f"关闭高级实时数据适配器失败: {e}")
    
    async def subscribe_symbol_data(self, symbol: str, subscription_type: SubscriptionType,
                                  callback: Callable[[str, Any], None]) -> bool:
        """订阅品种数据"""
        try:
            subscription_key = f"{symbol}_{subscription_type.value}"
            
            # 检查是否已订阅
            if subscription_key in self.subscriptions:
                logger.warning(f"品种 {symbol} 已订阅 {subscription_type.value}")
                return True
            
            # 创建订阅信息
            subscription = SubscriptionInfo(
                symbol=symbol,
                subscription_type=subscription_type,
                callback=callback
            )
            
            self.subscriptions[subscription_key] = subscription
            
            # 创建数据缓冲区
            if symbol not in self.data_buffers:
                self.data_buffers[symbol] = RealtimeDataBuffer(max_size=self.buffer_size)
            
            # 发送订阅状态事件
            await self.event_dispatcher.dispatch_event(RealtimeEvent(
                event_type=EventType.SUBSCRIPTION_STATUS,
                symbol=symbol,
                data={'status': 'subscribed', 'type': subscription_type.value}
            ))
            
            logger.info(f"✅ 订阅成功: {symbol} {subscription_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"订阅失败 {symbol}: {e}")
            return False
    
    async def unsubscribe_symbol_data(self, symbol: str, subscription_type: SubscriptionType) -> bool:
        """取消订阅品种数据"""
        try:
            subscription_key = f"{symbol}_{subscription_type.value}"
            
            if subscription_key not in self.subscriptions:
                logger.warning(f"未找到订阅: {symbol} {subscription_type.value}")
                return False
            
            # 移除订阅
            del self.subscriptions[subscription_key]
            
            # 发送取消订阅事件
            await self.event_dispatcher.dispatch_event(RealtimeEvent(
                event_type=EventType.SUBSCRIPTION_STATUS,
                symbol=symbol,
                data={'status': 'unsubscribed', 'type': subscription_type.value}
            ))
            
            logger.info(f"取消订阅成功: {symbol} {subscription_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"取消订阅失败 {symbol}: {e}")
            return False
    
    async def process_realtime_data(self, symbol: str, raw_data: Dict[str, Any],
                                  subscription_type: SubscriptionType) -> bool:
        """处理实时数据"""
        try:
            start_time = time.perf_counter()
            
            # 记录性能指标
            self.performance_monitor.record_data_processing_start(symbol)
            
            # 数据质量检查
            quality_score = self.quality_monitor.evaluate_data_quality(raw_data)
            
            if quality_score < 0.5:  # 质量过低
                logger.warning(f"数据质量过低: {symbol}, 分数: {quality_score}")
                await self.event_dispatcher.dispatch_event(RealtimeEvent(
                    event_type=EventType.DATA_QUALITY_ALERT,
                    symbol=symbol,
                    data={'quality_score': quality_score, 'raw_data': raw_data}
                ))
                return False
            
            # 添加到缓冲区
            buffer = self.data_buffers.get(symbol)
            if buffer:
                buffer.add_data(raw_data)
            
            # 查找相关订阅
            subscription_key = f"{symbol}_{subscription_type.value}"
            subscription = self.subscriptions.get(subscription_key)
            
            if subscription and subscription.is_active:
                try:
                    # 调用订阅回调
                    if asyncio.iscoroutinefunction(subscription.callback):
                        await subscription.callback(symbol, raw_data)
                    else:
                        subscription.callback(symbol, raw_data)
                    
                    subscription.last_update_time = time.time()
                    
                    # 发送数据更新事件
                    await self.event_dispatcher.dispatch_event(RealtimeEvent(
                        event_type=EventType.DATA_UPDATE,
                        symbol=symbol,
                        data=raw_data,
                        metadata={
                            'subscription_type': subscription_type.value,
                            'quality_score': quality_score,
                            'processing_time_ms': (time.perf_counter() - start_time) * 1000
                        }
                    ))
                    
                except Exception as e:
                    logger.error(f"调用订阅回调失败 {symbol}: {e}")
                    subscription.error_count += 1
                    
                    # 如果错误次数过多，暂停订阅
                    if subscription.error_count > 10:
                        subscription.is_active = False
                        logger.warning(f"订阅 {symbol} 因错误过多被暂停")
            
            # 记录性能指标
            processing_time = (time.perf_counter() - start_time) * 1000
            self.performance_monitor.record_data_processing_end(symbol, processing_time)
            
            return True
            
        except Exception as e:
            logger.error(f"处理实时数据失败 {symbol}: {e}")
            return False
    
    def get_symbol_buffer_data(self, symbol: str, count: int = 100) -> List[Tuple[float, Any]]:
        """获取品种缓冲数据"""
        try:
            buffer = self.data_buffers.get(symbol)
            if buffer:
                return buffer.get_latest_data(count)
            return []
            
        except Exception as e:
            logger.error(f"获取缓冲数据失败 {symbol}: {e}")
            return []
    
    def get_subscription_status(self) -> Dict[str, Any]:
        """获取订阅状态"""
        try:
            active_subscriptions = sum(1 for sub in self.subscriptions.values() if sub.is_active)
            total_subscriptions = len(self.subscriptions)
            
            symbol_counts = defaultdict(int)
            type_counts = defaultdict(int)
            
            for subscription in self.subscriptions.values():
                symbol_counts[subscription.symbol] += 1
                type_counts[subscription.subscription_type.value] += 1
            
            return {
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
                'inactive_subscriptions': total_subscriptions - active_subscriptions,
                'symbols_count': len(symbol_counts),
                'subscription_by_symbol': dict(symbol_counts),
                'subscription_by_type': dict(type_counts),
                'buffer_stats': {
                    symbol: buffer.get_buffer_stats() 
                    for symbol, buffer in self.data_buffers.items()
                }
            }
            
        except Exception as e:
            logger.error(f"获取订阅状态失败: {e}")
            return {}
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计"""
        return {
            'subscription_status': self.get_subscription_status(),
            'event_stats': self.event_dispatcher.get_event_stats(),
            'performance_stats': self.performance_monitor.get_performance_stats(),
            'quality_stats': self.quality_monitor.get_quality_stats(),
            'is_running': self.is_running
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throughput_counters: Dict[str, int] = defaultdict(int)
        self.start_times: Dict[str, float] = {}
        self.is_running = False
        
    async def start(self) -> None:
        """启动性能监控"""
        self.is_running = True
        logger.info("性能监控器已启动")
    
    async def stop(self) -> None:
        """停止性能监控"""
        self.is_running = False
        logger.info("性能监控器已停止")
    
    def record_data_processing_start(self, symbol: str) -> None:
        """记录数据处理开始"""
        self.start_times[symbol] = time.perf_counter()
    
    def record_data_processing_end(self, symbol: str, processing_time_ms: float) -> None:
        """记录数据处理结束"""
        if symbol in self.start_times:
            del self.start_times[symbol]
        
        self.processing_times[symbol].append(processing_time_ms)
        self.throughput_counters[symbol] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        try:
            stats = {
                'symbols': {},
                'overall_avg_processing_time_ms': 0.0,
                'total_throughput': 0
            }
            
            total_processing_time = 0
            total_samples = 0
            
            for symbol, times in self.processing_times.items():
                if times:
                    avg_time = sum(times) / len(times)
                    max_time = max(times)
                    min_time = min(times)
                    
                    stats['symbols'][symbol] = {
                        'avg_processing_time_ms': avg_time,
                        'max_processing_time_ms': max_time,
                        'min_processing_time_ms': min_time,
                        'total_processed': self.throughput_counters[symbol],
                        'samples_count': len(times)
                    }
                    
                    total_processing_time += avg_time * len(times)
                    total_samples += len(times)
            
            if total_samples > 0:
                stats['overall_avg_processing_time_ms'] = total_processing_time / total_samples
            
            stats['total_throughput'] = sum(self.throughput_counters.values())
            
            return stats
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {}


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self):
        self.quality_scores: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.quality_alerts_count: Dict[str, int] = defaultdict(int)
        self.is_running = False
    
    async def start(self) -> None:
        """启动质量监控"""
        self.is_running = True
        logger.info("数据质量监控器已启动")
    
    async def stop(self) -> None:
        """停止质量监控"""
        self.is_running = False
        logger.info("数据质量监控器已停止")
    
    def evaluate_data_quality(self, data: Dict[str, Any]) -> float:
        """评估数据质量"""
        try:
            score = 1.0
            
            # 检查必需字段
            required_fields = ['time', 'open', 'high', 'low', 'close']
            missing_fields = sum(1 for field in required_fields if field not in data)
            score *= (1 - missing_fields * 0.2)
            
            # 检查数据有效性
            if 'open' in data and 'high' in data and 'low' in data and 'close' in data:
                try:
                    open_price = float(data['open'])
                    high_price = float(data['high'])
                    low_price = float(data['low'])
                    close_price = float(data['close'])
                    
                    # 检查价格逻辑
                    if high_price < max(open_price, close_price) or low_price > min(open_price, close_price):
                        score *= 0.5
                    
                    # 检查价格为正数
                    if any(price <= 0 for price in [open_price, high_price, low_price, close_price]):
                        score *= 0.3
                        
                except (ValueError, TypeError):
                    score *= 0.4
            
            # 检查时间戳
            if 'time' in data:
                try:
                    timestamp = float(data['time'])
                    current_time = time.time()
                    time_diff = abs(current_time - timestamp)
                    
                    if time_diff > 3600:  # 超过1小时
                        score *= 0.7
                    elif time_diff > 300:  # 超过5分钟
                        score *= 0.9
                        
                except (ValueError, TypeError):
                    score *= 0.6
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"评估数据质量失败: {e}")
            return 0.5
    
    def record_quality_score(self, symbol: str, score: float) -> None:
        """记录质量分数"""
        self.quality_scores[symbol].append(score)
        
        if score < 0.5:
            self.quality_alerts_count[symbol] += 1
    
    def get_quality_stats(self) -> Dict[str, Any]:
        """获取质量统计"""
        try:
            stats = {
                'symbols': {},
                'overall_avg_quality': 0.0,
                'total_alerts': sum(self.quality_alerts_count.values())
            }
            
            total_quality = 0
            total_samples = 0
            
            for symbol, scores in self.quality_scores.items():
                if scores:
                    avg_quality = sum(scores) / len(scores)
                    min_quality = min(scores)
                    
                    stats['symbols'][symbol] = {
                        'avg_quality': avg_quality,
                        'min_quality': min_quality,
                        'samples_count': len(scores),
                        'alerts_count': self.quality_alerts_count[symbol]
                    }
                    
                    total_quality += avg_quality * len(scores)
                    total_samples += len(scores)
            
            if total_samples > 0:
                stats['overall_avg_quality'] = total_quality / total_samples
            
            return stats
            
        except Exception as e:
            logger.error(f"获取质量统计失败: {e}")
            return {}


# 便捷函数
def create_realtime_adapter(buffer_size: int = 1000, max_workers: int = 4) -> AdvancedRealtimeAdapter:
    """创建高级实时数据适配器"""
    return AdvancedRealtimeAdapter(buffer_size=buffer_size, max_workers=max_workers)


async def test_realtime_adapter():
    """测试实时数据适配器"""
    adapter = create_realtime_adapter()
    
    try:
        # 初始化适配器
        await adapter.initialize()
        
        # 定义数据回调
        async def on_kline_data(symbol: str, data: Dict[str, Any]):
            print(f"收到K线数据: {symbol} {data['close']}")
        
        # 订阅BTC 15分钟K线
        await adapter.subscribe_symbol_data(
            "BTC/USDT", 
            SubscriptionType.KLINE_15M, 
            on_kline_data
        )
        
        # 模拟接收数据
        test_data = {
            'time': time.time(),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49500.0,
            'close': 50500.0,
            'volume': 1000.0
        }
        
        # 处理测试数据
        await adapter.process_realtime_data("BTC/USDT", test_data, SubscriptionType.KLINE_15M)
        
        # 等待处理完成
        await asyncio.sleep(1)
        
        # 获取统计信息
        stats = adapter.get_comprehensive_stats()
        print(f"适配器统计: {json.dumps(stats, indent=2, default=str)}")
        
    finally:
        await adapter.shutdown()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_realtime_adapter())