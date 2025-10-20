#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版TradingView客户端
实现智能重连、连接监控和消息处理优化
"""

import asyncio
import time
import random
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum

from .client import Client, TradingViewClient
from config.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ConnectionMonitor:
    """连接状态监控器"""
    
    def __init__(self, client_ref=None):
        self.state = ConnectionState.DISCONNECTED
        self.last_ping_time = 0
        self.last_pong_time = 0
        self.latency_history = deque(maxlen=100)
        self.error_count = 0
        self.total_reconnects = 0
        self.uptime_start = time.time()
        self.connection_quality = 1.0
        self.client_ref = client_ref  # 客户端引用，用于访问连接状态
        
        # 健康检查阈值
        self.max_latency = 5000  # 5秒
        self.max_errors = 5
        self.ping_interval = 30  # 30秒
        
    def record_ping(self) -> None:
        """记录ping发送时间"""
        self.last_ping_time = time.time()
        
    def record_pong(self) -> None:
        """记录pong接收时间"""
        self.last_pong_time = time.time()
        if self.last_ping_time > 0:
            latency = (self.last_pong_time - self.last_ping_time) * 1000
            self.latency_history.append(latency)
            
    def record_error(self) -> None:
        """记录错误"""
        self.error_count += 1
        
    def record_reconnect(self) -> None:
        """记录重连"""
        self.total_reconnects += 1
        self.error_count = 0  # 重置错误计数
        
    def get_average_latency(self) -> float:
        """获取平均延迟"""
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)
        
    def get_uptime(self) -> float:
        """获取运行时间(秒)"""
        return time.time() - self.uptime_start
        
    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        if self.state != ConnectionState.CONNECTED:
            return False
            
        # 检查基础连接状态 - 通过客户端引用访问连接状态
        if self.client_ref and hasattr(self.client_ref, 'is_open'):
            try:
                if not self.client_ref.is_open:
                    return False
            except AttributeError:
                # 如果属性访问失败，跳过此检查
                pass
            
        # 检查延迟（如果有延迟历史记录）
        avg_latency = self.get_average_latency()
        if avg_latency > 0 and avg_latency > self.max_latency:
            return False
            
        # 检查错误率
        if self.error_count > self.max_errors:
            return False
            
        # 检查连接运行时间 - 确保连接存在一定时间才进行心跳检查
        uptime = self.get_uptime()
        if uptime > 60:  # 连接超过60秒才检查心跳
            # 检查心跳 - 修复：如果last_pong_time为0（刚连接），给予宽限期
            if self.last_pong_time > 0 and time.time() - self.last_pong_time > self.ping_interval * 3:
                return False
            
        return True
        
    def calculate_quality_score(self) -> float:
        """计算连接质量分数 0.0-1.0"""
        if self.state != ConnectionState.CONNECTED:
            return 0.0
            
        quality_factors = []
        
        # 延迟因子 (0.4权重)
        avg_latency = self.get_average_latency()
        if avg_latency > 0:
            latency_score = max(0, 1 - (avg_latency / self.max_latency))
            quality_factors.append(latency_score * 0.4)
        else:
            quality_factors.append(0.4)
            
        # 错误率因子 (0.3权重)
        error_score = max(0, 1 - (self.error_count / self.max_errors))
        quality_factors.append(error_score * 0.3)
        
        # 稳定性因子 (0.3权重)
        uptime = self.get_uptime()
        stability_score = min(1.0, uptime / 3600)  # 1小时达到满分
        quality_factors.append(stability_score * 0.3)
        
        self.connection_quality = sum(quality_factors)
        return self.connection_quality


class MessageProcessor:
    """消息处理器 - 支持优先级和批量处理"""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.message_queues = {
            MessagePriority.CRITICAL: asyncio.Queue(),
            MessagePriority.HIGH: asyncio.Queue(),
            MessagePriority.NORMAL: asyncio.Queue(),
            MessagePriority.LOW: asyncio.Queue()
        }
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.processing_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.message_handlers = {}
        
    async def start(self) -> None:
        """启动消息处理器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_messages())
        logger.info("消息处理器已启动")
        
    async def stop(self) -> None:
        """停止消息处理器"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("消息处理器已停止")
        
    async def add_message(self, message: Dict, priority: MessagePriority = MessagePriority.NORMAL) -> None:
        """添加消息到队列"""
        try:
            await self.message_queues[priority].put(message)
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        
    async def _process_messages(self) -> None:
        """消息处理主循环"""
        while self.is_running:
            try:
                # 按优先级处理消息
                message_batch = []
                
                # 优先处理高优先级消息
                for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                               MessagePriority.NORMAL, MessagePriority.LOW]:
                    queue = self.message_queues[priority]
                    
                    # 收集批量消息
                    batch_start = time.time()
                    while (len(message_batch) < self.batch_size and 
                           time.time() - batch_start < self.batch_timeout):
                        try:
                            message = await asyncio.wait_for(queue.get(), timeout=0.01)
                            message_batch.append((message, priority))
                        except asyncio.TimeoutError:
                            break
                            
                    if message_batch:
                        break
                
                # 处理批量消息
                if message_batch:
                    await self._process_batch(message_batch)
                else:
                    await asyncio.sleep(0.01)  # 避免空转
                    
            except Exception as e:
                logger.error(f"消息处理错误: {e}")
                self.error_count += 1
                await asyncio.sleep(0.1)
                
    async def _process_batch(self, message_batch: List) -> None:
        """处理批量消息"""
        try:
            # 按消息类型分组
            grouped_messages = defaultdict(list)
            for message, priority in message_batch:
                msg_type = message.get('type', 'unknown')
                grouped_messages[msg_type].append((message, priority))
            
            # 批量处理相同类型的消息
            for msg_type, messages in grouped_messages.items():
                if msg_type in self.message_handlers:
                    try:
                        handler = self.message_handlers[msg_type]
                        await handler([msg[0] for msg in messages])
                        self.processed_count += len(messages)
                    except Exception as e:
                        logger.error(f"处理 {msg_type} 消息失败: {e}")
                        self.error_count += 1
                else:
                    logger.warning(f"未找到 {msg_type} 消息处理器")
                    
        except Exception as e:
            logger.error(f"批量消息处理失败: {e}")
            self.error_count += 1
            
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'queue_sizes': {
                priority.name: queue.qsize() 
                for priority, queue in self.message_queues.items()
            }
        }


class ReconnectStrategy:
    """重连策略"""
    
    def __init__(self, 
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 max_retries: int = -1,  # -1表示无限重试
                 jitter: bool = True):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.jitter = jitter
        
        self.current_delay = initial_delay
        self.retry_count = 0
        
    def get_next_delay(self) -> float:
        """获取下次重连延迟"""
        if self.max_retries > 0 and self.retry_count >= self.max_retries:
            raise Exception("已达到最大重试次数")
            
        delay = self.current_delay
        
        # 添加随机抖动避免雷群效应
        if self.jitter:
            delay += random.uniform(0, delay * 0.1)
            
        # 指数退避
        self.current_delay = min(self.max_delay, self.current_delay * self.backoff_factor)
        self.retry_count += 1
        
        return delay
        
    def reset(self) -> None:
        """重置重连策略"""
        self.current_delay = self.initial_delay
        self.retry_count = 0


class EnhancedTradingViewClient(Client):
    """增强版TradingView客户端"""
    
    def __init__(self, options=None, **kwargs):
        # 如果没有提供认证信息，尝试从认证管理器获取
        if options is None:
            options = {}
        
        if not options.get('token') or not options.get('signature'):
            try:
                from .auth_config import get_tradingview_auth
                auth_info = get_tradingview_auth(options.get('account_name'))
                if auth_info:
                    options.update(auth_info)
            except ImportError:
                pass  # 认证管理器不可用，继续使用传入的参数
        
        super().__init__(options, **kwargs)
        
        # 连接监控
        self.monitor = ConnectionMonitor(client_ref=self)
        
        # 消息处理器
        self.message_processor = MessageProcessor()
        
        # 重连策略
        self.reconnect_strategy = ReconnectStrategy()
        
        # 增强功能配置
        self.auto_reconnect = kwargs.get('auto_reconnect', True)
        self.health_check_interval = kwargs.get('health_check_interval', 30)
        self.enable_message_batching = kwargs.get('enable_message_batching', True)
        
        # 任务管理
        self.health_check_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        
        # 增强回调
        self.connection_state_callbacks = []
        self.health_callbacks = []
        
        # 统计信息
        self.stats = {
            'total_messages': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'total_reconnects': 0
        }
        
    async def connect(self, **kwargs) -> bool:
        """增强的连接方法"""
        try:
            self.monitor.state = ConnectionState.CONNECTING
            self._notify_connection_state_change(ConnectionState.CONNECTING)
            
            # 调用父类连接方法
            success = await super().connect(**kwargs)
            
            if success:
                self.monitor.state = ConnectionState.CONNECTED
                self.monitor.uptime_start = time.time()
                # 修复：初始化心跳时间，避免健康检查错误判断
                self.monitor.last_pong_time = time.time()
                self.stats['successful_connections'] += 1
                
                # 启动增强功能
                await self._start_enhanced_features()
                
                self._notify_connection_state_change(ConnectionState.CONNECTED)
                logger.info("✅ TradingView增强客户端连接成功")
                return True
            else:
                self.monitor.state = ConnectionState.FAILED
                self.stats['failed_connections'] += 1
                self._notify_connection_state_change(ConnectionState.FAILED)
                logger.error("❌ TradingView增强客户端连接失败")
                logger.debug(f"🐛 连接失败详情:")
                logger.debug(f"🐛   - 客户端类型: {type(self).__name__}")
                logger.debug(f"🐛   - WebSocket对象: {self._ws is not None}")
                if self._ws:
                    ws_state = getattr(self._ws, 'state', 'unknown')
                    logger.debug(f"🐛   - WebSocket状态: {ws_state}")
                    logger.debug(f"🐛   - WebSocket已关闭: {getattr(self._ws, 'closed', 'unknown')}")
                logger.debug(f"🐛   - 连接监控状态: {self.monitor.state}")  
                logger.debug(f"🐛   - 连接质量: {self.monitor.connection_quality}")
                logger.debug(f"🐛   - 错误计数: {self.monitor.error_count}")
                return False
                
        except Exception as e:
            self.monitor.state = ConnectionState.FAILED
            self.stats['failed_connections'] += 1
            self._notify_connection_state_change(ConnectionState.FAILED)
            logger.error(f"连接异常: {e}")
            logger.debug(f"🐛 连接异常详情:")
            logger.debug(f"🐛   - 异常类型: {type(e).__name__}")
            logger.debug(f"🐛   - 异常信息: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.debug(f"🐛   - 异常堆栈: {traceback.format_exc()}")
            
            # 如果启用自动重连，开始重连
            if self.auto_reconnect:
                asyncio.create_task(self._auto_reconnect())
                
            return False
            
    async def _start_enhanced_features(self) -> None:
        """启动增强功能"""
        try:
            # 启动消息处理器
            if self.enable_message_batching:
                await self.message_processor.start()
                
            # 启动健康检查
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            # 启动心跳检查
            self.ping_task = asyncio.create_task(self._ping_loop())
            
            logger.info("增强功能已启动")
            
        except Exception as e:
            logger.error(f"启动增强功能失败: {e}")
            
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.monitor.state == ConnectionState.CONNECTED:
            try:
                is_healthy = self.monitor.is_healthy()
                quality_score = self.monitor.calculate_quality_score()
                
                # 通知健康状态回调
                health_info = {
                    'is_healthy': is_healthy,
                    'quality_score': quality_score,
                    'average_latency': self.monitor.get_average_latency(),
                    'error_count': self.monitor.error_count,
                    'uptime': self.monitor.get_uptime()
                }
                
                for callback in self.health_callbacks:
                    try:
                        await callback(health_info)
                    except Exception as e:
                        logger.error(f"健康状态回调失败: {e}")
                
                # 如果不健康且启用自动重连，触发重连
                if not is_healthy and self.auto_reconnect:
                    logger.warning("连接不健康，触发重连")
                    asyncio.create_task(self._auto_reconnect())
                    break
                    
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"健康检查错误: {e}")
                await asyncio.sleep(5)
                
    async def _ping_loop(self) -> None:
        """心跳循环 - 主要用于更新监控状态"""
        while self.monitor.state == ConnectionState.CONNECTED:
            try:
                # 记录心跳时间用于监控
                self.monitor.record_ping()
                # 如果基础连接正常，也记录pong（模拟正常心跳）
                if self.is_open:
                    self.monitor.record_pong()
                
                await asyncio.sleep(self.monitor.ping_interval)
                
            except Exception as e:
                logger.error(f"心跳检查错误: {e}")
                await asyncio.sleep(5)
                
    async def _auto_reconnect(self) -> None:
        """自动重连"""
        if self.monitor.state == ConnectionState.RECONNECTING:
            return  # 避免重复重连
            
        self.monitor.state = ConnectionState.RECONNECTING
        self._notify_connection_state_change(ConnectionState.RECONNECTING)
        
        try:
            while self.auto_reconnect:
                try:
                    delay = self.reconnect_strategy.get_next_delay()
                    logger.info(f"🔄 {delay:.1f}秒后重连 (第{self.reconnect_strategy.retry_count}次)")
                    
                    await asyncio.sleep(delay)
                    
                    # 清理现有连接
                    await self._cleanup_connection()
                    
                    # 尝试重连
                    success = await self.connect()
                    
                    if success:
                        self.reconnect_strategy.reset()
                        self.monitor.record_reconnect()
                        self.stats['total_reconnects'] += 1
                        logger.info("✅ 重连成功")
                        return
                    else:
                        logger.warning("❌ 重连失败，继续尝试")
                        
                except Exception as e:
                    if "已达到最大重试次数" in str(e):
                        logger.error("已达到最大重试次数，停止重连")
                        break
                    else:
                        logger.error(f"重连异常: {e}")
                        
        except Exception as e:
            logger.error(f"自动重连失败: {e}")
        finally:
            if self.monitor.state == ConnectionState.RECONNECTING:
                self.monitor.state = ConnectionState.FAILED
                self._notify_connection_state_change(ConnectionState.FAILED)
                
    async def _cleanup_connection(self) -> None:
        """清理连接"""
        try:
            # 停止增强功能
            if self.health_check_task:
                self.health_check_task.cancel()
                
            if self.ping_task:
                self.ping_task.cancel()
                
            # 停止消息处理器
            await self.message_processor.stop()
            
            # 关闭WebSocket连接
            if self._ws:
                await self._ws.close()
                
        except Exception as e:
            logger.error(f"清理连接失败: {e}")
            
    def _notify_connection_state_change(self, new_state: ConnectionState) -> None:
        """通知连接状态变更"""
        for callback in self.connection_state_callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.error(f"连接状态回调失败: {e}")
                
    # 增强的公共接口
    def on_connection_state_change(self, callback: Callable[[ConnectionState], None]) -> None:
        """注册连接状态变更回调"""
        self.connection_state_callbacks.append(callback)
        
    def on_health_update(self, callback: Callable[[Dict], None]) -> None:
        """注册健康状态更新回调"""
        self.health_callbacks.append(callback)
        
    @property
    def is_connected(self) -> bool:
        """检查是否已连接 - 兼容连接管理器的接口"""
        return self.is_open and self.monitor.state == ConnectionState.CONNECTED
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            'state': self.monitor.state.value,
            'quality_score': self.monitor.connection_quality,
            'average_latency': self.monitor.get_average_latency(),
            'uptime': self.monitor.get_uptime(),
            'error_count': self.monitor.error_count,
            'total_reconnects': self.monitor.total_reconnects,
            'stats': self.stats,
            'message_processor_stats': self.message_processor.get_stats()
        }
        
    async def disconnect(self) -> None:
        """增强的断开连接方法"""
        self.auto_reconnect = False  # 禁用自动重连
        
        await self._cleanup_connection()
        
        self.monitor.state = ConnectionState.DISCONNECTED
        self._notify_connection_state_change(ConnectionState.DISCONNECTED)
        
        await super().end()
        logger.info("🔌 TradingView增强客户端已断开连接")


# 为了向后兼容，创建别名
EnhancedTradingViewClient = EnhancedTradingViewClient