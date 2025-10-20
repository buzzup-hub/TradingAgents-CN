#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView连接健康监控系统
实现连接质量评估、异常检测和自动恢复
"""

import asyncio
import time
import statistics
from typing import Dict, List, Optional, Callable, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto

from config.logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    EXCELLENT = auto()    # 优秀 (90-100%)
    GOOD = auto()         # 良好 (70-89%)
    FAIR = auto()         # 一般 (50-69%)
    POOR = auto()         # 较差 (30-49%)
    CRITICAL = auto()     # 危险 (0-29%)


class AlertLevel(Enum):
    """告警级别"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class HealthMetrics:
    """健康指标"""
    timestamp: float = field(default_factory=time.time)
    
    # 连接指标
    is_connected: bool = False
    connection_uptime: float = 0.0
    total_reconnects: int = 0
    
    # 延迟指标
    current_latency: float = 0.0
    average_latency: float = 0.0
    max_latency: float = 0.0
    latency_variance: float = 0.0
    
    # 错误指标
    error_count: int = 0
    error_rate: float = 0.0
    last_error_time: Optional[float] = None
    
    # 消息指标
    messages_received: int = 0
    messages_processed: int = 0
    message_loss_rate: float = 0.0
    processing_rate: float = 0.0
    
    # 数据质量指标
    data_quality_score: float = 1.0
    data_freshness: float = 0.0
    data_completeness: float = 1.0
    
    # 综合健康分数
    overall_health_score: float = 1.0
    health_status: HealthStatus = HealthStatus.EXCELLENT


