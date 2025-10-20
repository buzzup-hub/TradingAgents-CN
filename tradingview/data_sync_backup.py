#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView数据同步和备份策略实现
提供多层次的数据同步、备份和恢复机制
"""

import asyncio
import time
import json
import hashlib
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import threading
import schedule
from concurrent.futures import ThreadPoolExecutor

from config.logging_config import get_logger

logger = get_logger(__name__)


class SyncStatus(Enum):
    """同步状态枚举"""
    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class BackupType(Enum):
    """备份类型枚举"""
    FULL = "full"           # 全量备份
    INCREMENTAL = "incremental"  # 增量备份
    DIFFERENTIAL = "differential"  # 差异备份
    SNAPSHOT = "snapshot"   # 快照备份


@dataclass
class SyncTask:
    """同步任务"""
    task_id: str
    source_type: str  # "primary", "secondary", "cache"
    target_type: str  # "cache", "backup", "remote"
    symbols: List[str]
    timeframes: List[str]
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    priority: int = 1  # 1-10, 数字越小优先级越高
    retry_count: int = 0
    max_retries: int = 3
    created_at: int = 0
    updated_at: int = 0
    status: SyncStatus = SyncStatus.IDLE


@dataclass
class BackupRecord:
    """备份记录"""
    backup_id: str
    backup_type: BackupType
    file_path: str
    size_bytes: int
    checksum: str
    created_at: int
    symbols_count: int
    data_range_start: int
    data_range_end: int
    metadata: Dict[str, Any]


class DataSyncEngine:
    """数据同步引擎"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化同步引擎"""
        self.config = config or {}
        
        # 同步配置
        self.sync_interval = self.config.get('sync_interval', 300)  # 5分钟
        self.batch_size = self.config.get('batch_size', 100)
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 5)
        
        # 任务管理
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        
        # 状态管理
        self.is_running = False
        self.last_sync_time = 0
        self.sync_statistics = {
            'total_synced': 0,
            'total_failed': 0,
            'last_error': None,
            'sync_speed': 0.0  # records/second
        }
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_tasks)
        
        logger.info("数据同步引擎初始化完成")
    
    async def start_sync_engine(self):
        """启动同步引擎"""
        if self.is_running:
            logger.warning("同步引擎已在运行")
            return
        
        self.is_running = True
        logger.info("启动数据同步引擎")
        
        # 启动同步工作线程
        asyncio.create_task(self._sync_worker())
        asyncio.create_task(self._sync_scheduler())
        
    async def stop_sync_engine(self):
        """停止同步引擎"""
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("数据同步引擎已停止")
    
    async def add_sync_task(self, task: SyncTask) -> str:
        """添加同步任务"""
        task.task_id = f"sync_{int(time.time())}_{hash(task.source_type + task.target_type)}"
        task.created_at = int(time.time())
        task.updated_at = task.created_at
        
        await self.task_queue.put(task)
        logger.info(f"添加同步任务: {task.task_id}")
        
        return task.task_id
    
    async def _sync_worker(self):
        """同步工作线程"""
        while self.is_running:
            try:
                # 获取任务
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # 执行同步任务
                await self._execute_sync_task(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"同步工作线程错误: {e}")
                await asyncio.sleep(1)
    
    async def _sync_scheduler(self):
        """同步调度器"""
        while self.is_running:
            try:
                current_time = int(time.time())
                
                # 检查是否需要定期同步
                if current_time - self.last_sync_time >= self.sync_interval:
                    await self._schedule_periodic_sync()
                    self.last_sync_time = current_time
                
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"同步调度器错误: {e}")
                await asyncio.sleep(60)
    
    async def _schedule_periodic_sync(self):
        """调度定期同步任务"""
        # 主数据源到缓存的同步
        cache_sync_task = SyncTask(
            task_id="",
            source_type="primary",
            target_type="cache",
            symbols=["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"],  # 热门品种
            timeframes=["1", "5", "15", "60"],
            priority=1
        )
        
        await self.add_sync_task(cache_sync_task)
        
        # 缓存到备份的同步
        backup_sync_task = SyncTask(
            task_id="",
            source_type="cache",
            target_type="backup",
            symbols=["*"],  # 全部品种
            timeframes=["*"],  # 全部时间框架
            priority=2
        )
        
        await self.add_sync_task(backup_sync_task)
    
    async def _execute_sync_task(self, task: SyncTask):
        """执行同步任务"""
        task.status = SyncStatus.SYNCING
        task.updated_at = int(time.time())
        self.active_tasks[task.task_id] = task
        
        try:
            start_time = time.time()
            
            # 根据任务类型执行不同的同步逻辑
            if task.source_type == "primary" and task.target_type == "cache":
                result = await self._sync_primary_to_cache(task)
            elif task.source_type == "cache" and task.target_type == "backup":
                result = await self._sync_cache_to_backup(task)
            elif task.source_type == "backup" and task.target_type == "cache":
                result = await self._sync_backup_to_cache(task)
            else:
                raise ValueError(f"不支持的同步类型: {task.source_type} -> {task.target_type}")
            
            # 更新统计信息
            sync_time = time.time() - start_time
            self.sync_statistics['total_synced'] += result.get('synced_count', 0)
            self.sync_statistics['sync_speed'] = result.get('synced_count', 0) / sync_time
            
            task.status = SyncStatus.SUCCESS
            self.completed_tasks[task.task_id] = task
            
            logger.info(f"同步任务完成: {task.task_id}, 耗时: {sync_time:.2f}秒")
            
        except Exception as e:
            task.status = SyncStatus.FAILED
            task.retry_count += 1
            
            self.sync_statistics['total_failed'] += 1
            self.sync_statistics['last_error'] = str(e)
            
            logger.error(f"同步任务失败: {task.task_id}, 错误: {e}")
            
            # 重试机制
            if task.retry_count < task.max_retries:
                await asyncio.sleep(2 ** task.retry_count)  # 指数退避
                await self.task_queue.put(task)
            else:
                self.failed_tasks[task.task_id] = task
        
        finally:
            self.active_tasks.pop(task.task_id, None)
    
    async def _sync_primary_to_cache(self, task: SyncTask) -> Dict[str, Any]:
        """从主数据源同步到缓存"""
        synced_count = 0
        
        for symbol in task.symbols:
            for timeframe in task.timeframes:
                try:
                    # 模拟从主数据源获取数据
                    # 在实际实现中，这里会调用TradingView客户端
                    data = await self._fetch_from_primary_source(symbol, timeframe)
                    
                    if data:
                        # 存储到缓存
                        await self._store_to_cache(symbol, timeframe, data)
                        synced_count += len(data.get('klines', []))
                        
                except Exception as e:
                    logger.error(f"同步 {symbol}:{timeframe} 失败: {e}")
        
        return {'synced_count': synced_count}
    
    async def _sync_cache_to_backup(self, task: SyncTask) -> Dict[str, Any]:
        """从缓存同步到备份"""
        synced_count = 0
        
        # 获取缓存中的所有数据
        cached_data = await self._get_all_cached_data(task.symbols, task.timeframes)
        
        for data_item in cached_data:
            try:
                # 存储到备份
                await self._store_to_backup(data_item)
                synced_count += 1
                
            except Exception as e:
                logger.error(f"备份数据失败: {e}")
        
        return {'synced_count': synced_count}
    
    async def _sync_backup_to_cache(self, task: SyncTask) -> Dict[str, Any]:
        """从备份恢复到缓存"""
        restored_count = 0
        
        # 获取备份数据
        backup_data = await self._get_backup_data(task.symbols, task.timeframes)
        
        for data_item in backup_data:
            try:
                # 恢复到缓存
                await self._restore_to_cache(data_item)
                restored_count += 1
                
            except Exception as e:
                logger.error(f"恢复数据失败: {e}")
        
        return {'synced_count': restored_count}
    
    async def _fetch_from_primary_source(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """从主数据源获取数据"""
        # 这里是模拟实现，实际中会调用TradingView客户端
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'klines': [
                {
                    'timestamp': int(time.time()) - i * 60,
                    'open': 35000.0 + i,
                    'high': 35100.0 + i,
                    'low': 34900.0 + i,
                    'close': 35050.0 + i,
                    'volume': 100.0 + i
                }
                for i in range(10)
            ],
            'quality_score': 0.95,
            'sync_timestamp': int(time.time())
        }
    
    async def _store_to_cache(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """存储数据到缓存"""
        # 模拟存储逻辑
        logger.debug(f"存储到缓存: {symbol}:{timeframe}, {len(data.get('klines', []))} 条记录")
        await asyncio.sleep(0.01)
    
    async def _get_all_cached_data(self, symbols: List[str], timeframes: List[str]) -> List[Dict[str, Any]]:
        """获取所有缓存数据"""
        # 模拟获取缓存数据
        data = []
        for symbol in symbols[:5]:  # 限制数量用于演示
            for timeframe in timeframes[:2]:
                data.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'data': f"cached_data_{symbol}_{timeframe}",
                    'timestamp': int(time.time())
                })
        
        return data
    
    async def _store_to_backup(self, data_item: Dict[str, Any]):
        """存储数据到备份"""
        logger.debug(f"存储到备份: {data_item.get('symbol')}:{data_item.get('timeframe')}")
        await asyncio.sleep(0.01)
    
    async def _get_backup_data(self, symbols: List[str], timeframes: List[str]) -> List[Dict[str, Any]]:
        """获取备份数据"""
        # 模拟获取备份数据
        return [
            {
                'symbol': symbol,
                'timeframe': timeframe,
                'data': f"backup_data_{symbol}_{timeframe}",
                'timestamp': int(time.time())
            }
            for symbol in symbols[:3]
            for timeframe in timeframes[:2]
        ]
    
    async def _restore_to_cache(self, data_item: Dict[str, Any]):
        """恢复数据到缓存"""
        logger.debug(f"恢复到缓存: {data_item.get('symbol')}:{data_item.get('timeframe')}")
        await asyncio.sleep(0.01)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'is_running': self.is_running,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'queue_size': self.task_queue.qsize(),
            'last_sync_time': self.last_sync_time,
            'statistics': self.sync_statistics.copy()
        }


