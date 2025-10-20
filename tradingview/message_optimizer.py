#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView消息处理优化器
实现高效的消息队列、去重、优先级处理和批量操作
"""

import asyncio
import time
import hashlib
import json
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum, auto

from config.logging_config import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    KLINE_UPDATE = auto()
    QUOTE_UPDATE = auto()
    SYMBOL_RESOLVED = auto()
    CHART_DATA = auto()
    STUDY_DATA = auto()
    ERROR = auto()
    PING = auto()
    PONG = auto()
    OTHER = auto()


@dataclass
class ProcessedMessage:
    """处理后的消息"""
    message_id: str
    message_type: MessageType
    symbol: Optional[str]
    data: Dict[str, Any]
    timestamp: float
    priority: int
    processed: bool = False
    retry_count: int = 0


class MessageDeduplicator:
    """消息去重器"""
    
    def __init__(self, window_size: int = 1000, ttl: float = 300.0):
        self.window_size = window_size
        self.ttl = ttl
        self.seen_messages: deque = deque(maxlen=window_size)
        self.message_timestamps: Dict[str, float] = {}
        
    def is_duplicate(self, message: Dict[str, Any]) -> bool:
        """检查消息是否重复"""
        try:
            # 生成消息指纹
            fingerprint = self._generate_fingerprint(message)
            current_time = time.time()
            
            # 清理过期消息
            self._cleanup_expired_messages(current_time)
            
            # 检查是否重复
            if fingerprint in self.message_timestamps:
                logger.debug(f"发现重复消息: {fingerprint}")
                return True
                
            # 记录新消息
            self.seen_messages.append(fingerprint)
            self.message_timestamps[fingerprint] = current_time
            
            return False
            
        except Exception as e:
            logger.error(f"去重检查失败: {e}")
            return False
            
    def _generate_fingerprint(self, message: Dict[str, Any]) -> str:
        """生成消息指纹"""
        try:
            # 提取关键字段生成指纹
            key_fields = {
                'type': message.get('type'),
                'symbol': message.get('symbol'),
                'timestamp': message.get('timestamp')
            }
            
            # 对于数据消息，包含数据摘要
            if 'data' in message:
                data_str = json.dumps(message['data'], sort_keys=True)
                key_fields['data_hash'] = hashlib.md5(data_str.encode()).hexdigest()[:8]
                
            fingerprint_str = json.dumps(key_fields, sort_keys=True)
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.error(f"生成消息指纹失败: {e}")
            return str(hash(str(message)))
            
    def _cleanup_expired_messages(self, current_time: float) -> None:
        """清理过期消息"""
        try:
            expired_keys = [
                key for key, timestamp in self.message_timestamps.items()
                if current_time - timestamp > self.ttl
            ]
            
            for key in expired_keys:
                del self.message_timestamps[key]
                
        except Exception as e:
            logger.error(f"清理过期消息失败: {e}")


class MessageClassifier:
    """消息分类器"""
    
    def __init__(self):
        self.classification_rules = {
            'timescale_update': MessageType.KLINE_UPDATE,
            'quote_update': MessageType.QUOTE_UPDATE,
            'symbol_resolved': MessageType.SYMBOL_RESOLVED,
            'series_completed': MessageType.CHART_DATA,
            'study_completed': MessageType.STUDY_DATA,
            'protocol_error': MessageType.ERROR,
            'ping': MessageType.PING,
            'pong': MessageType.PONG
        }
        
        self.priority_rules = {
            MessageType.ERROR: 100,
            MessageType.PING: 90,
            MessageType.PONG: 90,
            MessageType.KLINE_UPDATE: 80,
            MessageType.QUOTE_UPDATE: 70,
            MessageType.CHART_DATA: 60,
            MessageType.SYMBOL_RESOLVED: 50,
            MessageType.STUDY_DATA: 40,
            MessageType.OTHER: 10
        }
        
    def classify_message(self, raw_message: Dict[str, Any]) -> ProcessedMessage:
        """分类消息"""
        try:
            # 确定消息类型
            message_type = self._determine_type(raw_message)
            
            # 提取符号
            symbol = self._extract_symbol(raw_message)
            
            # 生成消息ID
            message_id = self._generate_message_id(raw_message)
            
            # 确定优先级
            priority = self.priority_rules.get(message_type, 10)
            
            return ProcessedMessage(
                message_id=message_id,
                message_type=message_type,
                symbol=symbol,
                data=raw_message,
                timestamp=time.time(),
                priority=priority
            )
            
        except Exception as e:
            logger.error(f"消息分类失败: {e}")
            return ProcessedMessage(
                message_id=f"error_{time.time()}",
                message_type=MessageType.OTHER,
                symbol=None,
                data=raw_message,
                timestamp=time.time(),
                priority=1
            )
            
    def _determine_type(self, message: Dict[str, Any]) -> MessageType:
        """确定消息类型"""
        message_method = message.get('type', '').lower()
        
        for pattern, msg_type in self.classification_rules.items():
            if pattern in message_method:
                return msg_type
                
        return MessageType.OTHER
        
    def _extract_symbol(self, message: Dict[str, Any]) -> Optional[str]:
        """提取交易符号"""
        try:
            # 尝试从不同位置提取符号
            if 'symbol' in message:
                return message['symbol']
                
            if 'data' in message and isinstance(message['data'], list):
                for item in message['data']:
                    if isinstance(item, str) and ':' in item:
                        return item
                        
            return None
            
        except Exception:
            return None
            
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """生成消息ID"""
        try:
            timestamp = str(time.time())
            content_hash = hashlib.md5(str(message).encode()).hexdigest()[:8]
            return f"msg_{timestamp}_{content_hash}"
        except Exception:
            return f"msg_{time.time()}"


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, 
                 max_batch_size: int = 50,
                 max_wait_time: float = 0.1,
                 max_concurrent_batches: int = 5):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrent_batches = max_concurrent_batches
        
        self.pending_batches: Dict[MessageType, List[ProcessedMessage]] = defaultdict(list)
        self.batch_timers: Dict[MessageType, float] = {}
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        self.processed_count = 0
        self.batch_count = 0
        
    async def add_message(self, message: ProcessedMessage) -> None:
        """添加消息到批处理队列"""
        try:
            message_type = message.message_type
            
            # 添加到对应类型的批次
            self.pending_batches[message_type].append(message)
            
            # 设置首次计时器
            if message_type not in self.batch_timers:
                self.batch_timers[message_type] = time.time()
                
            # 检查是否需要立即处理批次
            batch = self.pending_batches[message_type]
            elapsed = time.time() - self.batch_timers[message_type]
            
            if len(batch) >= self.max_batch_size or elapsed >= self.max_wait_time:
                await self._process_batch(message_type)
                
        except Exception as e:
            logger.error(f"添加批处理消息失败: {e}")
            
    async def _process_batch(self, message_type: MessageType) -> None:
        """处理指定类型的批次"""
        try:
            batch = self.pending_batches[message_type]
            if not batch:
                return
                
            # 清空当前批次
            self.pending_batches[message_type] = []
            if message_type in self.batch_timers:
                del self.batch_timers[message_type]
                
            # 异步处理批次
            asyncio.create_task(self._handle_batch(message_type, batch))
            
        except Exception as e:
            logger.error(f"处理批次失败: {e}")
            
    async def _handle_batch(self, message_type: MessageType, batch: List[ProcessedMessage]) -> None:
        """处理消息批次"""
        async with self.processing_semaphore:
            try:
                start_time = time.time()
                
                # 按符号分组处理
                symbol_groups = defaultdict(list)
                for message in batch:
                    symbol = message.symbol or 'unknown'
                    symbol_groups[symbol].append(message)
                    
                # 并发处理各符号组
                tasks = []
                for symbol, messages in symbol_groups.items():
                    task = asyncio.create_task(
                        self._process_symbol_group(message_type, symbol, messages)
                    )
                    tasks.append(task)
                    
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # 更新统计
                self.processed_count += len(batch)
                self.batch_count += 1
                
                processing_time = (time.time() - start_time) * 1000
                logger.debug(f"批次处理完成: {message_type.name}, "
                           f"消息数: {len(batch)}, 耗时: {processing_time:.1f}ms")
                
            except Exception as e:
                logger.error(f"批次处理异常: {e}")
                
    async def _process_symbol_group(self, 
                                  message_type: MessageType, 
                                  symbol: str, 
                                  messages: List[ProcessedMessage]) -> None:
        """处理单个符号的消息组"""
        try:
            # 这里可以实现特定的业务逻辑
            # 比如合并K线数据、去重报价更新等
            
            if message_type == MessageType.KLINE_UPDATE:
                await self._merge_kline_updates(symbol, messages)
            elif message_type == MessageType.QUOTE_UPDATE:
                await self._merge_quote_updates(symbol, messages)
            else:
                # 默认处理
                for message in messages:
                    message.processed = True
                    
        except Exception as e:
            logger.error(f"处理符号组失败 {symbol}: {e}")
            
    async def _merge_kline_updates(self, symbol: str, messages: List[ProcessedMessage]) -> None:
        """合并K线更新"""
        try:
            # 按时间戳排序
            messages.sort(key=lambda m: m.timestamp)
            
            # 合并逻辑：保留最新的完整数据
            latest_message = messages[-1]
            latest_message.processed = True
            
            # 标记其他消息为已处理
            for message in messages[:-1]:
                message.processed = True
                
            logger.debug(f"合并 {symbol} K线更新: {len(messages)} -> 1")
            
        except Exception as e:
            logger.error(f"合并K线更新失败: {e}")
            
    async def _merge_quote_updates(self, symbol: str, messages: List[ProcessedMessage]) -> None:
        """合并报价更新"""
        try:
            # 保留最新报价
            latest_message = messages[-1]
            latest_message.processed = True
            
            # 标记其他消息为已处理
            for message in messages[:-1]:
                message.processed = True
                
            logger.debug(f"合并 {symbol} 报价更新: {len(messages)} -> 1")
            
        except Exception as e:
            logger.error(f"合并报价更新失败: {e}")
            
    async def flush_all_batches(self) -> None:
        """刷新所有待处理批次"""
        try:
            for message_type in list(self.pending_batches.keys()):
                if self.pending_batches[message_type]:
                    await self._process_batch(message_type)
                    
        except Exception as e:
            logger.error(f"刷新批次失败: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """获取批处理统计"""
        return {
            'processed_count': self.processed_count,
            'batch_count': self.batch_count,
            'pending_batches': {
                msg_type.name: len(batch) 
                for msg_type, batch in self.pending_batches.items()
            },
            'avg_batch_size': self.processed_count / max(1, self.batch_count)
        }


class AdvancedMessageOptimizer:
    """高级消息优化器"""
    
    def __init__(self, 
                 enable_deduplication: bool = True,
                 enable_batching: bool = True,
                 max_queue_size: int = 10000):
        
        # 核心组件
        self.deduplicator = MessageDeduplicator() if enable_deduplication else None
        self.classifier = MessageClassifier()
        self.batch_processor = BatchProcessor() if enable_batching else None
        
        # 消息队列
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # 处理器注册
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # 运行状态
        self.is_running = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            'total_messages': 0,
            'processed_messages': 0,
            'duplicate_messages': 0,
            'error_messages': 0,
            'processing_time_ms': deque(maxlen=1000)
        }
        
    async def start(self) -> None:
        """启动消息优化器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.processor_task = asyncio.create_task(self._process_messages())
        logger.info("高级消息优化器已启动")
        
    async def stop(self) -> None:
        """停止消息优化器"""
        self.is_running = False
        
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
                
        # 刷新剩余批次
        if self.batch_processor:
            await self.batch_processor.flush_all_batches()
            
        logger.info("高级消息优化器已停止")
        
    async def add_message(self, raw_message: Dict[str, Any]) -> bool:
        """添加原始消息进行处理"""
        try:
            if not self.is_running:
                return False
                
            # 检查队列是否已满
            if self.message_queue.full():
                logger.warning("消息队列已满，丢弃消息")
                return False
                
            await self.message_queue.put(raw_message)
            self.stats['total_messages'] += 1
            return True
            
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False
            
    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"注册消息处理器: {message_type.name}")
        
    async def _process_messages(self) -> None:
        """消息处理主循环"""
        while self.is_running:
            try:
                # 获取原始消息
                raw_message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.1
                )
                
                start_time = time.perf_counter()
                
                # 去重检查
                if self.deduplicator and self.deduplicator.is_duplicate(raw_message):
                    self.stats['duplicate_messages'] += 1
                    continue
                    
                # 消息分类
                processed_message = self.classifier.classify_message(raw_message)
                
                # 批量处理
                if self.batch_processor:
                    await self.batch_processor.add_message(processed_message)
                else:
                    # 直接处理
                    await self._handle_single_message(processed_message)
                    
                # 记录处理时间
                processing_time = (time.perf_counter() - start_time) * 1000
                self.stats['processing_time_ms'].append(processing_time)
                self.stats['processed_messages'] += 1
                
            except asyncio.TimeoutError:
                # 处理批次超时
                if self.batch_processor:
                    await self.batch_processor.flush_all_batches()
                continue
            except Exception as e:
                logger.error(f"消息处理异常: {e}")
                self.stats['error_messages'] += 1
                await asyncio.sleep(0.01)
                
    async def _handle_single_message(self, message: ProcessedMessage) -> None:
        """处理单个消息"""
        try:
            handler = self.message_handlers.get(message.message_type)
            if handler:
                await handler(message)
                message.processed = True
            else:
                logger.debug(f"未找到 {message.message_type.name} 消息处理器")
                
        except Exception as e:
            logger.error(f"单个消息处理失败: {e}")
            message.retry_count += 1
            
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        stats = {
            'optimizer_stats': self.stats.copy(),
            'batch_processor_stats': None,
            'avg_processing_time_ms': 0.0,
            'message_throughput': 0.0
        }
        
        # 计算平均处理时间
        if self.stats['processing_time_ms']:
            stats['avg_processing_time_ms'] = sum(self.stats['processing_time_ms']) / len(self.stats['processing_time_ms'])
            
        # 计算消息吞吐量
        if self.stats['processed_messages'] > 0:
            stats['message_throughput'] = self.stats['processed_messages'] / max(1, time.time())
            
        # 批处理统计
        if self.batch_processor:
            stats['batch_processor_stats'] = self.batch_processor.get_stats()
            
        return stats