@dataclass
class HealthAlert:
    """健康告警"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: float = field(default_factory=time.time)
    metric_name: str = ""
    current_value: Any = None
    threshold: Any = None
    resolved: bool = False


class HealthThresholds:
    """健康阈值配置"""
    
    def __init__(self):
        # 延迟阈值 (毫秒)
        self.latency_warning = 1000
        self.latency_error = 3000
        self.latency_critical = 5000
        
        # 错误率阈值
        self.error_rate_warning = 0.05   # 5%
        self.error_rate_error = 0.15     # 15%
        self.error_rate_critical = 0.30  # 30%
        
        # 消息丢失率阈值
        self.message_loss_warning = 0.01  # 1%
        self.message_loss_error = 0.05    # 5%
        self.message_loss_critical = 0.10 # 10%
        
        # 数据质量阈值
        self.data_quality_warning = 0.90
        self.data_quality_error = 0.80
        self.data_quality_critical = 0.70
        
        # 数据新鲜度阈值 (秒)
        self.data_freshness_warning = 60
        self.data_freshness_error = 300
        self.data_freshness_critical = 600
        
        # 综合健康分数阈值
        self.health_score_warning = 0.70
        self.health_score_error = 0.50
        self.health_score_critical = 0.30


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        
        # 延迟数据
        self.latency_history: deque = deque(maxlen=window_size)
        self.ping_times: Dict[str, float] = {}
        
        # 错误数据
        self.error_history: deque = deque(maxlen=window_size)
        self.error_types: defaultdict = defaultdict(int)
        
        # 消息数据
        self.message_stats = {
            'received': 0,
            'processed': 0,
            'failed': 0,
            'last_received_time': 0,
            'processing_times': deque(maxlen=window_size)
        }
        
        # 连接数据
        self.connection_stats = {
            'connect_time': 0,
            'disconnect_count': 0,
            'reconnect_count': 0,
            'total_uptime': 0
        }
        
        # 数据质量
        self.data_quality_history: deque = deque(maxlen=100)
        
    def record_ping(self, ping_id: str) -> None:
        """记录ping发送"""
        self.ping_times[ping_id] = time.time()
        
    def record_pong(self, ping_id: str) -> None:
        """记录pong接收"""
        if ping_id in self.ping_times:
            latency = (time.time() - self.ping_times[ping_id]) * 1000
            self.latency_history.append(latency)
            del self.ping_times[ping_id]
            
    def record_error(self, error_type: str, error_msg: str) -> None:
        """记录错误"""
        self.error_history.append({
            'type': error_type,
            'message': error_msg,
            'timestamp': time.time()
        })
        self.error_types[error_type] += 1
        
    def record_message_received(self) -> None:
        """记录消息接收"""
        self.message_stats['received'] += 1
        self.message_stats['last_received_time'] = time.time()
        
    def record_message_processed(self, processing_time: float) -> None:
        """记录消息处理"""
        self.message_stats['processed'] += 1
        self.message_stats['processing_times'].append(processing_time)
        
    def record_message_failed(self) -> None:
        """记录消息处理失败"""
        self.message_stats['failed'] += 1
        
    def record_connection_event(self, event_type: str) -> None:
        """记录连接事件"""
        if event_type == 'connect':
            self.connection_stats['connect_time'] = time.time()
        elif event_type == 'disconnect':
            self.connection_stats['disconnect_count'] += 1
        elif event_type == 'reconnect':
            self.connection_stats['reconnect_count'] += 1
            
    def record_data_quality(self, quality_score: float) -> None:
        """记录数据质量"""
        self.data_quality_history.append({
            'score': quality_score,
            'timestamp': time.time()
        })
        
    def get_current_metrics(self) -> HealthMetrics:
        """获取当前健康指标"""
        current_time = time.time()
        
        # 计算延迟指标
        current_latency = self.latency_history[-1] if self.latency_history else 0
        avg_latency = statistics.mean(self.latency_history) if self.latency_history else 0
        max_latency = max(self.latency_history) if self.latency_history else 0
        latency_variance = statistics.variance(self.latency_history) if len(self.latency_history) > 1 else 0
        
        # 计算错误指标
        recent_errors = [
            err for err in self.error_history 
            if current_time - err['timestamp'] < 300  # 最近5分钟
        ]
        error_count = len(recent_errors)
        total_operations = self.message_stats['received'] + self.message_stats['processed']
        error_rate = error_count / max(1, total_operations)
        
        # 计算消息指标
        messages_received = self.message_stats['received']
        messages_processed = self.message_stats['processed']
        messages_failed = self.message_stats['failed']
        message_loss_rate = messages_failed / max(1, messages_received)
        
        avg_processing_time = 0
        if self.message_stats['processing_times']:
            avg_processing_time = statistics.mean(self.message_stats['processing_times'])
        processing_rate = messages_processed / max(1, avg_processing_time) if avg_processing_time > 0 else 0
        
        # 计算连接指标
        connection_uptime = 0
        if self.connection_stats['connect_time'] > 0:
            connection_uptime = current_time - self.connection_stats['connect_time']
            
        # 计算数据质量指标
        data_quality_score = 1.0
        data_freshness = 0
        data_completeness = 1.0
        
        if self.data_quality_history:
            recent_quality = [
                q['score'] for q in self.data_quality_history
                if current_time - q['timestamp'] < 300
            ]
            if recent_quality:
                data_quality_score = statistics.mean(recent_quality)
                
        if self.message_stats['last_received_time'] > 0:
            data_freshness = current_time - self.message_stats['last_received_time']
            
        # 计算综合健康分数
        health_factors = [
            1.0 - min(1.0, avg_latency / 5000),  # 延迟因子
            1.0 - min(1.0, error_rate),          # 错误因子
            1.0 - min(1.0, message_loss_rate),   # 丢失因子
            data_quality_score,                  # 质量因子
            min(1.0, connection_uptime / 3600)   # 稳定性因子
        ]
        
        overall_health_score = sum(health_factors) / len(health_factors)
        
        # 确定健康状态
        if overall_health_score >= 0.9:
            health_status = HealthStatus.EXCELLENT
        elif overall_health_score >= 0.7:
            health_status = HealthStatus.GOOD
        elif overall_health_score >= 0.5:
            health_status = HealthStatus.FAIR
        elif overall_health_score >= 0.3:
            health_status = HealthStatus.POOR
        else:
            health_status = HealthStatus.CRITICAL
            
        return HealthMetrics(
            timestamp=current_time,
            is_connected=self.connection_stats['connect_time'] > 0,
            connection_uptime=connection_uptime,
            total_reconnects=self.connection_stats['reconnect_count'],
            current_latency=current_latency,
            average_latency=avg_latency,
            max_latency=max_latency,
            latency_variance=latency_variance,
            error_count=error_count,
            error_rate=error_rate,
            last_error_time=recent_errors[-1]['timestamp'] if recent_errors else None,
            messages_received=messages_received,
            messages_processed=messages_processed,
            message_loss_rate=message_loss_rate,
            processing_rate=processing_rate,
            data_quality_score=data_quality_score,
            data_freshness=data_freshness,
            data_completeness=data_completeness,
            overall_health_score=overall_health_score,
            health_status=health_status
        )


class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.alerts: deque = deque(maxlen=max_alerts)
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.alert_callbacks: List[Callable] = []
        self.alert_count = 0
        
    def add_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """添加告警回调"""
        self.alert_callbacks.append(callback)
        
    def create_alert(self, 
                    level: AlertLevel,
                    title: str,
                    message: str,
                    metric_name: str = "",
                    current_value: Any = None,
                    threshold: Any = None) -> HealthAlert:
        """创建告警"""
        alert_id = f"alert_{self.alert_count}_{int(time.time())}"
        self.alert_count += 1
        
        alert = HealthAlert(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold
        )
        
        # 添加到告警列表
        self.alerts.append(alert)
        self.active_alerts[alert_id] = alert
        
        # 通知回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调失败: {e}")
                
        logger.warning(f"产生 {level.name} 级别告警: {title}")
        return alert
        
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]
            
            logger.info(f"告警已解决: {alert.title}")
            return True
        return False
        
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[HealthAlert]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
        
    def get_alert_summary(self) -> Dict[str, int]:
        """获取告警摘要"""
        summary = {level.name: 0 for level in AlertLevel}
        for alert in self.active_alerts.values():
            summary[alert.level.name] += 1
        return summary


class ConnectionHealthMonitor:
    """连接健康监控器"""
    
    def __init__(self, 
                 check_interval: float = 30.0,
                 enable_auto_recovery: bool = True):
        
        self.check_interval = check_interval
        self.enable_auto_recovery = enable_auto_recovery
        
        # 核心组件
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.thresholds = HealthThresholds()
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 健康历史
        self.health_history: deque = deque(maxlen=1000)
        
        # 回调函数
        self.health_callbacks: List[Callable] = []
        self.recovery_callbacks: List[Callable] = []
        
        # 自动恢复配置
        self.auto_recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5分钟
        self.last_recovery_time = 0
        
    async def start_monitoring(self) -> None:
        """开始健康监控"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("连接健康监控已启动")
        
    async def stop_monitoring(self) -> None:
        """停止健康监控"""
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("连接健康监控已停止")
        
    def add_health_callback(self, callback: Callable[[HealthMetrics], None]) -> None:
        """添加健康状态回调"""
        self.health_callbacks.append(callback)
        
    def add_recovery_callback(self, callback: Callable[[], None]) -> None:
        """添加恢复回调"""
        self.recovery_callbacks.append(callback)
        
    async def _monitoring_loop(self) -> None:
        """监控主循环"""
        while self.is_monitoring:
            try:
                # 收集当前指标
                current_metrics = self.metrics_collector.get_current_metrics()
                
                # 保存健康历史
                self.health_history.append(current_metrics)
                
                # 健康检查和告警
                await self._check_health_and_alert(current_metrics)
                
                # 通知健康状态回调
                for callback in self.health_callbacks:
                    try:
                        await callback(current_metrics)
                    except Exception as e:
                        logger.error(f"健康状态回调失败: {e}")
                
                # 自动恢复检查
                if self.enable_auto_recovery:
                    await self._check_auto_recovery(current_metrics)
                    
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"健康监控异常: {e}")
                await asyncio.sleep(5)
                
    async def _check_health_and_alert(self, metrics: HealthMetrics) -> None:
        """健康检查和告警"""
        try:
            # 延迟告警
            if metrics.average_latency > self.thresholds.latency_critical:
                self.alert_manager.create_alert(
                    AlertLevel.CRITICAL,
                    "连接延迟过高",
                    f"平均延迟 {metrics.average_latency:.1f}ms 超过临界值",
                    "average_latency",
                    metrics.average_latency,
                    self.thresholds.latency_critical
                )
            elif metrics.average_latency > self.thresholds.latency_error:
                self.alert_manager.create_alert(
                    AlertLevel.ERROR,
                    "连接延迟告警",
                    f"平均延迟 {metrics.average_latency:.1f}ms 超过错误阈值",
                    "average_latency",
                    metrics.average_latency,
                    self.thresholds.latency_error
                )
            elif metrics.average_latency > self.thresholds.latency_warning:
                self.alert_manager.create_alert(
                    AlertLevel.WARNING,
                    "连接延迟预警",
                    f"平均延迟 {metrics.average_latency:.1f}ms 超过预警阈值",
                    "average_latency",
                    metrics.average_latency,
                    self.thresholds.latency_warning
                )
                
            # 错误率告警
            if metrics.error_rate > self.thresholds.error_rate_critical:
                self.alert_manager.create_alert(
                    AlertLevel.CRITICAL,
                    "错误率过高",
                    f"错误率 {metrics.error_rate:.1%} 超过临界值",
                    "error_rate",
                    metrics.error_rate,
                    self.thresholds.error_rate_critical
                )
                
            # 数据质量告警
            if metrics.data_quality_score < self.thresholds.data_quality_critical:
                self.alert_manager.create_alert(
                    AlertLevel.CRITICAL,
                    "数据质量严重下降",
                    f"数据质量分数 {metrics.data_quality_score:.2f} 低于临界值",
                    "data_quality_score",
                    metrics.data_quality_score,
                    self.thresholds.data_quality_critical
                )
                
            # 数据新鲜度告警
            if metrics.data_freshness > self.thresholds.data_freshness_critical:
                self.alert_manager.create_alert(
                    AlertLevel.CRITICAL,
                    "数据更新停滞",
                    f"数据已 {metrics.data_freshness:.0f} 秒未更新",
                    "data_freshness",
                    metrics.data_freshness,
                    self.thresholds.data_freshness_critical
                )
                
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            
    async def _check_auto_recovery(self, metrics: HealthMetrics) -> None:
        """检查自动恢复"""
        try:
            current_time = time.time()
            
            # 检查是否需要恢复
            needs_recovery = (
                metrics.health_status in [HealthStatus.POOR, HealthStatus.CRITICAL] or
                not metrics.is_connected or
                metrics.error_rate > self.thresholds.error_rate_error
            )
            
            if not needs_recovery:
                self.auto_recovery_attempts = 0
                return
                
            # 检查恢复冷却时间
            if current_time - self.last_recovery_time < self.recovery_cooldown:
                return
                
            # 检查恢复次数限制
            if self.auto_recovery_attempts >= self.max_recovery_attempts:
                logger.warning("已达到最大自动恢复次数")
                return
                
            # 执行自动恢复
            logger.info(f"执行自动恢复 (第 {self.auto_recovery_attempts + 1} 次)")
            
            for callback in self.recovery_callbacks:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"恢复回调失败: {e}")
                    
            self.auto_recovery_attempts += 1
            self.last_recovery_time = current_time
            
        except Exception as e:
            logger.error(f"自动恢复检查失败: {e}")
            
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        if not self.health_history:
            return {}
            
        latest_metrics = self.health_history[-1]
        
        # 计算趋势
        if len(self.health_history) >= 2:
            previous_metrics = self.health_history[-2]
            health_trend = latest_metrics.overall_health_score - previous_metrics.overall_health_score
        else:
            health_trend = 0.0
            
        return {
            'current_health': {
                'status': latest_metrics.health_status.name,
                'score': latest_metrics.overall_health_score,
                'trend': health_trend
            },
            'connection': {
                'is_connected': latest_metrics.is_connected,
                'uptime': latest_metrics.connection_uptime,
                'reconnects': latest_metrics.total_reconnects
            },
            'performance': {
                'current_latency': latest_metrics.current_latency,
                'average_latency': latest_metrics.average_latency,
                'max_latency': latest_metrics.max_latency,
                'processing_rate': latest_metrics.processing_rate
            },
            'quality': {
                'data_quality_score': latest_metrics.data_quality_score,
                'data_freshness': latest_metrics.data_freshness,
                'message_loss_rate': latest_metrics.message_loss_rate
            },
            'alerts': {
                'active_count': len(self.alert_manager.active_alerts),
                'summary': self.alert_manager.get_alert_summary(),
                'recent_alerts': [
                    {
                        'level': alert.level.name,
                        'title': alert.title,
                        'timestamp': alert.timestamp
                    }
                    for alert in self.alert_manager.get_active_alerts()[:5]
                ]
            },
            'auto_recovery': {
                'enabled': self.enable_auto_recovery,
                'attempts': self.auto_recovery_attempts,
                'last_recovery': self.last_recovery_time
            }
        }