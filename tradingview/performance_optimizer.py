#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView性能优化系统
实现智能缓存、连接池管理和性能优化
"""

import asyncio
import time
import json
import weakref
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict, OrderedDict
from enum import Enum, auto
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from config.logging_config import get_logger

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = auto()        # 最近最少使用
    LFU = auto()        # 最少使用频率
    TTL = auto()        # 生存时间
    ADAPTIVE = auto()   # 自适应


class ConnectionStatus(Enum):
    """连接状态"""
    IDLE = auto()
    ACTIVE = auto()
    ERROR = auto()
    CLOSED = auto()


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    access_count: int = 0
    last_access_time: float = field(default_factory=time.time)
    created_time: float = field(default_factory=time.time)
    ttl_seconds: Optional[float] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_time > self.ttl_seconds
    
    def touch(self) -> None:
        """更新访问信息"""
        self.access_count += 1
        self.last_access_time = time.time()


@dataclass
class ConnectionMetrics:
    """连接指标"""
    connection_id: str
    created_time: float = field(default_factory=time.time)
    last_used_time: float = field(default_factory=time.time)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    average_latency_ms: float = 0.0
    status: ConnectionStatus = ConnectionStatus.IDLE


class IntelligentCache:
    """智能缓存系统"""
    
    def __init__(self, max_size: int = 10000, strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 default_ttl: Optional[float] = 3600):
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        # 缓存存储
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size_bytes': 0,
            'entry_count': 0
        }
        
        # 自适应缓存配置
        self.adaptive_config = {
            'hit_rate_threshold': 0.8,
            'size_threshold_ratio': 0.9,
            'adjustment_interval': 300  # 5分钟
        }
        
        # 清理任务
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start(self) -> None:
        """启动缓存系统"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("智能缓存系统已启动")
    
    async def stop(self) -> None:
        """停止缓存系统"""
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("智能缓存系统已停止")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            with self.lock:
                if key not in self.cache:
                    self.stats['misses'] += 1
                    return None
                
                entry = self.cache[key]
                
                # 检查是否过期
                if entry.is_expired():
                    del self.cache[key]
                    self.stats['misses'] += 1
                    self._update_size_stats()
                    return None
                
                # 更新访问信息
                entry.touch()
                
                # LRU策略：移动到末尾
                if self.strategy in [CacheStrategy.LRU, CacheStrategy.ADAPTIVE]:
                    self.cache.move_to_end(key)
                
                self.stats['hits'] += 1
                return entry.value
                
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存值"""
        try:
            with self.lock:
                # 计算大小
                size_bytes = self._calculate_size(value)
                
                # 创建缓存条目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl_seconds=ttl or self.default_ttl,
                    size_bytes=size_bytes
                )
                
                # 如果键已存在，更新
                if key in self.cache:
                    old_entry = self.cache[key]
                    self.stats['total_size_bytes'] -= old_entry.size_bytes
                
                # 添加到缓存
                self.cache[key] = entry
                self.stats['total_size_bytes'] += size_bytes
                self.stats['entry_count'] = len(self.cache)
                
                # 检查是否需要清理
                await self._check_and_evict()
                
                return True
                
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def remove(self, key: str) -> bool:
        """移除缓存条目"""
        try:
            with self.lock:
                if key in self.cache:
                    entry = self.cache[key]
                    del self.cache[key]
                    self.stats['total_size_bytes'] -= entry.size_bytes
                    self.stats['entry_count'] = len(self.cache)
                    return True
                return False
                
        except Exception as e:
            logger.error(f"移除缓存失败: {e}")
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        try:
            with self.lock:
                self.cache.clear()
                self.stats['total_size_bytes'] = 0
                self.stats['entry_count'] = 0
                self.stats['evictions'] += len(self.cache)
                
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    async def _check_and_evict(self) -> None:
        """检查并清理缓存"""
        try:
            # 如果未超过限制，不需要清理
            if len(self.cache) <= self.max_size:
                return
            
            # 根据策略清理
            if self.strategy == CacheStrategy.LRU:
                await self._evict_lru()
            elif self.strategy == CacheStrategy.LFU:
                await self._evict_lfu()
            elif self.strategy == CacheStrategy.TTL:
                await self._evict_expired()
            elif self.strategy == CacheStrategy.ADAPTIVE:
                await self._evict_adaptive()
                
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
    
    async def _evict_lru(self) -> None:
        """LRU清理策略"""
        try:
            evict_count = len(self.cache) - self.max_size + 1
            
            for _ in range(min(evict_count, len(self.cache))):
                if self.cache:
                    key, entry = self.cache.popitem(last=False)  # 移除最旧的
                    self.stats['total_size_bytes'] -= entry.size_bytes
                    self.stats['evictions'] += 1
                    
        except Exception as e:
            logger.error(f"LRU清理失败: {e}")
    
    async def _evict_lfu(self) -> None:
        """LFU清理策略"""
        try:
            # 按访问次数排序
            items = sorted(self.cache.items(), key=lambda x: x[1].access_count)
            evict_count = len(self.cache) - self.max_size + 1
            
            for i in range(min(evict_count, len(items))):
                key, entry = items[i]
                if key in self.cache:
                    del self.cache[key]
                    self.stats['total_size_bytes'] -= entry.size_bytes
                    self.stats['evictions'] += 1
                    
        except Exception as e:
            logger.error(f"LFU清理失败: {e}")
    
    async def _evict_expired(self) -> None:
        """清理过期条目"""
        try:
            expired_keys = [
                key for key, entry in self.cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                if key in self.cache:
                    entry = self.cache[key]
                    del self.cache[key]
                    self.stats['total_size_bytes'] -= entry.size_bytes
                    self.stats['evictions'] += 1
                    
        except Exception as e:
            logger.error(f"过期清理失败: {e}")
    
    async def _evict_adaptive(self) -> None:
        """自适应清理策略"""
        try:
            # 先清理过期的
            await self._evict_expired()
            
            # 如果还需要清理，根据命中率决定策略
            if len(self.cache) > self.max_size:
                hit_rate = self._calculate_hit_rate()
                
                if hit_rate > self.adaptive_config['hit_rate_threshold']:
                    # 命中率高，使用LFU
                    await self._evict_lfu()
                else:
                    # 命中率低，使用LRU
                    await self._evict_lru()
                    
        except Exception as e:
            logger.error(f"自适应清理失败: {e}")
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while self.is_running:
            try:
                await self._evict_expired()
                await asyncio.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
                await asyncio.sleep(5)
    
    def _calculate_size(self, value: Any) -> int:
        """计算对象大小"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) 
                          for k, v in value.items())
            else:
                # 使用JSON序列化估算大小
                return len(json.dumps(value, default=str))
                
        except Exception:
            return 1024  # 默认1KB
    
    def _calculate_hit_rate(self) -> float:
        """计算命中率"""
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests == 0:
            return 0.0
        return self.stats['hits'] / total_requests
    
    def _update_size_stats(self) -> None:
        """更新大小统计"""
        self.stats['entry_count'] = len(self.cache)
        self.stats['total_size_bytes'] = sum(entry.size_bytes for entry in self.cache.values())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            hit_rate = self._calculate_hit_rate()
            
            return {
                **self.stats,
                'hit_rate': hit_rate,
                'miss_rate': 1 - hit_rate,
                'max_size': self.max_size,
                'current_size': len(self.cache),
                'fill_ratio': len(self.cache) / self.max_size,
                'average_entry_size': (self.stats['total_size_bytes'] / max(1, len(self.cache))),
                'strategy': self.strategy.name
            }


