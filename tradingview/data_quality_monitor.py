#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView数据质量监控系统
实现多维度数据质量评估、异常检测和质量报告
"""

import asyncio
import time
import statistics
import math
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto

from config.logging_config import get_logger

logger = get_logger(__name__)


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = auto()  # 优秀 (95-100%)
    GOOD = auto()       # 良好 (85-94%)
    FAIR = auto()       # 一般 (70-84%)
    POOR = auto()       # 较差 (50-69%)
    CRITICAL = auto()   # 危险 (0-49%)


class AnomalyType(Enum):
    """异常类型"""
    PRICE_SPIKE = auto()        # 价格异常跳跃
    VOLUME_ANOMALY = auto()     # 成交量异常
    TIME_GAP = auto()           # 时间间隔异常
    MISSING_DATA = auto()       # 数据缺失
    DUPLICATE_DATA = auto()     # 重复数据
    INVALID_OHLC = auto()       # 无效OHLC关系
    EXTREME_VALUE = auto()      # 极值异常
    PATTERN_BREAK = auto()      # 模式中断


@dataclass
class QualityMetrics:
    """质量指标"""
    symbol: str
    timeframe: str
    timestamp: float = field(default_factory=time.time)
    
    # 完整性指标
    completeness_score: float = 1.0        # 数据完整性分数
    missing_data_ratio: float = 0.0        # 缺失数据比例
    duplicate_data_ratio: float = 0.0      # 重复数据比例
    
    # 准确性指标
    accuracy_score: float = 1.0            # 数据准确性分数
    invalid_ohlc_ratio: float = 0.0        # 无效OHLC比例
    extreme_value_ratio: float = 0.0       # 极值比例
    
    # 一致性指标
    consistency_score: float = 1.0         # 数据一致性分数
    time_consistency_ratio: float = 1.0    # 时间一致性比例
    value_consistency_ratio: float = 1.0   # 数值一致性比例
    
    # 及时性指标
    timeliness_score: float = 1.0          # 数据及时性分数
    data_delay: float = 0.0                # 数据延迟(秒)
    update_frequency: float = 0.0          # 更新频率
    
    # 异常检测
    anomaly_count: int = 0                 # 异常数量
    anomaly_types: Dict[str, int] = field(default_factory=dict)
    anomaly_severity: float = 0.0          # 异常严重程度
    
    # 综合质量分数
    overall_quality_score: float = 1.0
    quality_level: QualityLevel = QualityLevel.EXCELLENT
    
    # 数据统计
    total_records: int = 0
    valid_records: int = 0
    processed_records: int = 0


@dataclass
class DataAnomaly:
    """数据异常"""
    anomaly_id: str
    anomaly_type: AnomalyType
    symbol: str
    timestamp: float
    severity: float                        # 严重程度 0.0-1.0
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


class DataValidator:
    """数据验证器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.validation_count = 0
        self.error_count = 0
        
    async def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证数据"""
        raise NotImplementedError
        
    def get_error_rate(self) -> float:
        """获取错误率"""
        if self.validation_count == 0:
            return 0.0
        return self.error_count / self.validation_count


class OHLCValidator(DataValidator):
    """OHLC数据验证器"""
    
    def __init__(self):
        super().__init__("OHLC验证器")
        
    async def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证OHLC数据"""
        self.validation_count += 1
        errors = []
        
        try:
            # 检查必需字段
            required_fields = ['open', 'high', 'low', 'close', 'time']
            for field in required_fields:
                if field not in data:
                    errors.append(f"缺少必需字段: {field}")
                    
            if errors:
                self.error_count += 1
                return False, errors
                
            # 获取OHLC值
            open_price = float(data['open'])
            high_price = float(data['high'])
            low_price = float(data['low'])
            close_price = float(data['close'])
            
            # 验证价格为正数
            prices = [open_price, high_price, low_price, close_price]
            if any(price <= 0 for price in prices):
                errors.append("价格值必须为正数")
                
            # 验证OHLC逻辑关系
            if high_price < max(open_price, close_price):
                errors.append(f"最高价 {high_price} 小于开盘价或收盘价的最大值")
                
            if low_price > min(open_price, close_price):
                errors.append(f"最低价 {low_price} 大于开盘价或收盘价的最小值")
                
            # 验证价格合理性 (不能相差过大)
            max_price = max(prices)
            min_price = min(prices)
            if max_price > 0 and (max_price - min_price) / min_price > 0.5:  # 50%变动
                errors.append("单个周期内价格变动过大")
                
            if errors:
                self.error_count += 1
                return False, errors
            else:
                return True, []
                
        except (ValueError, TypeError) as e:
            self.error_count += 1
            errors.append(f"数据类型错误: {e}")
            return False, errors
        except Exception as e:
            self.error_count += 1
            errors.append(f"验证异常: {e}")
            return False, errors


