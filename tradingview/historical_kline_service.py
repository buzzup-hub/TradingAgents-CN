#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView 历史K线数据服务 - 专业级数据获取引擎
"""

import asyncio
import time
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import statistics

# 导入tradingview核心模块
from tradingview.client import Client
from tradingview.enhanced_client import EnhancedTradingViewClient

# 日志配置
from config.logging_config import get_logger
logger = get_logger(__name__)

# 核心数据结构定义
class KlineQualityLevel(Enum):
    """K线数据质量等级"""
    DEVELOPMENT = "development"      # ≥90%
    PRODUCTION = "production"        # ≥95%
    FINANCIAL = "financial"          # ≥98%

class DataFetchStatus(Enum):
    """数据获取状态"""
    PENDING = "pending"
    FETCHING = "fetching"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class KlineDataRequest:
    """K线数据请求"""
    symbol: str
    timeframe: str
    count: int = 500
    quality_level: KlineQualityLevel = KlineQualityLevel.PRODUCTION
    request_id: str = field(default_factory=lambda: f"req_{int(time.time()*1000)}")
    created_time: datetime = field(default_factory=datetime.now)
    timeout: int = 30
    retry_count: int = 3
    cache_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KlineData:
    """标准化K线数据"""
    timestamp: int
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> Tuple[bool, List[str]]:
        """验证K线数据"""
        errors = []
        if self.high < max(self.open, self.close):
            errors.append(f"最高价({self.high})小于开盘价({self.open})或收盘价({self.close})")
        if self.low > min(self.open, self.close):
            errors.append(f"最低价({self.low})大于开盘价({self.open})或收盘价({self.close})")
        if any(v < 0 for v in [self.open, self.high, self.low, self.close]):
            errors.append("存在负数价格")
        if self.volume < 0:
            errors.append("成交量为负数")
        if self.timestamp <= 0:
            errors.append("时间戳无效")
        return len(errors) == 0, errors

@dataclass
class KlineDataResponse:
    """K线数据响应"""
    request_id: str
    symbol: str
    timeframe: str
    status: DataFetchStatus
    klines: List[KlineData] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    error_message: Optional[str] = None
    fetch_time: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "status": self.status.value,
            "klines": [k.to_dict() for k in self.klines],
            "metadata": self.metadata,
            "quality_score": self.quality_score,
            "error_message": self.error_message,
            "fetch_time": self.fetch_time.isoformat(),
            "response_time_ms": self.response_time_ms
        }

@dataclass
class QualityMetrics:
    """数据质量指标"""
    completeness_rate: float = 0.0
    accuracy_rate: float = 0.0
    consistency_rate: float = 0.0
    overall_quality: float = 0.0
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    issues: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class KlineDataValidator:
    """K线数据质量验证器"""
    
    def __init__(self, quality_level: KlineQualityLevel = KlineQualityLevel.PRODUCTION):
        self.quality_level = quality_level
        self.quality_thresholds = {
            KlineQualityLevel.DEVELOPMENT: 0.90,
            KlineQualityLevel.PRODUCTION: 0.95,
            KlineQualityLevel.FINANCIAL: 0.98
        }

    def validate_klines(self, klines: List[KlineData]) -> QualityMetrics:
        """验证K线数据质量"""
        metrics = QualityMetrics()
        metrics.total_records = len(klines)

        if not klines:
            metrics.overall_quality = 0.0
            metrics.issues.append("没有数据")
            return metrics

        # 验证每条K线
        valid_count = 0
        for kline in klines:
            is_valid, errors = kline.validate()
            if is_valid:
                valid_count += 1
            else:
                metrics.issues.extend(errors)

        metrics.valid_records = valid_count
        metrics.invalid_records = len(klines) - valid_count
        metrics.completeness_rate = valid_count / len(klines)
        metrics.accuracy_rate = 1.0 - (len(self._check_accuracy(klines)) / len(klines)) if klines else 0.0
        metrics.consistency_rate = 1.0 - (len(self._check_consistency(klines)) / len(klines)) if klines else 0.0
        
        metrics.overall_quality = (
            metrics.completeness_rate * 0.4 +
            metrics.accuracy_rate * 0.4 +
            metrics.consistency_rate * 0.2
        )

        return metrics

    def _check_accuracy(self, klines: List[KlineData]) -> List[str]:
        """检查准确性"""
        issues = []
        for i, kline in enumerate(klines):
            if kline.high / kline.low > 10:
                issues.append(f"索引{i}: 价格波动异常")
            if i > 0 and kline.volume > klines[i-1].volume * 100:
                issues.append(f"索引{i}: 成交量异常")
        return issues

    def _check_consistency(self, klines: List[KlineData]) -> List[str]:
        """检查一致性"""
        issues = []
        timestamps = [k.timestamp for k in klines]
        if timestamps != sorted(timestamps):
            issues.append("时间序列不是升序")
        return issues

    def meets_quality_threshold(self, metrics: QualityMetrics) -> bool:
        """检查是否满足质量阈值"""
        threshold = self.quality_thresholds[self.quality_level]
        return metrics.overall_quality >= threshold

class HistoricalKlineService:
    """历史K线数据服务"""

    def __init__(self, use_enhanced_client: bool = True, cache_dir: Optional[str] = None, db_path: Optional[str] = None):
        self.use_enhanced_client = use_enhanced_client
        self.client = None
        self.validator = KlineDataValidator()
        
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".tradingview" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path or str(self.cache_dir / "kline_cache.db")
        self._init_database()
        
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_response_time": 0.0,
            "response_times": []
        }
        
        self.max_concurrent_requests = 10
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        self.is_initialized = False
        
        logger.info(f"历史K线数据服务初始化 (增强客户端: {use_enhanced_client})")

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kline_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quality_score REAL,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp
            ON kline_cache(symbol, timeframe, timestamp)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成: {self.db_path}")

    async def initialize(self):
        """初始化服务"""
        if self.is_initialized:
            return

        try:
            if self.use_enhanced_client:
                self.client = EnhancedTradingViewClient()
            else:
                self.client = Client()
            
            await self.client.connect()
            self.is_initialized = True
            logger.info("历史K线数据服务初始化成功")
        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise

    async def fetch_klines(self, request: KlineDataRequest) -> KlineDataResponse:
        """获取K线数据"""
        start_time = time.time()
        self.stats["total_requests"] += 1

        response = KlineDataResponse(
            request_id=request.request_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            status=DataFetchStatus.PENDING
        )

        try:
            # 检查缓存
            if request.cache_enabled:
                cached_klines = await self._get_from_cache(request)
                if cached_klines and len(cached_klines) >= request.count:
                    logger.info(f"缓存命中: {request.symbol}")
                    self.stats["cache_hits"] += 1
                    response.klines = cached_klines[:request.count]
                    response.status = DataFetchStatus.COMPLETED
                    response.metadata["source"] = "cache"
                    
                    metrics = self.validator.validate_klines(response.klines)
                    response.quality_score = metrics.overall_quality
                    response.metadata["quality_metrics"] = asdict(metrics)
                    response.response_time_ms = (time.time() - start_time) * 1000
                    self.stats["successful_requests"] += 1
                    return response

            self.stats["cache_misses"] += 1

            # 从TradingView获取
            response.status = DataFetchStatus.FETCHING
            raw_klines = await self._fetch_from_tradingview(request)

            if not raw_klines:
                response.status = DataFetchStatus.FAILED
                response.error_message = "未获取到数据"
                self.stats["failed_requests"] += 1
                return response

            # 转换格式
            response.klines = self._convert_to_standard_format(raw_klines)

            # 质量验证
            metrics = self.validator.validate_klines(response.klines)
            response.quality_score = metrics.overall_quality
            response.metadata["quality_metrics"] = asdict(metrics)

            if not self.validator.meets_quality_threshold(metrics):
                response.status = DataFetchStatus.PARTIAL
                response.error_message = f"数据质量未达标"
            else:
                response.status = DataFetchStatus.COMPLETED

            # 保存缓存
            if request.cache_enabled and response.klines:
                await self._save_to_cache(request, response.klines, metrics.overall_quality)

            response.response_time_ms = (time.time() - start_time) * 1000
            self.stats["successful_requests"] += 1
            self.stats["response_times"].append(response.response_time_ms)
            
            logger.info(f"获取成功: {request.symbol} {len(response.klines)}条")

        except Exception as e:
            response.status = DataFetchStatus.FAILED
            response.error_message = str(e)
            self.stats["failed_requests"] += 1
            logger.error(f"获取失败: {e}")

        return response

    async def _fetch_from_tradingview(self, request: KlineDataRequest) -> List[Any]:
        """从TradingView获取数据"""
        async with self.request_semaphore:
            try:
                chart_session = self.client.Session.Chart()

                # 使用ChartSession的get_historical_data方法
                klines = await chart_session.get_historical_data(
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    count=request.count
                )

                logger.info(f"从TradingView获取到 {len(klines) if klines else 0} 条K线数据")
                return klines

            except Exception as e:
                logger.error(f"TradingView获取失败: {e}")
                raise

    def _convert_to_standard_format(self, raw_klines: List[Any]) -> List[KlineData]:
        """转换为标准格式"""
        standard_klines = []
        for raw in raw_klines:
            try:
                if hasattr(raw, 'time'):
                    kline = KlineData(
                        timestamp=int(raw.time),
                        datetime=datetime.fromtimestamp(raw.time).isoformat(),
                        open=float(raw.open),
                        high=float(raw.high),
                        low=float(raw.low),
                        close=float(raw.close),
                        volume=float(getattr(raw, 'volume', 0))
                    )
                elif isinstance(raw, dict):
                    kline = KlineData(
                        timestamp=int(raw['time']),
                        datetime=datetime.fromtimestamp(raw['time']).isoformat(),
                        open=float(raw['open']),
                        high=float(raw['high']),
                        low=float(raw['low']),
                        close=float(raw['close']),
                        volume=float(raw.get('volume', 0))
                    )
                else:
                    continue
                standard_klines.append(kline)
            except Exception as e:
                logger.error(f"转换失败: {e}")
                continue
        return standard_klines

    async def _get_from_cache(self, request: KlineDataRequest) -> Optional[List[KlineData]]:
        """从缓存获取"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, datetime, open, high, low, close, volume
                FROM kline_cache
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (request.symbol, request.timeframe, request.count))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None
            
            return [KlineData(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in rows]
        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            return None

    async def _save_to_cache(self, request: KlineDataRequest, klines: List[KlineData], quality_score: float):
        """保存到缓存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for kline in klines:
                cursor.execute("""
                    INSERT OR REPLACE INTO kline_cache
                    (symbol, timeframe, timestamp, datetime, open, high, low, close, volume, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (request.symbol, request.timeframe, kline.timestamp, kline.datetime, 
                     kline.open, kline.high, kline.low, kline.close, kline.volume, quality_score))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")

    async def batch_fetch_klines(self, requests: List[KlineDataRequest]) -> List[KlineDataResponse]:
        """批量获取"""
        tasks = [self.fetch_klines(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append(KlineDataResponse(
                    request_id=requests[i].request_id,
                    symbol=requests[i].symbol,
                    timeframe=requests[i].timeframe,
                    status=DataFetchStatus.FAILED,
                    error_message=str(response)
                ))
            else:
                results.append(response)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        stats = self.stats.copy()
        if stats["response_times"]:
            stats["avg_response_time_ms"] = statistics.mean(stats["response_times"])
            if len(stats["response_times"]) >= 20:
                stats["p95_response_time_ms"] = statistics.quantiles(stats["response_times"], n=20)[18]
            if len(stats["response_times"]) >= 100:
                stats["p99_response_time_ms"] = statistics.quantiles(stats["response_times"], n=100)[98]
        
        stats["success_rate"] = stats["successful_requests"] / stats["total_requests"] if stats["total_requests"] > 0 else 0.0
        stats["cache_hit_rate"] = stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"]) if (stats["cache_hits"] + stats["cache_misses"]) > 0 else 0.0
        return stats

    async def close(self):
        """关闭服务"""
        if self.client:
            await self.client.end()
        logger.info("服务已关闭")