class ConnectionPool:
    """连接池管理器"""
    
    def __init__(self, min_connections: int = 5, max_connections: int = 50,
                 connection_timeout: float = 30.0, idle_timeout: float = 300.0):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        
        # 连接池
        self.idle_connections: deque = deque()
        self.active_connections: Dict[str, Any] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        
        # 锁和信号量
        self.lock = threading.RLock()
        self.connection_semaphore = asyncio.Semaphore(max_connections)
        
        # 连接工厂
        self.connection_factory: Optional[Callable] = None
        
        # 管理任务
        self.management_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # 统计信息
        self.pool_stats = {
            'total_created': 0,
            'total_destroyed': 0,
            'current_active': 0,
            'current_idle': 0,
            'connection_requests': 0,
            'connection_timeouts': 0,
            'average_wait_time_ms': 0.0
        }
    
    async def initialize(self, connection_factory: Callable) -> bool:
        """初始化连接池"""
        try:
            self.connection_factory = connection_factory
            
            # 创建最小连接数
            for _ in range(self.min_connections):
                connection = await self._create_connection()
                if connection:
                    self.idle_connections.append(connection)
            
            # 启动管理任务
            self.is_running = True
            self.management_task = asyncio.create_task(self._management_loop())
            
            logger.info(f"✅ 连接池初始化成功，初始连接数: {len(self.idle_connections)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 连接池初始化失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭连接池"""
        try:
            self.is_running = False
            
            # 停止管理任务
            if self.management_task:
                self.management_task.cancel()
                try:
                    await self.management_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭所有连接
            with self.lock:
                # 关闭空闲连接
                while self.idle_connections:
                    connection = self.idle_connections.popleft()
                    await self._destroy_connection(connection)
                
                # 关闭活跃连接
                for connection_id, connection in list(self.active_connections.items()):
                    await self._destroy_connection(connection)
                    del self.active_connections[connection_id]
            
            logger.info("连接池已关闭")
            
        except Exception as e:
            logger.error(f"关闭连接池失败: {e}")
    
    async def get_connection(self, timeout: Optional[float] = None) -> Optional[Any]:
        """获取连接"""
        start_time = time.perf_counter()
        timeout = timeout or self.connection_timeout
        
        try:
            # 获取连接权限
            await asyncio.wait_for(
                self.connection_semaphore.acquire(), 
                timeout=timeout
            )
            
            self.pool_stats['connection_requests'] += 1
            
            with self.lock:
                # 尝试从空闲连接获取
                connection = await self._get_idle_connection()
                
                if connection is None:
                    # 创建新连接
                    connection = await self._create_connection()
                
                if connection:
                    # 移到活跃连接
                    connection_id = id(connection)
                    self.active_connections[str(connection_id)] = connection
                    
                    # 更新指标
                    if str(connection_id) not in self.connection_metrics:
                        self.connection_metrics[str(connection_id)] = ConnectionMetrics(
                            connection_id=str(connection_id)
                        )
                    
                    metrics = self.connection_metrics[str(connection_id)]
                    metrics.last_used_time = time.time()
                    metrics.status = ConnectionStatus.ACTIVE
                    
                    # 更新统计
                    self._update_pool_stats()
                    
                    # 记录等待时间
                    wait_time = (time.perf_counter() - start_time) * 1000
                    self._update_wait_time_stats(wait_time)
                    
                    return connection
                else:
                    self.connection_semaphore.release()
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning("获取连接超时")
            self.pool_stats['connection_timeouts'] += 1
            return None
        except Exception as e:
            logger.error(f"获取连接失败: {e}")
            self.connection_semaphore.release()
            return None
    
    async def return_connection(self, connection: Any) -> bool:
        """归还连接"""
        try:
            with self.lock:
                connection_id = str(id(connection))
                
                if connection_id in self.active_connections:
                    # 从活跃连接移除
                    del self.active_connections[connection_id]
                    
                    # 检查连接健康状态
                    if await self._is_connection_healthy(connection):
                        # 放回空闲连接
                        self.idle_connections.append(connection)
                        
                        # 更新指标
                        if connection_id in self.connection_metrics:
                            metrics = self.connection_metrics[connection_id]
                            metrics.status = ConnectionStatus.IDLE
                    else:
                        # 销毁不健康的连接
                        await self._destroy_connection(connection)
                        del self.connection_metrics[connection_id]
                    
                    # 更新统计
                    self._update_pool_stats()
                    
                    # 释放信号量
                    self.connection_semaphore.release()
                    
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"归还连接失败: {e}")
            return False
    
    async def _get_idle_connection(self) -> Optional[Any]:
        """获取空闲连接"""
        try:
            while self.idle_connections:
                connection = self.idle_connections.popleft()
                
                # 检查连接是否健康
                if await self._is_connection_healthy(connection):
                    return connection
                else:
                    # 销毁不健康的连接
                    await self._destroy_connection(connection)
                    connection_id = str(id(connection))
                    if connection_id in self.connection_metrics:
                        del self.connection_metrics[connection_id]
            
            return None
            
        except Exception as e:
            logger.error(f"获取空闲连接失败: {e}")
            return None
    
    async def _create_connection(self) -> Optional[Any]:
        """创建新连接"""
        try:
            if not self.connection_factory:
                return None
            
            connection = await self.connection_factory()
            if connection:
                self.pool_stats['total_created'] += 1
                logger.debug("创建新连接成功")
                return connection
            
            return None
            
        except Exception as e:
            logger.error(f"创建连接失败: {e}")
            return None
    
    async def _destroy_connection(self, connection: Any) -> None:
        """销毁连接"""
        try:
            if hasattr(connection, 'close'):
                await connection.close()
            elif hasattr(connection, 'disconnect'):
                await connection.disconnect()
            
            self.pool_stats['total_destroyed'] += 1
            logger.debug("销毁连接成功")
            
        except Exception as e:
            logger.error(f"销毁连接失败: {e}")
    
    async def _is_connection_healthy(self, connection: Any) -> bool:
        """检查连接健康状态"""
        try:
            # 这里可以实现具体的健康检查逻辑
            # 例如发送ping命令或检查连接状态
            if hasattr(connection, 'is_connected'):
                return connection.is_connected()
            elif hasattr(connection, 'ping'):
                await connection.ping()
                return True
            
            return True  # 默认认为健康
            
        except Exception as e:
            logger.debug(f"连接健康检查失败: {e}")
            return False
    
    async def _management_loop(self) -> None:
        """连接池管理循环"""
        while self.is_running:
            try:
                await self._maintain_min_connections()
                await self._cleanup_idle_connections()
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"连接池管理异常: {e}")
                await asyncio.sleep(5)
    
    async def _maintain_min_connections(self) -> None:
        """维护最小连接数"""
        try:
            with self.lock:
                current_total = len(self.idle_connections) + len(self.active_connections)
                
                if current_total < self.min_connections:
                    needed = self.min_connections - current_total
                    
                    for _ in range(needed):
                        connection = await self._create_connection()
                        if connection:
                            self.idle_connections.append(connection)
                        else:
                            break
                            
        except Exception as e:
            logger.error(f"维护最小连接数失败: {e}")
    
    async def _cleanup_idle_connections(self) -> None:
        """清理空闲连接"""
        try:
            current_time = time.time()
            
            with self.lock:
                # 清理超时的空闲连接
                idle_to_remove = []
                
                for connection in list(self.idle_connections):
                    connection_id = str(id(connection))
                    metrics = self.connection_metrics.get(connection_id)
                    
                    if metrics and current_time - metrics.last_used_time > self.idle_timeout:
                        if len(self.idle_connections) + len(self.active_connections) > self.min_connections:
                            idle_to_remove.append(connection)
                
                # 移除超时连接
                for connection in idle_to_remove:
                    self.idle_connections.remove(connection)
                    await self._destroy_connection(connection)
                    
                    connection_id = str(id(connection))
                    if connection_id in self.connection_metrics:
                        del self.connection_metrics[connection_id]
                        
        except Exception as e:
            logger.error(f"清理空闲连接失败: {e}")
    
    def _update_pool_stats(self) -> None:
        """更新连接池统计"""
        self.pool_stats['current_active'] = len(self.active_connections)
        self.pool_stats['current_idle'] = len(self.idle_connections)
    
    def _update_wait_time_stats(self, wait_time_ms: float) -> None:
        """更新等待时间统计"""
        current_avg = self.pool_stats['average_wait_time_ms']
        requests = self.pool_stats['connection_requests']
        
        if requests > 0:
            new_avg = ((current_avg * (requests - 1)) + wait_time_ms) / requests
            self.pool_stats['average_wait_time_ms'] = new_avg
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        with self.lock:
            return {
                **self.pool_stats,
                'min_connections': self.min_connections,
                'max_connections': self.max_connections,
                'connection_timeout': self.connection_timeout,
                'idle_timeout': self.idle_timeout,
                'connection_efficiency': (
                    self.pool_stats['total_created'] / max(1, self.pool_stats['connection_requests'])
                ),
                'connection_metrics_count': len(self.connection_metrics)
            }