class VolumeValidator(DataValidator):
    """成交量验证器"""
    
    def __init__(self):
        super().__init__("成交量验证器")
        
    async def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证成交量数据"""
        self.validation_count += 1
        errors = []
        
        try:
            if 'volume' not in data:
                return True, []  # 成交量是可选字段
                
            volume = float(data['volume'])
            
            # 验证成交量非负
            if volume < 0:
                errors.append("成交量不能为负数")
                
            # 检查异常成交量 (如果有历史数据对比)
            # 这里可以添加基于历史数据的异常检测
            
            if errors:
                self.error_count += 1
                return False, errors
            else:
                return True, []
                
        except (ValueError, TypeError) as e:
            self.error_count += 1
            errors.append(f"成交量数据类型错误: {e}")
            return False, errors


class TimestampValidator(DataValidator):
    """时间戳验证器"""
    
    def __init__(self, max_future_seconds: int = 300, max_past_seconds: int = 86400):
        super().__init__("时间戳验证器")
        self.max_future_seconds = max_future_seconds
        self.max_past_seconds = max_past_seconds
        
    async def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证时间戳"""
        self.validation_count += 1
        errors = []
        
        try:
            if 'time' not in data:
                errors.append("缺少时间戳字段")
                self.error_count += 1
                return False, errors
                
            timestamp = data['time']
            current_time = time.time()
            
            # 转换时间戳格式
            if isinstance(timestamp, str):
                timestamp = float(timestamp)
            elif isinstance(timestamp, datetime):
                timestamp = timestamp.timestamp()
                
            # 检查时间戳范围
            time_diff = timestamp - current_time
            
            if time_diff > self.max_future_seconds:
                errors.append(f"时间戳过于未来: {time_diff:.0f}秒")
                
            if time_diff < -self.max_past_seconds:
                errors.append(f"时间戳过于过去: {abs(time_diff):.0f}秒")
                
            if errors:
                self.error_count += 1
                return False, errors
            else:
                return True, []
                
        except (ValueError, TypeError) as e:
            self.error_count += 1
            errors.append(f"时间戳格式错误: {e}")
            return False, errors


