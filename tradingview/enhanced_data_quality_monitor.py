#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版数据质量监控系统
实现多维度数据质量评估、实时监控和智能容错机制
"""

import asyncio
import time
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import deque, defaultdict
import logging
import numpy as np

from config.logging_config import get_logger

logger = get_logger(__name__)


class QualityLevel(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"    # >= 0.95
    GOOD = "good"             # >= 0.85
    ACCEPTABLE = "acceptable"  # >= 0.75
    POOR = "poor"             # >= 0.60
    UNACCEPTABLE = "unacceptable"  # < 0.60


class DataIssueType(Enum):
    """数据问题类型"""
    MISSING_DATA = "missing_data"
    INVALID_VALUE = "invalid_value"
    LOGICAL_ERROR = "logical_error"
    TIMESTAMP_ERROR = "timestamp_error"
    PRICE_ANOMALY = "price_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    SEQUENCE_ERROR = "sequence_error"
    DUPLICATE_DATA = "duplicate_data"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    completeness_score: float = 0.0      # 完整性得分
    accuracy_score: float = 0.0          # 准确性得分
    consistency_score: float = 0.0       # 一致性得分
    timeliness_score: float = 0.0        # 及时性得分
    validity_score: float = 0.0          # 有效性得分
    uniqueness_score: float = 0.0        # 唯一性得分
    overall_score: float = 0.0           # 综合得分
    quality_level: QualityLevel = QualityLevel.UNACCEPTABLE
    
    # 详细统计
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    missing_records: int = 0
    duplicate_records: int = 0
    
    # 问题统计
    issues: Dict[DataIssueType, int] = field(default_factory=dict)
    
    # 时间统计
    evaluation_time: float = 0.0
    data_timestamp: int = 0


@dataclass
class DataQualityAlert:
    """数据质量告警"""
    alert_id: str
    level: AlertLevel
    issue_type: DataIssueType
    symbol: str
    timeframe: str
    message: str
    details: Dict[str, Any]
    timestamp: int
    resolved: bool = False


@dataclass
class KlineValidationResult:
    """K线数据验证结果"""
    is_valid: bool
    quality_score: float
    issues: List[DataIssueType]
    metrics: DataQualityMetrics
    corrected_data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)


class DataQualityValidator:
    """数据质量验证器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化验证器"""
        self.config = config or {}
        
        # 质量阈值配置
        self.thresholds = {
            'min_completeness': self.config.get('min_completeness', 0.95),
            'min_accuracy': self.config.get('min_accuracy', 0.90),
            'max_price_deviation': self.config.get('max_price_deviation', 0.20),  # 20%
            'max_volume_deviation': self.config.get('max_volume_deviation', 5.0),  # 5倍
            'max_timestamp_gap': self.config.get('max_timestamp_gap', 300),      # 5分钟
            'min_price': self.config.get('min_price', 0.0001),
            'max_price': self.config.get('max_price', 1000000.0)
        }
        
        # 质量权重配置
        self.weights = {
            'completeness': self.config.get('completeness_weight', 0.25),
            'accuracy': self.config.get('accuracy_weight', 0.25),
            'consistency': self.config.get('consistency_weight', 0.20),
            'timeliness': self.config.get('timeliness_weight', 0.15),
            'validity': self.config.get('validity_weight', 0.10),
            'uniqueness': self.config.get('uniqueness_weight', 0.05)
        }
    
    async def validate_kline_data(self, data: Dict[str, Any]) -> KlineValidationResult:
        """验证K线数据质量"""
        start_time = time.time()
        
        klines = data.get('klines', [])
        symbol = data.get('symbol', 'UNKNOWN')
        timeframe = data.get('timeframe', 'UNKNOWN')
        
        # 初始化指标
        metrics = DataQualityMetrics()
        metrics.total_records = len(klines)
        metrics.data_timestamp = int(time.time())
        
        issues = []
        corrected_data = None
        suggestions = []
        
        if not klines:
            issues.append(DataIssueType.MISSING_DATA)
            metrics.overall_score = 0.0
            metrics.quality_level = QualityLevel.UNACCEPTABLE
            
            return KlineValidationResult(
                is_valid=False,
                quality_score=0.0,
                issues=issues,
                metrics=metrics,
                suggestions=["数据为空，请检查数据源"]
            )
        
        # 1. 完整性检查
        completeness_score = await self._check_completeness(klines, metrics, issues)
        
        # 2. 准确性检查
        accuracy_score = await self._check_accuracy(klines, metrics, issues)
        
        # 3. 一致性检查
        consistency_score = await self._check_consistency(klines, metrics, issues)
        
        # 4. 及时性检查
        timeliness_score = await self._check_timeliness(klines, metrics, issues)
        
        # 5. 有效性检查
        validity_score = await self._check_validity(klines, metrics, issues)
        
        # 6. 唯一性检查
        uniqueness_score = await self._check_uniqueness(klines, metrics, issues)
        
        # 计算综合得分
        overall_score = (
            completeness_score * self.weights['completeness'] +
            accuracy_score * self.weights['accuracy'] +
            consistency_score * self.weights['consistency'] +
            timeliness_score * self.weights['timeliness'] +
            validity_score * self.weights['validity'] +
            uniqueness_score * self.weights['uniqueness']
        )
        
        # 更新指标
        metrics.completeness_score = completeness_score
        metrics.accuracy_score = accuracy_score
        metrics.consistency_score = consistency_score
        metrics.timeliness_score = timeliness_score
        metrics.validity_score = validity_score
        metrics.uniqueness_score = uniqueness_score
        metrics.overall_score = overall_score
        metrics.quality_level = self._determine_quality_level(overall_score)
        metrics.evaluation_time = time.time() - start_time
        
        # 生成修复建议
        suggestions = self._generate_suggestions(issues, metrics)
        
        # 尝试数据修复
        if issues and overall_score > 0.6:
            corrected_data = await self._attempt_data_correction(data, issues)
        
        return KlineValidationResult(
            is_valid=overall_score >= self.thresholds['min_accuracy'],
            quality_score=overall_score,
            issues=issues,
            metrics=metrics,
            corrected_data=corrected_data,
            suggestions=suggestions
        )
    
    async def _check_completeness(self, klines: List[Dict], metrics: DataQualityMetrics, 
                                 issues: List[DataIssueType]) -> float:
        """检查数据完整性"""
        if not klines:
            issues.append(DataIssueType.MISSING_DATA)
            return 0.0
        
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        total_checks = len(klines) * len(required_fields)
        valid_checks = 0
        missing_count = 0
        
        for kline in klines:
            for field in required_fields:
                if field in kline and kline[field] is not None:
                    valid_checks += 1
                else:
                    missing_count += 1
        
        metrics.missing_records = missing_count
        
        if missing_count > 0:
            issues.append(DataIssueType.MISSING_DATA)
            if DataIssueType.MISSING_DATA not in metrics.issues:
                metrics.issues[DataIssueType.MISSING_DATA] = 0
            metrics.issues[DataIssueType.MISSING_DATA] += missing_count
        
        completeness = valid_checks / total_checks if total_checks > 0 else 0.0
        return completeness
    
    async def _check_accuracy(self, klines: List[Dict], metrics: DataQualityMetrics, 
                             issues: List[DataIssueType]) -> float:
        """检查数据准确性"""
        if not klines:
            return 0.0
        
        valid_count = 0
        invalid_count = 0
        
        for kline in klines:
            try:
                open_price = float(kline.get('open', 0))
                high_price = float(kline.get('high', 0))
                low_price = float(kline.get('low', 0))
                close_price = float(kline.get('close', 0))
                volume = float(kline.get('volume', 0))
                
                # 价格关系逻辑检查
                if not (low_price <= min(open_price, close_price) <= max(open_price, close_price) <= high_price):
                    invalid_count += 1
                    issues.append(DataIssueType.LOGICAL_ERROR)
                    continue
                
                # 价格范围检查
                if (open_price < self.thresholds['min_price'] or open_price > self.thresholds['max_price'] or
                    high_price < self.thresholds['min_price'] or high_price > self.thresholds['max_price'] or
                    low_price < self.thresholds['min_price'] or low_price > self.thresholds['max_price'] or
                    close_price < self.thresholds['min_price'] or close_price > self.thresholds['max_price']):
                    invalid_count += 1
                    issues.append(DataIssueType.INVALID_VALUE)
                    continue
                
                # 成交量检查
                if volume < 0:
                    invalid_count += 1
                    issues.append(DataIssueType.INVALID_VALUE)
                    continue
                
                valid_count += 1
                
            except (ValueError, TypeError):
                invalid_count += 1
                issues.append(DataIssueType.INVALID_VALUE)
        
        metrics.valid_records = valid_count
        metrics.invalid_records = invalid_count
        
        if invalid_count > 0:
            if DataIssueType.LOGICAL_ERROR not in metrics.issues:
                metrics.issues[DataIssueType.LOGICAL_ERROR] = 0
            if DataIssueType.INVALID_VALUE not in metrics.issues:
                metrics.issues[DataIssueType.INVALID_VALUE] = 0
            
            logical_errors = sum(1 for issue in issues if issue == DataIssueType.LOGICAL_ERROR)
            invalid_values = sum(1 for issue in issues if issue == DataIssueType.INVALID_VALUE)
            
            metrics.issues[DataIssueType.LOGICAL_ERROR] += logical_errors
            metrics.issues[DataIssueType.INVALID_VALUE] += invalid_values
        
        total_records = valid_count + invalid_count
        return valid_count / total_records if total_records > 0 else 0.0
    
    async def _check_consistency(self, klines: List[Dict], metrics: DataQualityMetrics, 
                                issues: List[DataIssueType]) -> float:
        """检查数据一致性"""
        if len(klines) < 2:
            return 1.0
        
        consistent_count = 0
        total_checks = len(klines) - 1
        
        # 检查价格异常波动
        for i in range(1, len(klines)):
            prev_kline = klines[i-1]
            curr_kline = klines[i]
            
            try:
                prev_close = float(prev_kline.get('close', 0))
                curr_open = float(curr_kline.get('open', 0))
                curr_high = float(curr_kline.get('high', 0))
                curr_low = float(curr_kline.get('low', 0))
                
                # 检查价格跳跃
                if prev_close > 0:
                    price_change = abs(curr_open - prev_close) / prev_close
                    if price_change > self.thresholds['max_price_deviation']:
                        issues.append(DataIssueType.PRICE_ANOMALY)
                        continue
                
                # 检查K线内部一致性
                if curr_high > 0 and curr_low > 0:
                    price_range = (curr_high - curr_low) / curr_high
                    if price_range > self.thresholds['max_price_deviation']:
                        issues.append(DataIssueType.PRICE_ANOMALY)
                        continue
                
                consistent_count += 1
                
            except (ValueError, TypeError, ZeroDivisionError):
                issues.append(DataIssueType.INVALID_VALUE)
        
        if DataIssueType.PRICE_ANOMALY in issues:
            anomaly_count = sum(1 for issue in issues if issue == DataIssueType.PRICE_ANOMALY)
            if DataIssueType.PRICE_ANOMALY not in metrics.issues:
                metrics.issues[DataIssueType.PRICE_ANOMALY] = 0
            metrics.issues[DataIssueType.PRICE_ANOMALY] += anomaly_count
        
        return consistent_count / total_checks if total_checks > 0 else 1.0
    
    async def _check_timeliness(self, klines: List[Dict], metrics: DataQualityMetrics, 
                               issues: List[DataIssueType]) -> float:
        """检查数据及时性"""
        if not klines:
            return 0.0
        
        current_time = int(time.time())
        timely_count = 0
        
        for kline in klines:
            try:
                timestamp = int(kline.get('timestamp', 0))
                
                # 检查时间戳有效性
                if timestamp <= 0:
                    issues.append(DataIssueType.TIMESTAMP_ERROR)
                    continue
                
                # 检查时间戳是否过于陈旧（超过7天）
                if current_time - timestamp > 7 * 24 * 3600:
                    issues.append(DataIssueType.TIMESTAMP_ERROR)
                    continue
                
                # 检查时间戳是否来自未来（超过1小时）
                if timestamp - current_time > 3600:
                    issues.append(DataIssueType.TIMESTAMP_ERROR)
                    continue
                
                timely_count += 1
                
            except (ValueError, TypeError):
                issues.append(DataIssueType.TIMESTAMP_ERROR)
        
        if DataIssueType.TIMESTAMP_ERROR in issues:
            error_count = sum(1 for issue in issues if issue == DataIssueType.TIMESTAMP_ERROR)
            if DataIssueType.TIMESTAMP_ERROR not in metrics.issues:
                metrics.issues[DataIssueType.TIMESTAMP_ERROR] = 0
            metrics.issues[DataIssueType.TIMESTAMP_ERROR] += error_count
        
        return timely_count / len(klines) if klines else 0.0
    
    async def _check_validity(self, klines: List[Dict], metrics: DataQualityMetrics, 
                             issues: List[DataIssueType]) -> float:
        """检查数据有效性"""
        if not klines:
            return 0.0
        
        valid_count = 0
        
        for kline in klines:
            try:
                # 检查必需字段是否存在且有效
                required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                field_valid = True
                
                for field in required_fields:
                    if field not in kline:
                        field_valid = False
                        break
                    
                    value = kline[field]
                    if value is None or (isinstance(value, str) and value.strip() == ''):
                        field_valid = False
                        break
                    
                    # 数值类型检查
                    if field != 'timestamp':
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            field_valid = False
                            break
                    else:
                        try:
                            int(value)
                        except (ValueError, TypeError):
                            field_valid = False
                            break
                
                if field_valid:
                    valid_count += 1
                else:
                    issues.append(DataIssueType.INVALID_VALUE)
                    
            except Exception:
                issues.append(DataIssueType.INVALID_VALUE)
        
        return valid_count / len(klines) if klines else 0.0
    
    async def _check_uniqueness(self, klines: List[Dict], metrics: DataQualityMetrics, 
                               issues: List[DataIssueType]) -> float:
        """检查数据唯一性（无重复）"""
        if not klines:
            return 1.0
        
        seen_timestamps = set()
        unique_count = 0
        duplicate_count = 0
        
        for kline in klines:
            try:
                timestamp = int(kline.get('timestamp', 0))
                
                if timestamp in seen_timestamps:
                    duplicate_count += 1
                    issues.append(DataIssueType.DUPLICATE_DATA)
                else:
                    seen_timestamps.add(timestamp)
                    unique_count += 1
                    
            except (ValueError, TypeError):
                # 无效时间戳，跳过
                pass
        
        metrics.duplicate_records = duplicate_count
        
        if duplicate_count > 0:
            if DataIssueType.DUPLICATE_DATA not in metrics.issues:
                metrics.issues[DataIssueType.DUPLICATE_DATA] = 0
            metrics.issues[DataIssueType.DUPLICATE_DATA] += duplicate_count
        
        total_valid = unique_count + duplicate_count
        return unique_count / total_valid if total_valid > 0 else 1.0
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级"""
        if score >= 0.95:
            return QualityLevel.EXCELLENT
        elif score >= 0.85:
            return QualityLevel.GOOD
        elif score >= 0.75:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.60:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def _generate_suggestions(self, issues: List[DataIssueType], 
                             metrics: DataQualityMetrics) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if DataIssueType.MISSING_DATA in issues:
            suggestions.append("存在缺失数据，建议检查数据源或使用数据插值方法")
        
        if DataIssueType.INVALID_VALUE in issues:
            suggestions.append("存在无效数值，建议进行数据清洗和格式标准化")
        
        if DataIssueType.LOGICAL_ERROR in issues:
            suggestions.append("存在逻辑错误（如high < low），建议检查数据源质量")
        
        if DataIssueType.TIMESTAMP_ERROR in issues:
            suggestions.append("存在时间戳错误，建议同步时间或检查时区设置")
        
        if DataIssueType.PRICE_ANOMALY in issues:
            suggestions.append("存在价格异常波动，建议启用异常检测和过滤机制")
        
        if DataIssueType.VOLUME_ANOMALY in issues:
            suggestions.append("存在成交量异常，建议检查数据源或应用平滑算法")
        
        if DataIssueType.DUPLICATE_DATA in issues:
            suggestions.append("存在重复数据，建议启用去重机制")
        
        if metrics.overall_score < 0.8:
            suggestions.append("整体数据质量偏低，建议考虑更换数据源或增强数据清洗")
        
        return suggestions
    
    async def _attempt_data_correction(self, data: Dict[str, Any], 
                                      issues: List[DataIssueType]) -> Optional[Dict[str, Any]]:
        """尝试数据修复"""
        # 简单的数据修复逻辑
        corrected_data = data.copy()
        klines = corrected_data.get('klines', [])
        
        if not klines:
            return None
        
        corrected_klines = []
        
        for kline in klines:
            corrected_kline = kline.copy()
            
            try:
                # 修复价格逻辑错误
                open_price = float(corrected_kline.get('open', 0))
                high_price = float(corrected_kline.get('high', 0))
                low_price = float(corrected_kline.get('low', 0))
                close_price = float(corrected_kline.get('close', 0))
                
                # 确保high是最高价，low是最低价
                actual_high = max(open_price, high_price, low_price, close_price)
                actual_low = min(open_price, high_price, low_price, close_price)
                
                corrected_kline['high'] = actual_high
                corrected_kline['low'] = actual_low
                
                corrected_klines.append(corrected_kline)
                
            except (ValueError, TypeError):
                # 无法修复的数据，跳过
                continue
        
        corrected_data['klines'] = corrected_klines
        return corrected_data


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化监控器"""
        self.config = config or {}
        self.validator = DataQualityValidator(config)
        
        # 监控状态
        self.active_monitors = set()
        self.quality_history = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = deque(maxlen=10000)
        self.alert_handlers = []
        
        # 统计信息
        self.total_evaluations = 0
        self.total_issues = defaultdict(int)
        self.avg_quality_score = 0.0
        
        # 阈值配置
        self.alert_thresholds = {
            'critical_quality_score': self.config.get('critical_quality_score', 0.6),
            'warning_quality_score': self.config.get('warning_quality_score', 0.8),
            'max_consecutive_failures': self.config.get('max_consecutive_failures', 3)
        }
        
        logger.info("数据质量监控器初始化完成")
    
    async def evaluate_data_quality(self, symbol: str, timeframe: str, 
                                   data: Dict[str, Any]) -> KlineValidationResult:
        """评估数据质量"""
        validation_result = await self.validator.validate_kline_data(data)
        
        # 更新统计
        self.total_evaluations += 1
        
        # 记录质量历史
        monitor_key = f"{symbol}:{timeframe}"
        self.quality_history[monitor_key].append({
            'timestamp': int(time.time()),
            'quality_score': validation_result.quality_score,
            'quality_level': validation_result.metrics.quality_level.value,
            'issues': [issue.value for issue in validation_result.issues]
        })
        
        # 更新平均质量得分
        total_score = self.avg_quality_score * (self.total_evaluations - 1) + validation_result.quality_score
        self.avg_quality_score = total_score / self.total_evaluations
        
        # 统计问题类型
        for issue in validation_result.issues:
            self.total_issues[issue] += 1
        
        # 生成告警
        await self._check_and_generate_alerts(symbol, timeframe, validation_result)
        
        logger.debug(f"数据质量评估完成: {symbol}:{timeframe} 得分={validation_result.quality_score:.3f}")
        
        return validation_result
    
    async def _check_and_generate_alerts(self, symbol: str, timeframe: str, 
                                        result: KlineValidationResult) -> None:
        """检查并生成告警"""
        quality_score = result.quality_score
        
        # 生成质量告警
        if quality_score < self.alert_thresholds['critical_quality_score']:
            alert = DataQualityAlert(
                alert_id=f"quality_{symbol}_{timeframe}_{int(time.time())}",
                level=AlertLevel.CRITICAL,
                issue_type=DataIssueType.INVALID_VALUE,
                symbol=symbol,
                timeframe=timeframe,
                message=f"数据质量严重下降: {quality_score:.3f}",
                details={
                    'quality_score': quality_score,
                    'quality_level': result.metrics.quality_level.value,
                    'issues': [issue.value for issue in result.issues],
                    'suggestions': result.suggestions
                },
                timestamp=int(time.time())
            )
            
            await self._emit_alert(alert)
            
        elif quality_score < self.alert_thresholds['warning_quality_score']:
            alert = DataQualityAlert(
                alert_id=f"quality_{symbol}_{timeframe}_{int(time.time())}",
                level=AlertLevel.WARNING,
                issue_type=DataIssueType.INVALID_VALUE,
                symbol=symbol,
                timeframe=timeframe,
                message=f"数据质量下降: {quality_score:.3f}",
                details={
                    'quality_score': quality_score,
                    'quality_level': result.metrics.quality_level.value,
                    'issues': [issue.value for issue in result.issues]
                },
                timestamp=int(time.time())
            )
            
            await self._emit_alert(alert)
    
    async def _emit_alert(self, alert: DataQualityAlert) -> None:
        """发送告警"""
        self.alerts.append(alert)
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        logger.warning(f"数据质量告警: {alert.level.value} - {alert.message}")
    
    def register_alert_handler(self, handler: callable) -> None:
        """注册告警处理器"""
        self.alert_handlers.append(handler)
        logger.info(f"注册告警处理器: {handler.__name__}")
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """获取质量统计信息"""
        recent_alerts = [alert for alert in self.alerts 
                        if alert.timestamp > int(time.time()) - 3600]  # 最近1小时
        
        return {
            'total_evaluations': self.total_evaluations,
            'avg_quality_score': self.avg_quality_score,
            'total_issues_by_type': dict(self.total_issues),
            'active_monitors': len(self.active_monitors),
            'recent_alerts_count': len(recent_alerts),
            'alert_distribution': {
                level.value: sum(1 for alert in recent_alerts if alert.level == level)
                for level in AlertLevel
            }
        }
    
    def get_symbol_quality_history(self, symbol: str, timeframe: str, 
                                  hours: int = 24) -> List[Dict[str, Any]]:
        """获取品种质量历史"""
        monitor_key = f"{symbol}:{timeframe}"
        
        if monitor_key not in self.quality_history:
            return []
        
        cutoff_time = int(time.time()) - (hours * 3600)
        
        return [
            record for record in self.quality_history[monitor_key]
            if record['timestamp'] > cutoff_time
        ]
    
    def get_recent_alerts(self, hours: int = 24) -> List[DataQualityAlert]:
        """获取最近告警"""
        cutoff_time = int(time.time()) - (hours * 3600)
        
        return [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time
        ]


# ==================== 容错机制 ====================

class DataFaultTolerance:
    """数据容错机制"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化容错机制"""
        self.config = config or {}
        self.fallback_strategies = {}
        self.circuit_breakers = {}
        
    def register_fallback_strategy(self, issue_type: DataIssueType, strategy: callable) -> None:
        """注册容错策略"""
        self.fallback_strategies[issue_type] = strategy
        logger.info(f"注册容错策略: {issue_type.value}")
    
    async def handle_data_issue(self, issue_type: DataIssueType, 
                               context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理数据问题"""
        if issue_type in self.fallback_strategies:
            try:
                strategy = self.fallback_strategies[issue_type]
                return await strategy(context)
            except Exception as e:
                logger.error(f"容错策略执行失败: {e}")
        
        return None


# ==================== 使用示例 ====================

async def example_quality_monitoring():
    """质量监控使用示例"""
    
    # 初始化监控器
    monitor = DataQualityMonitor({
        'critical_quality_score': 0.6,
        'warning_quality_score': 0.8
    })
    
    # 注册告警处理器
    async def alert_handler(alert: DataQualityAlert):
        print(f"收到告警: {alert.level.value} - {alert.message}")
    
    monitor.register_alert_handler(alert_handler)
    
    # 模拟数据质量评估
    sample_data = {
        'symbol': 'BINANCE:BTCUSDT',
        'timeframe': '15',
        'klines': [
            {
                'timestamp': int(time.time()) - 900,
                'open': 35000.0,
                'high': 35500.0,
                'low': 34800.0,
                'close': 35200.0,
                'volume': 123.45
            },
            {
                'timestamp': int(time.time()),
                'open': 35200.0,
                'high': 35800.0,
                'low': 35000.0,
                'close': 35600.0,
                'volume': 156.78
            }
        ]
    }
    
    # 评估数据质量
    result = await monitor.evaluate_data_quality('BINANCE:BTCUSDT', '15', sample_data)
    
    print(f"质量评估结果:")
    print(f"- 总体得分: {result.quality_score:.3f}")
    print(f"- 质量等级: {result.metrics.quality_level.value}")
    print(f"- 发现问题: {len(result.issues)}个")
    print(f"- 改进建议: {len(result.suggestions)}条")
    
    # 获取统计信息
    stats = monitor.get_quality_statistics()
    print(f"监控统计: {stats}")


if __name__ == "__main__":
    asyncio.run(example_quality_monitoring())