class DataBackupManager:
    """数据备份管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化备份管理器"""
        self.config = config or {}
        
        # 备份配置
        self.backup_dir = Path(self.config.get('backup_dir', 'data/backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_backup_files = self.config.get('max_backup_files', 30)
        self.compression_enabled = self.config.get('compression_enabled', True)
        
        # 备份记录
        self.backup_records = {}
        self.backup_index_file = self.backup_dir / 'backup_index.json'
        
        # 加载现有备份记录
        self._load_backup_index()
        
        logger.info(f"数据备份管理器初始化完成，备份目录: {self.backup_dir}")
    
    def _load_backup_index(self):
        """加载备份索引"""
        if self.backup_index_file.exists():
            try:
                with open(self.backup_index_file, 'r') as f:
                    index_data = json.load(f)
                    
                for record_data in index_data.get('records', []):
                    record = BackupRecord(**record_data)
                    self.backup_records[record.backup_id] = record
                    
                logger.info(f"加载了 {len(self.backup_records)} 条备份记录")
                
            except Exception as e:
                logger.error(f"加载备份索引失败: {e}")
    
    def _save_backup_index(self):
        """保存备份索引"""
        try:
            index_data = {
                'version': '1.0',
                'created_at': int(time.time()),
                'records': [asdict(record) for record in self.backup_records.values()]
            }
            
            with open(self.backup_index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"保存备份索引失败: {e}")
    
    async def create_backup(self, backup_type: BackupType, 
                          symbols: List[str] = None, 
                          timeframes: List[str] = None) -> Optional[str]:
        """创建备份"""
        backup_id = f"backup_{backup_type.value}_{int(time.time())}"
        
        try:
            # 生成备份文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"{backup_id}_{timestamp}.db"
            
            # 执行备份
            symbols_count, data_range = await self._execute_backup(
                backup_type, backup_file, symbols, timeframes
            )
            
            # 计算文件大小和校验和
            file_size = backup_file.stat().st_size
            checksum = await self._calculate_checksum(backup_file)
            
            # 创建备份记录
            backup_record = BackupRecord(
                backup_id=backup_id,
                backup_type=backup_type,
                file_path=str(backup_file),
                size_bytes=file_size,
                checksum=checksum,
                created_at=int(time.time()),
                symbols_count=symbols_count,
                data_range_start=data_range[0],
                data_range_end=data_range[1],
                metadata={
                    'symbols': symbols or [],
                    'timeframes': timeframes or [],
                    'compression': self.compression_enabled
                }
            )
            
            self.backup_records[backup_id] = backup_record
            self._save_backup_index()
            
            # 清理旧备份
            await self._cleanup_old_backups()
            
            logger.info(f"备份创建成功: {backup_id}, 大小: {file_size / 1024 / 1024:.2f}MB")
            return backup_id
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return None
    
    async def _execute_backup(self, backup_type: BackupType, backup_file: Path,
                            symbols: List[str], timeframes: List[str]) -> Tuple[int, Tuple[int, int]]:
        """执行备份操作"""
        # 创建备份数据库
        conn = sqlite3.connect(str(backup_file))
        
        try:
            # 创建备份表结构
            await self._create_backup_tables(conn)
            
            symbols_count = 0
            min_timestamp = int(time.time())
            max_timestamp = 0
            
            if backup_type == BackupType.FULL:
                # 全量备份
                symbols_count, (min_timestamp, max_timestamp) = await self._full_backup(
                    conn, symbols, timeframes
                )
            elif backup_type == BackupType.INCREMENTAL:
                # 增量备份
                symbols_count, (min_timestamp, max_timestamp) = await self._incremental_backup(
                    conn, symbols, timeframes
                )
            elif backup_type == BackupType.SNAPSHOT:
                # 快照备份
                symbols_count, (min_timestamp, max_timestamp) = await self._snapshot_backup(
                    conn, symbols, timeframes
                )
            
            conn.commit()
            
            return symbols_count, (min_timestamp, max_timestamp)
            
        finally:
            conn.close()
    
    async def _create_backup_tables(self, conn: sqlite3.Connection):
        """创建备份表结构"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backup_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kline_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quality_score REAL DEFAULT 1.0,
                backup_timestamp INTEGER NOT NULL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_kline_symbol_timeframe 
            ON kline_data(symbol, timeframe)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_kline_timestamp 
            ON kline_data(timestamp)
        """)
    
    async def _full_backup(self, conn: sqlite3.Connection, 
                          symbols: List[str], timeframes: List[str]) -> Tuple[int, Tuple[int, int]]:
        """执行全量备份"""
        # 模拟全量备份
        symbols_count = 0
        min_timestamp = int(time.time())
        max_timestamp = 0
        
        # 保存备份元数据
        conn.execute("""
            INSERT OR REPLACE INTO backup_metadata (key, value, created_at)
            VALUES (?, ?, ?)
        """, ('backup_type', 'full', int(time.time())))
        
        # 模拟备份数据
        for symbol in (symbols or ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'])[:10]:
            for timeframe in (timeframes or ['15', '60'])[:5]:
                for i in range(1000):  # 每个品种备份1000条记录
                    timestamp = int(time.time()) - i * 900  # 15分钟间隔
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO kline_data 
                        (symbol, timeframe, timestamp, open, high, low, close, volume, backup_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, timeframe, timestamp,
                        35000.0 + i, 35100.0 + i, 34900.0 + i, 35050.0 + i, 100.0 + i,
                        int(time.time())
                    ))
                    
                    min_timestamp = min(min_timestamp, timestamp)
                    max_timestamp = max(max_timestamp, timestamp)
                
                symbols_count += 1
        
        return symbols_count, (min_timestamp, max_timestamp)
    
    async def _incremental_backup(self, conn: sqlite3.Connection,
                                symbols: List[str], timeframes: List[str]) -> Tuple[int, Tuple[int, int]]:
        """执行增量备份"""
        # 获取上次备份时间
        last_backup_time = self._get_last_backup_time()
        
        symbols_count = 0
        min_timestamp = int(time.time())
        max_timestamp = 0
        
        # 保存备份元数据
        conn.execute("""
            INSERT OR REPLACE INTO backup_metadata (key, value, created_at)
            VALUES (?, ?, ?)
        """, ('backup_type', 'incremental', int(time.time())))
        
        conn.execute("""
            INSERT OR REPLACE INTO backup_metadata (key, value, created_at)
            VALUES (?, ?, ?)
        """, ('last_backup_time', str(last_backup_time), int(time.time())))
        
        # 模拟增量备份（只备份新数据）
        for symbol in (symbols or ['BINANCE:BTCUSDT'])[:5]:
            for timeframe in (timeframes or ['15'])[:2]:
                for i in range(100):  # 增量备份较少数据
                    timestamp = int(time.time()) - i * 900
                    
                    if timestamp > last_backup_time:  # 只备份新数据
                        conn.execute("""
                            INSERT OR REPLACE INTO kline_data 
                            (symbol, timeframe, timestamp, open, high, low, close, volume, backup_timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            symbol, timeframe, timestamp,
                            35000.0 + i, 35100.0 + i, 34900.0 + i, 35050.0 + i, 100.0 + i,
                            int(time.time())
                        ))
                        
                        min_timestamp = min(min_timestamp, timestamp)
                        max_timestamp = max(max_timestamp, timestamp)
                
                symbols_count += 1
        
        return symbols_count, (min_timestamp, max_timestamp)
    
    async def _snapshot_backup(self, conn: sqlite3.Connection,
                             symbols: List[str], timeframes: List[str]) -> Tuple[int, Tuple[int, int]]:
        """执行快照备份"""
        # 快照备份当前时刻的数据状态
        current_time = int(time.time())
        symbols_count = 0
        
        # 保存备份元数据
        conn.execute("""
            INSERT OR REPLACE INTO backup_metadata (key, value, created_at)
            VALUES (?, ?, ?)
        """, ('backup_type', 'snapshot', current_time))
        
        conn.execute("""
            INSERT OR REPLACE INTO backup_metadata (key, value, created_at)
            VALUES (?, ?, ?)
        """, ('snapshot_time', str(current_time), current_time))
        
        # 模拟快照数据
        for symbol in (symbols or ['BINANCE:BTCUSDT'])[:3]:
            for timeframe in (timeframes or ['15'])[:1]:
                # 快照只备份最新的数据点
                conn.execute("""
                    INSERT OR REPLACE INTO kline_data 
                    (symbol, timeframe, timestamp, open, high, low, close, volume, backup_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, timeframe, current_time,
                    35000.0, 35100.0, 34900.0, 35050.0, 100.0,
                    current_time
                ))
                
                symbols_count += 1
        
        return symbols_count, (current_time, current_time)
    
    def _get_last_backup_time(self) -> int:
        """获取上次备份时间"""
        if not self.backup_records:
            return int(time.time()) - 86400  # 默认24小时前
        
        # 找到最新的备份记录
        latest_backup = max(self.backup_records.values(), key=lambda x: x.created_at)
        return latest_backup.created_at
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    async def _cleanup_old_backups(self):
        """清理旧备份文件"""
        if len(self.backup_records) > self.max_backup_files:
            # 按创建时间排序
            sorted_records = sorted(
                self.backup_records.values(),
                key=lambda x: x.created_at
            )
            
            # 删除最旧的备份
            records_to_delete = sorted_records[:-self.max_backup_files]
            
            for record in records_to_delete:
                try:
                    file_path = Path(record.file_path)
                    if file_path.exists():
                        file_path.unlink()
                    
                    del self.backup_records[record.backup_id]
                    logger.info(f"删除旧备份: {record.backup_id}")
                    
                except Exception as e:
                    logger.error(f"删除备份文件失败: {e}")
            
            self._save_backup_index()
    
    async def restore_backup(self, backup_id: str, target_db: str = None) -> bool:
        """恢复备份"""
        if backup_id not in self.backup_records:
            logger.error(f"备份记录不存在: {backup_id}")
            return False
        
        record = self.backup_records[backup_id]
        backup_file = Path(record.file_path)
        
        if not backup_file.exists():
            logger.error(f"备份文件不存在: {backup_file}")
            return False
        
        try:
            # 验证备份文件完整性
            current_checksum = await self._calculate_checksum(backup_file)
            if current_checksum != record.checksum:
                logger.error(f"备份文件校验失败: {backup_id}")
                return False
            
            # 执行恢复操作
            if target_db:
                await self._restore_to_database(backup_file, target_db)
            else:
                await self._restore_to_cache(backup_file)
            
            logger.info(f"备份恢复成功: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"备份恢复失败: {e}")
            return False
    
    async def _restore_to_database(self, backup_file: Path, target_db: str):
        """恢复到指定数据库"""
        # 简单的数据库文件复制
        shutil.copy2(backup_file, target_db)
        logger.info(f"备份文件已复制到: {target_db}")
    
    async def _restore_to_cache(self, backup_file: Path):
        """恢复到缓存系统"""
        conn = sqlite3.connect(str(backup_file))
        
        try:
            cursor = conn.execute("""
                SELECT symbol, timeframe, timestamp, open, high, low, close, volume, quality_score
                FROM kline_data
            """)
            
            restored_count = 0
            for row in cursor:
                # 模拟恢复到缓存
                # 实际实现中会调用缓存管理器的接口
                await asyncio.sleep(0.001)  # 模拟处理时间
                restored_count += 1
            
            logger.info(f"恢复了 {restored_count} 条记录到缓存")
            
        finally:
            conn.close()
    
    def get_backup_info(self, backup_id: str = None) -> Dict[str, Any]:
        """获取备份信息"""
        if backup_id:
            if backup_id in self.backup_records:
                return asdict(self.backup_records[backup_id])
            else:
                return {}
        else:
            return {
                'total_backups': len(self.backup_records),
                'backup_records': [asdict(record) for record in self.backup_records.values()],
                'backup_dir': str(self.backup_dir),
                'total_size_mb': sum(
                    record.size_bytes for record in self.backup_records.values()
                ) / 1024 / 1024
            }


class DataSyncBackupController:
    """数据同步备份控制器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化控制器"""
        self.config = config or {}
        
        # 初始化组件
        self.sync_engine = DataSyncEngine(self.config.get('sync_config', {}))
        self.backup_manager = DataBackupManager(self.config.get('backup_config', {}))
        
        # 调度配置
        self.schedule_enabled = self.config.get('schedule_enabled', True)
        self.backup_schedule = self.config.get('backup_schedule', {
            'full_backup': {'hour': 2, 'minute': 0},      # 每天凌晨2点全量备份
            'incremental_backup': {'minute': 30},          # 每30分钟增量备份
            'snapshot_backup': {'hour': [6, 12, 18]}       # 每天6、12、18点快照备份
        })
        
        logger.info("数据同步备份控制器初始化完成")
    
    async def start(self):
        """启动控制器"""
        # 启动同步引擎
        await self.sync_engine.start_sync_engine()
        
        # 启动定时任务
        if self.schedule_enabled:
            self._setup_scheduled_tasks()
            
        logger.info("数据同步备份控制器已启动")
    
    async def stop(self):
        """停止控制器"""
        await self.sync_engine.stop_sync_engine()
        logger.info("数据同步备份控制器已停止")
    
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        # 全量备份
        full_config = self.backup_schedule.get('full_backup', {})
        if full_config:
            schedule.every().day.at(f"{full_config.get('hour', 2):02d}:{full_config.get('minute', 0):02d}").do(
                self._scheduled_full_backup
            )
        
        # 增量备份
        inc_config = self.backup_schedule.get('incremental_backup', {})
        if inc_config:
            schedule.every(inc_config.get('minute', 30)).minutes.do(
                self._scheduled_incremental_backup
            )
        
        # 快照备份
        snapshot_config = self.backup_schedule.get('snapshot_backup', {})
        if snapshot_config and 'hour' in snapshot_config:
            hours = snapshot_config['hour']
            if isinstance(hours, int):
                hours = [hours]
            
            for hour in hours:
                schedule.every().day.at(f"{hour:02d}:00").do(
                    self._scheduled_snapshot_backup
                )
        
        # 启动调度线程
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("定时任务已设置")
    
    def _scheduled_full_backup(self):
        """定时全量备份"""
        asyncio.create_task(
            self.backup_manager.create_backup(BackupType.FULL)
        )
    
    def _scheduled_incremental_backup(self):
        """定时增量备份"""
        asyncio.create_task(
            self.backup_manager.create_backup(BackupType.INCREMENTAL)
        )
    
    def _scheduled_snapshot_backup(self):
        """定时快照备份"""
        asyncio.create_task(
            self.backup_manager.create_backup(BackupType.SNAPSHOT)
        )
    
    async def create_manual_backup(self, backup_type: BackupType,
                                 symbols: List[str] = None,
                                 timeframes: List[str] = None) -> Optional[str]:
        """手动创建备份"""
        return await self.backup_manager.create_backup(backup_type, symbols, timeframes)
    
    async def restore_from_backup(self, backup_id: str, target_db: str = None) -> bool:
        """从备份恢复"""
        return await self.backup_manager.restore_backup(backup_id, target_db)
    
    async def sync_data(self, source_type: str, target_type: str,
                       symbols: List[str], timeframes: List[str]) -> str:
        """手动同步数据"""
        task = SyncTask(
            task_id="",
            source_type=source_type,
            target_type=target_type,
            symbols=symbols,
            timeframes=timeframes,
            priority=1
        )
        
        return await self.sync_engine.add_sync_task(task)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        sync_status = self.sync_engine.get_sync_status()
        backup_info = self.backup_manager.get_backup_info()
        
        return {
            'sync_engine': sync_status,
            'backup_manager': backup_info,
            'schedule_enabled': self.schedule_enabled,
            'system_time': int(time.time())
        }


# ==================== 使用示例 ====================

async def example_sync_backup():
    """数据同步备份使用示例"""
    
    # 初始化控制器
    config = {
        'sync_config': {
            'sync_interval': 300,  # 5分钟同步间隔
            'batch_size': 100,
            'max_concurrent_tasks': 5
        },
        'backup_config': {
            'backup_dir': 'data/backups',
            'max_backup_files': 30,
            'compression_enabled': True
        },
        'schedule_enabled': True,
        'backup_schedule': {
            'full_backup': {'hour': 2, 'minute': 0},
            'incremental_backup': {'minute': 30},
            'snapshot_backup': {'hour': [6, 12, 18]}
        }
    }
    
    controller = DataSyncBackupController(config)
    
    try:
        # 启动系统
        await controller.start()
        
        # 手动创建全量备份
        print("创建全量备份...")
        backup_id = await controller.create_manual_backup(
            BackupType.FULL,
            symbols=['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'],
            timeframes=['15', '60']
        )
        
        if backup_id:
            print(f"全量备份创建成功: {backup_id}")
        
        # 手动同步数据
        print("执行数据同步...")
        task_id = await controller.sync_data(
            source_type="primary",
            target_type="cache",
            symbols=['BINANCE:BTCUSDT'],
            timeframes=['15']
        )
        
        print(f"同步任务已添加: {task_id}")
        
        # 等待一段时间让任务执行
        await asyncio.sleep(5)
        
        # 获取系统状态
        status = controller.get_system_status()
        print(f"系统状态: {json.dumps(status, indent=2)}")
        
        # 如果需要，从备份恢复
        if backup_id:
            print("测试备份恢复...")
            success = await controller.restore_from_backup(backup_id)
            print(f"备份恢复{'成功' if success else '失败'}")
        
        # 运行一段时间以观察定时任务
        print("系统运行中，观察定时任务...")
        await asyncio.sleep(30)
        
    finally:
        # 停止系统
        await controller.stop()


if __name__ == "__main__":
    asyncio.run(example_sync_backup())