class ContinuityValidator(DataValidator):
    """连续性验证器"""
    
    def __init__(self, expected_interval: int = 900):  # 15分钟 = 900秒
        super().__init__("连续性验证器")
        self.expected_interval = expected_interval
        self.last_timestamp = None
        self.tolerance = expected_interval * 0.1  # 10%容差
        
    async def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证数据连续性"""
        self.validation_count += 1
        errors = []
        
        try:
            if 'time' not in data:
                return True, []  # 没有时间戳无法验证连续性
                
            current_timestamp = float(data['time'])
            
            if self.last_timestamp is not None:
                time_gap = current_timestamp - self.last_timestamp
                expected_gap = self.expected_interval
                
                # 检查时间间隔
                if abs(time_gap - expected_gap) > self.tolerance:
                    if time_gap > expected_gap:
                        errors.append(f"数据间隔过大: {time_gap:.0f}s (期望: {expected_gap:.0f}s)")
                    else:
                        errors.append(f"数据间隔过小: {time_gap:.0f}s (期望: {expected_gap:.0f}s)")
                        
            self.last_timestamp = current_timestamp
            
            if errors:
                self.error_count += 1
                return False, errors
            else:
                return True, []
                
        except (ValueError, TypeError) as e:
            self.error_count += 1
            errors.append(f"连续性验证错误: {e}")
            return False, errors


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, symbol: str, window_size: int = 100):
        self.symbol = symbol
        self.window_size = window_size
        
        # 历史数据窗口
        self.price_history: deque = deque(maxlen=window_size)
        self.volume_history: deque = deque(maxlen=window_size)
        self.time_history: deque = deque(maxlen=window_size)
        
        # 异常计数
        self.anomaly_count = 0
        self.detected_anomalies: List[DataAnomaly] = []
        
    async def detect_anomalies(self, data: Dict[str, Any]) -> List[DataAnomaly]:
        """检测数据异常"""
        anomalies = []
        
        try:
            current_time = time.time()
            
            # 价格异常检测
            if 'close' in data:
                price_anomalies = await self._detect_price_anomalies(data, current_time)
                anomalies.extend(price_anomalies)
                
            # 成交量异常检测
            if 'volume' in data:
                volume_anomalies = await self._detect_volume_anomalies(data, current_time)
                anomalies.extend(volume_anomalies)
                
            # 时间异常检测
            if 'time' in data:
                time_anomalies = await self._detect_time_anomalies(data, current_time)
                anomalies.extend(time_anomalies)
                
            # 更新历史数据
            self._update_history(data)
            
            # 保存检测到的异常
            self.detected_anomalies.extend(anomalies)
            self.anomaly_count += len(anomalies)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return []
            
    async def _detect_price_anomalies(self, data: Dict[str, Any], current_time: float) -> List[DataAnomaly]:
        """检测价格异常"""
        anomalies = []
        
        try:
            if len(self.price_history) < 10:  # 需要足够的历史数据
                return anomalies
                
            current_price = float(data['close'])
            
            # 计算价格统计
            prices = list(self.price_history)
            mean_price = statistics.mean(prices)
            std_price = statistics.stdev(prices) if len(prices) > 1 else 0
            
            if std_price > 0:
                # Z-score异常检测
                z_score = abs(current_price - mean_price) / std_price
                
                if z_score > 3:  # 3-sigma规则
                    severity = min(1.0, z_score / 5.0)  # 最大1.0
                    anomalies.append(DataAnomaly(
                        anomaly_id=f"price_spike_{self.symbol}_{int(current_time)}",
                        anomaly_type=AnomalyType.PRICE_SPIKE,
                        symbol=self.symbol,
                        timestamp=current_time,
                        severity=severity,
                        description=f"价格异常跳跃，Z-score: {z_score:.2f}",
                        details={
                            'current_price': current_price,
                            'mean_price': mean_price,
                            'std_price': std_price,
                            'z_score': z_score
                        }
                    ))
                    
            # 极值检测
            if len(prices) >= 20:
                percentile_95 = statistics.quantiles(prices, n=20)[18]  # 95th percentile
                percentile_5 = statistics.quantiles(prices, n=20)[0]   # 5th percentile
                
                if current_price > percentile_95 * 1.2 or current_price < percentile_5 * 0.8:
                    anomalies.append(DataAnomaly(
                        anomaly_id=f"extreme_value_{self.symbol}_{int(current_time)}",
                        anomaly_type=AnomalyType.EXTREME_VALUE,
                        symbol=self.symbol,
                        timestamp=current_time,
                        severity=0.7,
                        description="价格超出正常范围",
                        details={
                            'current_price': current_price,
                            'percentile_95': percentile_95,
                            'percentile_5': percentile_5
                        }
                    ))
                    
        except Exception as e:
            logger.error(f"价格异常检测失败: {e}")
            
        return anomalies
        
    async def _detect_volume_anomalies(self, data: Dict[str, Any], current_time: float) -> List[DataAnomaly]:
        """检测成交量异常"""
        anomalies = []
        
        try:
            if len(self.volume_history) < 10:
                return anomalies
                
            current_volume = float(data['volume'])
            
            # 计算成交量统计
            volumes = [v for v in self.volume_history if v > 0]
            if not volumes:
                return anomalies
                
            mean_volume = statistics.mean(volumes)
            
            # 成交量异常 (过高或过低)
            if current_volume > mean_volume * 10:  # 10倍以上
                anomalies.append(DataAnomaly(
                    anomaly_id=f"volume_spike_{self.symbol}_{int(current_time)}",
                    anomaly_type=AnomalyType.VOLUME_ANOMALY,
                    symbol=self.symbol,
                    timestamp=current_time,
                    severity=0.6,
                    description=f"成交量异常增大: {current_volume:.0f} (平均: {mean_volume:.0f})",
                    details={
                        'current_volume': current_volume,
                        'mean_volume': mean_volume,
                        'ratio': current_volume / mean_volume
                    }
                ))
                
        except Exception as e:
            logger.error(f"成交量异常检测失败: {e}")
            
        return anomalies
        
    async def _detect_time_anomalies(self, data: Dict[str, Any], current_time: float) -> List[DataAnomaly]:
        """检测时间异常"""
        anomalies = []
        
        try:
            if len(self.time_history) < 2:
                return anomalies
                
            data_timestamp = float(data['time'])
            last_timestamp = self.time_history[-1]
            
            # 时间间隔异常
            time_gap = data_timestamp - last_timestamp
            expected_gap = 900  # 15分钟
            
            if abs(time_gap - expected_gap) > expected_gap * 0.5:  # 50%容差
                anomalies.append(DataAnomaly(
                    anomaly_id=f"time_gap_{self.symbol}_{int(current_time)}",
                    anomaly_type=AnomalyType.TIME_GAP,
                    symbol=self.symbol,
                    timestamp=current_time,
                    severity=0.4,
                    description=f"时间间隔异常: {time_gap:.0f}s (期望: {expected_gap:.0f}s)",
                    details={
                        'actual_gap': time_gap,
                        'expected_gap': expected_gap,
                        'last_timestamp': last_timestamp,
                        'current_timestamp': data_timestamp
                    }
                ))
                
        except Exception as e:
            logger.error(f"时间异常检测失败: {e}")
            
        return anomalies
        
    def _update_history(self, data: Dict[str, Any]) -> None:
        """更新历史数据"""
        try:
            if 'close' in data:
                self.price_history.append(float(data['close']))
                
            if 'volume' in data:
                self.volume_history.append(float(data['volume']))
                
            if 'time' in data:
                self.time_history.append(float(data['time']))
                
        except Exception as e:
            logger.error(f"更新历史数据失败: {e}")
            
    def get_anomaly_stats(self) -> Dict[str, Any]:
        """获取异常统计"""
        anomaly_type_counts = defaultdict(int)
        total_severity = 0.0
        
        for anomaly in self.detected_anomalies:
            anomaly_type_counts[anomaly.anomaly_type.name] += 1
            total_severity += anomaly.severity
            
        avg_severity = total_severity / max(1, len(self.detected_anomalies))
        
        return {
            'total_anomalies': len(self.detected_anomalies),
            'anomaly_types': dict(anomaly_type_counts),
            'average_severity': avg_severity,
            'anomaly_rate': len(self.detected_anomalies) / max(1, len(self.price_history))
        }


class DataQualityEngine:
    """数据质量评估引擎"""
    
    def __init__(self):
        # 验证器集合
        self.validators = [
            OHLCValidator(),
            VolumeValidator(),
            TimestampValidator(),
            ContinuityValidator()
        ]
        
        # 异常检测器
        self.anomaly_detectors: Dict[str, AnomalyDetector] = {}
        
        # 质量历史
        self.quality_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 统计信息
        self.total_evaluations = 0
        self.quality_sum = 0.0
        
    async def evaluate_data_quality(self, symbol: str, data_batch: List[Dict[str, Any]]) -> QualityMetrics:
        """评估数据质量"""
        try:
            timeframe = "15m"  # 默认时间框架
            current_time = time.time()
            
            # 初始化指标
            metrics = QualityMetrics(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=current_time
            )
            
            if not data_batch:
                metrics.overall_quality_score = 0.0
                metrics.quality_level = QualityLevel.CRITICAL
                return metrics
                
            metrics.total_records = len(data_batch)
            
            # 数据验证
            validation_results = await self._validate_data_batch(data_batch)
            
            # 异常检测
            anomalies = await self._detect_batch_anomalies(symbol, data_batch)
            
            # 计算质量指标
            await self._calculate_quality_metrics(metrics, data_batch, validation_results, anomalies)
            
            # 保存质量历史
            self.quality_history[symbol].append(metrics)
            
            # 更新全局统计
            self.total_evaluations += 1
            self.quality_sum += metrics.overall_quality_score
            
            return metrics
            
        except Exception as e:
            logger.error(f"数据质量评估失败: {e}")
            return QualityMetrics(symbol=symbol, timeframe="15m", overall_quality_score=0.0)
            
    async def _validate_data_batch(self, data_batch: List[Dict[str, Any]]) -> Dict[str, List]:
        """批量验证数据"""
        validation_results = {
            'valid_records': [],
            'invalid_records': [],
            'validation_errors': []
        }
        
        for data in data_batch:
            is_valid = True
            record_errors = []
            
            # 使用所有验证器验证
            for validator in self.validators:
                try:
                    valid, errors = await validator.validate(data)
                    if not valid:
                        is_valid = False
                        record_errors.extend(errors)
                except Exception as e:
                    is_valid = False
                    record_errors.append(f"{validator.name}验证异常: {e}")
                    
            if is_valid:
                validation_results['valid_records'].append(data)
            else:
                validation_results['invalid_records'].append(data)
                validation_results['validation_errors'].extend(record_errors)
                
        return validation_results
        
    async def _detect_batch_anomalies(self, symbol: str, data_batch: List[Dict[str, Any]]) -> List[DataAnomaly]:
        """批量异常检测"""
        if symbol not in self.anomaly_detectors:
            self.anomaly_detectors[symbol] = AnomalyDetector(symbol)
            
        detector = self.anomaly_detectors[symbol]
        all_anomalies = []
        
        for data in data_batch:
            try:
                anomalies = await detector.detect_anomalies(data)
                all_anomalies.extend(anomalies)
            except Exception as e:
                logger.error(f"异常检测失败 {symbol}: {e}")
                
        return all_anomalies
        
    async def _calculate_quality_metrics(self, 
                                       metrics: QualityMetrics,
                                       data_batch: List[Dict[str, Any]],
                                       validation_results: Dict[str, List],
                                       anomalies: List[DataAnomaly]) -> None:
        """计算质量指标"""
        try:
            total_records = len(data_batch)
            valid_records = len(validation_results['valid_records'])
            
            # 完整性指标
            metrics.completeness_score = valid_records / max(1, total_records)
            metrics.missing_data_ratio = (total_records - valid_records) / max(1, total_records)
            metrics.valid_records = valid_records
            metrics.processed_records = total_records
            
            # 准确性指标
            invalid_ohlc_count = sum(1 for err in validation_results['validation_errors'] 
                                   if 'OHLC' in err or '价格' in err)
            metrics.invalid_ohlc_ratio = invalid_ohlc_count / max(1, total_records)
            metrics.accuracy_score = 1.0 - metrics.invalid_ohlc_ratio
            
            # 一致性指标
            time_errors = sum(1 for err in validation_results['validation_errors'] 
                            if '时间' in err or '间隔' in err)
            metrics.time_consistency_ratio = 1.0 - (time_errors / max(1, total_records))
            metrics.consistency_score = metrics.time_consistency_ratio
            
            # 及时性指标 
            if data_batch:
                latest_data = max(data_batch, key=lambda x: x.get('time', 0))
                if 'time' in latest_data:
                    data_time = float(latest_data['time'])
                    current_time = time.time()
                    metrics.data_delay = current_time - data_time
                    metrics.timeliness_score = max(0.0, 1.0 - (metrics.data_delay / 3600))  # 1小时内为满分
                    
            # 异常指标
            metrics.anomaly_count = len(anomalies)
            anomaly_types_count = defaultdict(int)
            total_severity = 0.0
            
            for anomaly in anomalies:
                anomaly_types_count[anomaly.anomaly_type.name] += 1
                total_severity += anomaly.severity
                
            metrics.anomaly_types = dict(anomaly_types_count)
            metrics.anomaly_severity = total_severity / max(1, len(anomalies))
            
            # 综合质量分数 (加权平均)
            quality_factors = [
                metrics.completeness_score * 0.25,    # 完整性 25%
                metrics.accuracy_score * 0.30,        # 准确性 30%
                metrics.consistency_score * 0.20,     # 一致性 20%
                metrics.timeliness_score * 0.15,      # 及时性 15%
                (1.0 - min(1.0, metrics.anomaly_severity)) * 0.10  # 异常程度 10%
            ]
            
            metrics.overall_quality_score = sum(quality_factors)
            
            # 确定质量等级
            if metrics.overall_quality_score >= 0.95:
                metrics.quality_level = QualityLevel.EXCELLENT
            elif metrics.overall_quality_score >= 0.85:
                metrics.quality_level = QualityLevel.GOOD
            elif metrics.overall_quality_score >= 0.70:
                metrics.quality_level = QualityLevel.FAIR
            elif metrics.overall_quality_score >= 0.50:
                metrics.quality_level = QualityLevel.POOR
            else:
                metrics.quality_level = QualityLevel.CRITICAL
                
        except Exception as e:
            logger.error(f"计算质量指标失败: {e}")
            metrics.overall_quality_score = 0.0
            metrics.quality_level = QualityLevel.CRITICAL
            
    def get_quality_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取质量摘要"""
        try:
            if symbol and symbol in self.quality_history:
                history = list(self.quality_history[symbol])
            else:
                # 汇总所有符号的质量历史
                history = []
                for symbol_history in self.quality_history.values():
                    history.extend(list(symbol_history))
                    
            if not history:
                return {
                    'total_evaluations': 0,
                    'average_quality_score': 0.0,
                    'quality_trend': 0.0,
                    'quality_distribution': {}
                }
                
            # 计算统计
            quality_scores = [m.overall_quality_score for m in history]
            avg_quality = statistics.mean(quality_scores)
            
            # 质量趋势 (最近10个vs之前的平均值)
            quality_trend = 0.0
            if len(quality_scores) >= 20:
                recent_avg = statistics.mean(quality_scores[-10:])
                previous_avg = statistics.mean(quality_scores[-20:-10])
                quality_trend = recent_avg - previous_avg
                
            # 质量分布
            quality_distribution = defaultdict(int)
            for metrics in history:
                quality_distribution[metrics.quality_level.name] += 1
                
            return {
                'total_evaluations': len(history),
                'average_quality_score': avg_quality,
                'quality_trend': quality_trend,
                'quality_distribution': dict(quality_distribution),
                'recent_quality_score': quality_scores[-1] if quality_scores else 0.0,
                'validator_stats': {
                    validator.name: {
                        'validation_count': validator.validation_count,
                        'error_count': validator.error_count,
                        'error_rate': validator.get_error_rate()
                    }
                    for validator in self.validators
                }
            }
            
        except Exception as e:
            logger.error(f"获取质量摘要失败: {e}")
            return {}
            
    def get_anomaly_report(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取异常报告"""
        try:
            if symbol and symbol in self.anomaly_detectors:
                detectors = [self.anomaly_detectors[symbol]]
            else:
                detectors = list(self.anomaly_detectors.values())
                
            if not detectors:
                return {'total_anomalies': 0}
                
            # 汇总异常统计
            total_anomalies = 0
            anomaly_type_counts = defaultdict(int)
            total_severity = 0.0
            
            for detector in detectors:
                stats = detector.get_anomaly_stats()
                total_anomalies += stats['total_anomalies']
                total_severity += stats['average_severity'] * stats['total_anomalies']
                
                for anomaly_type, count in stats['anomaly_types'].items():
                    anomaly_type_counts[anomaly_type] += count
                    
            avg_severity = total_severity / max(1, total_anomalies)
            
            return {
                'total_anomalies': total_anomalies,
                'anomaly_types': dict(anomaly_type_counts),
                'average_severity': avg_severity,
                'symbols_with_anomalies': len([d for d in detectors if d.anomaly_count > 0])
            }
            
        except Exception as e:
            logger.error(f"获取异常报告失败: {e}")
            return {}


# 便捷函数
async def evaluate_kline_quality(symbol: str, klines: List[Dict[str, Any]]) -> QualityMetrics:
    """便捷函数：评估K线数据质量"""
    engine = DataQualityEngine()
    return await engine.evaluate_data_quality(symbol, klines)