class PerformanceOptimizer:
    """性能优化管理器"""
    
    def __init__(self):
        # 核心组件
        self.cache = IntelligentCache()
        self.connection_pool = ConnectionPool()
        
        # 系统监控
        self.system_monitor = SystemMonitor()
        
        # 优化配置
        self.optimization_config = {
            'enable_auto_optimization': True,
            'memory_threshold': 0.85,  # 85%内存使用率
            'cpu_threshold': 0.80,     # 80%CPU使用率
            'optimization_interval': 60,  # 优化检查间隔60秒
        }
        
        # 运行状态
        self.is_running = False
        self.optimization_task: Optional[asyncio.Task] = None
        
        # 性能统计
        self.performance_stats = {
            'optimization_cycles': 0,
            'cache_optimizations': 0,
            'connection_optimizations': 0,
            'memory_optimizations': 0,
            'last_optimization_time': 0.0
        }
    
    async def initialize(self, connection_factory: Optional[Callable] = None) -> bool:
        """初始化性能优化器"""
        try:
            # 启动缓存系统
            await self.cache.start()
            
            # 初始化连接池
            if connection_factory:
                await self.connection_pool.initialize(connection_factory)
            
            # 启动系统监控
            await self.system_monitor.start()
            
            # 启动优化任务
            if self.optimization_config['enable_auto_optimization']:
                self.is_running = True
                self.optimization_task = asyncio.create_task(self._optimization_loop())
            
            logger.info("✅ 性能优化器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 性能优化器初始化失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭性能优化器"""
        try:
            self.is_running = False
            
            # 停止优化任务
            if self.optimization_task:
                self.optimization_task.cancel()
                try:
                    await self.optimization_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭组件
            await self.system_monitor.stop()
            await self.connection_pool.shutdown()
            await self.cache.stop()
            
            logger.info("性能优化器已关闭")
            
        except Exception as e:
            logger.error(f"关闭性能优化器失败: {e}")
    
    async def _optimization_loop(self) -> None:
        """优化循环"""
        while self.is_running:
            try:
                self.performance_stats['optimization_cycles'] += 1
                
                # 获取系统指标
                system_metrics = self.system_monitor.get_system_metrics()
                
                # 内存优化
                if system_metrics['memory_usage'] > self.optimization_config['memory_threshold']:
                    await self._optimize_memory()
                
                # 缓存优化
                cache_stats = self.cache.get_cache_stats()
                if cache_stats['hit_rate'] < 0.7:  # 命中率低于70%
                    await self._optimize_cache()
                
                # 连接池优化
                pool_stats = self.connection_pool.get_pool_stats()
                if pool_stats['average_wait_time_ms'] > 100:  # 等待时间超过100ms
                    await self._optimize_connections()
                
                self.performance_stats['last_optimization_time'] = time.time()
                
                await asyncio.sleep(self.optimization_config['optimization_interval'])
                
            except Exception as e:
                logger.error(f"优化循环异常: {e}")
                await asyncio.sleep(10)
    
    async def _optimize_memory(self) -> None:
        """内存优化"""
        try:
            logger.info("执行内存优化...")
            
            # 强制垃圾回收
            gc.collect()
            
            # 清理缓存中的过期条目
            await self.cache._evict_expired()
            
            # 如果内存使用率仍然很高，减少缓存大小
            system_metrics = self.system_monitor.get_system_metrics()
            if system_metrics['memory_usage'] > 0.9:
                current_size = self.cache.max_size
                new_size = int(current_size * 0.8)  # 减少20%
                self.cache.max_size = max(100, new_size)
                logger.info(f"调整缓存大小: {current_size} -> {new_size}")
            
            self.performance_stats['memory_optimizations'] += 1
            
        except Exception as e:
            logger.error(f"内存优化失败: {e}")
    
    async def _optimize_cache(self) -> None:
        """缓存优化"""
        try:
            logger.info("执行缓存优化...")
            
            cache_stats = self.cache.get_cache_stats()
            
            # 如果命中率低，调整策略
            if cache_stats['hit_rate'] < 0.5:
                # 切换到LFU策略
                self.cache.strategy = CacheStrategy.LFU
                logger.info("切换缓存策略为LFU")
            elif cache_stats['hit_rate'] < 0.7:
                # 切换到自适应策略
                self.cache.strategy = CacheStrategy.ADAPTIVE
                logger.info("切换缓存策略为ADAPTIVE")
            
            # 清理低频访问的缓存
            if self.cache.strategy == CacheStrategy.LFU:
                await self.cache._evict_lfu()
            
            self.performance_stats['cache_optimizations'] += 1
            
        except Exception as e:
            logger.error(f"缓存优化失败: {e}")
    
    async def _optimize_connections(self) -> None:
        """连接优化"""
        try:
            logger.info("执行连接优化...")
            
            # 清理空闲连接
            await self.connection_pool._cleanup_idle_connections()
            
            # 检查是否需要增加最小连接数
            pool_stats = self.connection_pool.get_pool_stats()
            if pool_stats['average_wait_time_ms'] > 200:  # 等待时间过长
                current_min = self.connection_pool.min_connections
                new_min = min(current_min + 2, self.connection_pool.max_connections)
                self.connection_pool.min_connections = new_min
                logger.info(f"调整最小连接数: {current_min} -> {new_min}")
            
            self.performance_stats['connection_optimizations'] += 1
            
        except Exception as e:
            logger.error(f"连接优化失败: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计"""
        return {
            'cache_stats': self.cache.get_cache_stats(),
            'pool_stats': self.connection_pool.get_pool_stats(),
            'system_metrics': self.system_monitor.get_system_metrics(),
            'performance_stats': self.performance_stats,
            'optimization_config': self.optimization_config,
            'is_running': self.is_running
        }


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动系统监控"""
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("系统监控器已启动")
    
    async def stop(self) -> None:
        """停止系统监控"""
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("系统监控器已停止")
    
    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.is_running:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                await asyncio.sleep(10)  # 每10秒收集一次
                
            except Exception as e:
                logger.error(f"系统监控异常: {e}")
                await asyncio.sleep(5)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            return {
                'timestamp': time.time(),
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent / 100.0,
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'disk_usage': psutil.disk_usage('/').percent / 100.0,
                'network_io': psutil.net_io_counters()._asdict(),
                'process_count': len(psutil.pids()),
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {
                'timestamp': time.time(),
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'memory_available_gb': 0.0,
                'disk_usage': 0.0,
                'network_io': {},
                'process_count': 0,
                'load_average': None
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取最新系统指标"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return self._collect_system_metrics()
    
    def get_metrics_history(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """获取历史指标"""
        cutoff_time = time.time() - (minutes * 60)
        return [
            metrics for metrics in self.metrics_history 
            if metrics['timestamp'] > cutoff_time
        ]


# 便捷函数
def create_performance_optimizer() -> PerformanceOptimizer:
    """创建性能优化器"""
    return PerformanceOptimizer()


async def test_performance_optimizer():
    """测试性能优化器"""
    optimizer = create_performance_optimizer()
    
    try:
        # 初始化优化器
        await optimizer.initialize()
        
        # 测试缓存
        cache = optimizer.cache
        
        # 添加测试数据
        for i in range(100):
            await cache.put(f"key_{i}", f"value_{i}")
        
        # 测试缓存命中
        for i in range(50):
            value = cache.get(f"key_{i}")
            print(f"Cache get key_{i}: {value}")
        
        # 获取统计信息
        stats = optimizer.get_comprehensive_stats()
        print(f"优化器统计: {json.dumps(stats, indent=2, default=str)}")
        
        # 等待一段时间观察优化
        await asyncio.sleep(30)
        
    finally:
        await optimizer.shutdown()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_performance_optimizer())


