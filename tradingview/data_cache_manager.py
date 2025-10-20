#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView数据缓存管理器
实现SQLite本地缓存和内存缓存的双层缓存架构
"""

import asyncio
import sqlite3
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import OrderedDict, defaultdict
import logging

from config.logging_config import get_logger

logger = get_logger(__name__)


class CacheStatus(Enum):
    """缓存状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class CacheLevel(Enum):
    """缓存级别枚举"""
    MEMORY = "memory"
    SQLITE = "sqlite"
    BOTH = "both"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Dict[str, Any]
    timestamp: int
    access_count: int
    quality_score: float
    expire_time: int
    size_bytes: int


@dataclass  
class CacheStatistics:
    """缓存统计信息"""
    total_entries: int
    memory_entries: int
    sqlite_entries: int
    total_size_mb: float
    hit_rate: float
    miss_rate: float
    eviction_count: int
    last_cleanup_time: int


class LRUCache:
    """LRU内存缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        """初始化LRU缓存"""
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        
    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 移到末尾表示最近使用
                entry = self.cache.pop(key)
                self.cache[key] = entry
                entry.access_count += 1
                self.hit_count += 1
                return entry
            else:
                self.miss_count += 1
                return None
    
    def put(self, key: str, entry: CacheEntry) -> None:
        """存储缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新现有项
                self.cache.pop(key)
                self.cache[key] = entry
            else:
                # 添加新项
                if len(self.cache) >= self.max_size:
                    # 移除最久未使用的项
                    oldest_key, _ = self.cache.popitem(last=False)
                    logger.debug(f"LRU缓存淘汰: {oldest_key}")
                
                self.cache[key] = entry
    
    def remove(self, key: str) -> bool:
        """移除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def get_hit_rate(self) -> float:
        """获取命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def get_size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class SQLiteCacheManager:
    """SQLite缓存管理器"""
    
    def __init__(self, db_path: str):
        """初始化SQLite缓存"""
        self.db_path = db_path
        self.connection_pool = {}
        self.lock = threading.RLock()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # 优化SQLite性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            self.connection_pool[thread_id] = conn
        
        return self.connection_pool[thread_id]
    
    def _init_database(self) -> None:
        """初始化数据库表"""
        conn = self._get_connection()
        
        # 创建K线数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kline_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                data_json TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                expire_time INTEGER NOT NULL,
                access_count INTEGER DEFAULT 0,
                quality_score REAL NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        
        # 创建实时数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS realtime_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                data_json TEXT NOT NULL,
                PRIMARY KEY (symbol, timeframe)
            ) WITHOUT ROWID
        """)
        
        # 创建品种信息表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS symbol_info (
                symbol TEXT PRIMARY KEY,
                exchange TEXT NOT NULL,
                base_currency TEXT,
                quote_currency TEXT,
                symbol_type TEXT,
                active BOOLEAN DEFAULT TRUE,
                last_updated INTEGER NOT NULL
            ) WITHOUT ROWID
        """)
        
        # 创建缓存统计表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                metric_name TEXT PRIMARY KEY,
                metric_value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            ) WITHOUT ROWID
        """)
        
        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kline_symbol_timeframe ON kline_cache(symbol, timeframe)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kline_timestamp ON kline_cache(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kline_expire ON kline_cache(expire_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_realtime_timestamp ON realtime_cache(timestamp)")
        
        conn.commit()
        logger.info(f"SQLite缓存数据库初始化完成: {self.db_path}")
    
    def store_kline_data(self, cache_key: str, symbol: str, timeframe: str, 
                        data: Dict[str, Any], quality_score: float, 
                        expire_seconds: int = 3600) -> bool:
        """存储K线数据"""
        try:
            conn = self._get_connection()
            
            data_json = json.dumps(data, ensure_ascii=False)
            size_bytes = len(data_json.encode('utf-8'))
            current_time = int(time.time())
            expire_time = current_time + expire_seconds
            
            with self.lock:
                conn.execute("""
                    INSERT OR REPLACE INTO kline_cache 
                    (cache_key, symbol, timeframe, data_json, timestamp, expire_time,
                     quality_score, size_bytes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cache_key, symbol, timeframe, data_json, current_time, expire_time,
                    quality_score, size_bytes, current_time, current_time
                ))
                
                conn.commit()
            
            logger.debug(f"SQLite存储K线数据: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"SQLite存储K线数据失败: {e}")
            return False
    
    def get_kline_data(self, cache_key: str) -> Optional[CacheEntry]:
        """获取K线数据"""
        try:
            conn = self._get_connection()
            
            with self.lock:
                cursor = conn.execute("""
                    SELECT * FROM kline_cache 
                    WHERE cache_key = ? AND expire_time > ?
                """, (cache_key, int(time.time())))
                
                row = cursor.fetchone()
                
                if row:
                    # 更新访问计数
                    conn.execute("""
                        UPDATE kline_cache 
                        SET access_count = access_count + 1, updated_at = ?
                        WHERE cache_key = ?
                    """, (int(time.time()), cache_key))
                    conn.commit()
                    
                    # 构建缓存条目
                    data = json.loads(row['data_json'])
                    entry = CacheEntry(
                        key=row['cache_key'],
                        data=data,
                        timestamp=row['timestamp'],
                        access_count=row['access_count'] + 1,
                        quality_score=row['quality_score'],
                        expire_time=row['expire_time'],
                        size_bytes=row['size_bytes']
                    )
                    
                    logger.debug(f"SQLite获取K线数据: {cache_key}")
                    return entry
                
                return None
                
        except Exception as e:
            logger.error(f"SQLite获取K线数据失败: {e}")
            return None
    
    def cleanup_expired_data(self) -> int:
        """清理过期数据"""
        try:
            conn = self._get_connection()
            current_time = int(time.time())
            
            with self.lock:
                cursor = conn.execute("""
                    DELETE FROM kline_cache WHERE expire_time < ?
                """, (current_time,))
                
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                logger.info(f"SQLite清理过期数据: {deleted_count}条")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"SQLite清理过期数据失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取SQLite缓存统计"""
        try:
            conn = self._get_connection()
            
            with self.lock:
                # 统计K线缓存
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(size_bytes) as total_size,
                        AVG(quality_score) as avg_quality,
                        COUNT(CASE WHEN expire_time > ? THEN 1 END) as active_entries
                    FROM kline_cache
                """, (int(time.time()),))
                
                kline_stats = cursor.fetchone()
                
                # 统计实时数据
                cursor = conn.execute("SELECT COUNT(*) as count FROM realtime_cache")
                realtime_count = cursor.fetchone()['count']
                
                return {
                    'sqlite_kline_entries': kline_stats['total_entries'] or 0,
                    'sqlite_active_entries': kline_stats['active_entries'] or 0,
                    'sqlite_realtime_entries': realtime_count,
                    'sqlite_total_size_bytes': kline_stats['total_size'] or 0,
                    'sqlite_avg_quality': kline_stats['avg_quality'] or 0.0
                }
                
        except Exception as e:
            logger.error(f"获取SQLite统计失败: {e}")
            return {}
    
    def clear_all_data(self) -> bool:
        """清空所有缓存数据"""
        try:
            conn = self._get_connection()
            
            with self.lock:
                conn.execute("DELETE FROM kline_cache")
                conn.execute("DELETE FROM realtime_cache")
                conn.execute("DELETE FROM cache_stats")
                conn.commit()
            
            logger.info("SQLite缓存已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空SQLite缓存失败: {e}")
            return False


class DataCacheManager:
    """数据缓存管理器 - 双层缓存架构"""
    
    def __init__(self, db_path: str = "tradingview_cache.db", max_memory_size: int = 1000):
        """初始化缓存管理器"""
        self.db_path = db_path
        self.max_memory_size = max_memory_size
        
        # 初始化双层缓存
        self.memory_cache = LRUCache(max_memory_size)
        self.sqlite_cache = SQLiteCacheManager(db_path)
        
        # 缓存统计
        self.total_requests = 0
        self.memory_hits = 0
        self.sqlite_hits = 0
        self.cache_misses = 0
        self.eviction_count = 0
        
        # 状态管理
        self.status = CacheStatus.ACTIVE
        self.last_cleanup_time = int(time.time())
        
        # 启动后台清理任务
        self._start_cleanup_task()
        
        logger.info(f"数据缓存管理器初始化完成: {db_path}")
    
    def _generate_cache_key(self, symbol: str, timeframe: str, **kwargs) -> str:
        """生成缓存键"""
        # 标准化参数
        params = {
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            **kwargs
        }
        
        # 生成稳定的哈希值
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode('utf-8')).hexdigest()
    
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                count: int = 500, **kwargs) -> Optional[Dict[str, Any]]:
        """获取历史数据"""
        cache_key = self._generate_cache_key(symbol, timeframe, count=count, **kwargs)
        self.total_requests += 1
        
        # L1: 内存缓存
        entry = self.memory_cache.get(cache_key)
        if entry and entry.expire_time > int(time.time()):
            self.memory_hits += 1
            logger.debug(f"内存缓存命中: {cache_key}")
            return entry.data
        
        # L2: SQLite缓存
        entry = self.sqlite_cache.get_kline_data(cache_key)
        if entry and entry.expire_time > int(time.time()):
            self.sqlite_hits += 1
            # 提升到内存缓存
            await self.memory_cache.put(cache_key, entry)
            logger.debug(f"SQLite缓存命中: {cache_key}")
            return entry.data
        
        # 缓存未命中
        self.cache_misses += 1
        logger.debug(f"缓存未命中: {cache_key}")
        return None
    
    async def store_historical_data(self, symbol: str, timeframe: str, 
                                  data: Dict[str, Any], expire_seconds: int = 3600) -> bool:
        """存储历史数据"""
        cache_key = self._generate_cache_key(
            symbol, timeframe, 
            count=len(data.get('klines', []))
        )
        
        quality_score = data.get('quality_score', 1.0)
        current_time = int(time.time())
        
        # 创建缓存条目
        data_json = json.dumps(data, ensure_ascii=False)
        size_bytes = len(data_json.encode('utf-8'))
        
        entry = CacheEntry(
            key=cache_key,
            data=data,
            timestamp=current_time,
            access_count=0,
            quality_score=quality_score,
            expire_time=current_time + expire_seconds,
            size_bytes=size_bytes
        )
        
        # 存储到双层缓存
        success = True
        
        # 存储到内存缓存
        await self.memory_cache.put(cache_key, entry)
        
        # 存储到SQLite缓存
        sqlite_success = self.sqlite_cache.store_kline_data(
            cache_key, symbol, timeframe, data, quality_score, expire_seconds
        )
        
        if not sqlite_success:
            logger.warning(f"SQLite存储失败，仅保存在内存: {cache_key}")
            success = False
        
        logger.debug(f"缓存存储完成: {cache_key}")
        return success
    
    async def get_cached_symbols(self) -> List[str]:
        """获取已缓存的品种列表"""
        try:
            conn = self.sqlite_cache._get_connection()
            
            cursor = conn.execute("""
                SELECT DISTINCT symbol FROM kline_cache 
                WHERE expire_time > ?
                ORDER BY symbol
            """, (int(time.time()),))
            
            symbols = [row['symbol'] for row in cursor.fetchall()]
            return symbols
            
        except Exception as e:
            logger.error(f"获取缓存品种列表失败: {e}")
            return []
    
    def get_hit_rate(self) -> float:
        """获取总体缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        
        total_hits = self.memory_hits + self.sqlite_hits
        return total_hits / self.total_requests
    
    def get_status(self) -> CacheStatus:
        """获取缓存状态"""
        return self.status
    
    async def get_statistics(self) -> CacheStatistics:
        """获取缓存统计信息"""
        memory_stats = {
            'memory_entries': self.memory_cache.get_size(),
            'memory_hit_rate': self.memory_cache.get_hit_rate()
        }
        
        sqlite_stats = self.sqlite_cache.get_statistics()
        
        # 计算总体统计
        total_entries = memory_stats['memory_entries'] + sqlite_stats.get('sqlite_active_entries', 0)
        total_size_mb = sqlite_stats.get('sqlite_total_size_bytes', 0) / (1024 * 1024)
        hit_rate = self.get_hit_rate()
        miss_rate = 1.0 - hit_rate if hit_rate > 0 else 0.0
        
        return CacheStatistics(
            total_entries=total_entries,
            memory_entries=memory_stats['memory_entries'],
            sqlite_entries=sqlite_stats.get('sqlite_active_entries', 0),
            total_size_mb=total_size_mb,
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            eviction_count=self.eviction_count,
            last_cleanup_time=self.last_cleanup_time
        )
    
    async def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        try:
            # 清空内存缓存
            self.memory_cache.clear()
            
            # 清空SQLite缓存
            sqlite_success = self.sqlite_cache.clear_all_data()
            
            # 重置统计
            self.total_requests = 0
            self.memory_hits = 0
            self.sqlite_hits = 0
            self.cache_misses = 0
            self.eviction_count = 0
            
            logger.info("所有缓存已清空")
            return sqlite_success
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def _start_cleanup_task(self):
        """启动后台清理任务"""
        def cleanup_worker():
            while self.status == CacheStatus.ACTIVE:
                try:
                    # 清理过期的SQLite数据
                    deleted_count = self.sqlite_cache.cleanup_expired_data()
                    if deleted_count > 0:
                        self.eviction_count += deleted_count
                    
                    self.last_cleanup_time = int(time.time())
                    
                    # 每5分钟清理一次
                    time.sleep(300)
                    
                except Exception as e:
                    logger.error(f"后台清理任务失败: {e}")
                    time.sleep(60)  # 出错后等待1分钟再试
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("后台清理任务已启动")


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    # 初始化缓存管理器
    cache_manager = DataCacheManager(
        db_path="example_cache.db",
        max_memory_size=500
    )
    
    # 存储数据
    sample_data = {
        'symbol': 'BINANCE:BTCUSDT',
        'timeframe': '15',
        'klines': [
            {
                'timestamp': 1699123456,
                'open': 35000.0,
                'high': 35500.0,
                'low': 34800.0,
                'close': 35200.0,
                'volume': 123.45
            }
        ],
        'quality_score': 0.95
    }
    
    await cache_manager.store_historical_data(
        'BINANCE:BTCUSDT', '15', sample_data
    )
    
    # 获取数据
    cached_data = await cache_manager.get_historical_data(
        'BINANCE:BTCUSDT', '15', count=500
    )
    
    if cached_data:
        print(f"缓存命中: {cached_data['symbol']}")
    else:
        print("缓存未命中")
    
    # 获取统计信息
    stats = await cache_manager.get_statistics()
    print(f"缓存统计: {asdict(stats)}")


if __name__ == "__main__":
    asyncio.run(example_usage())