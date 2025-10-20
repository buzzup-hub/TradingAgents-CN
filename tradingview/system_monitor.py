#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView系统综合监控管理器
整合连接健康、数据质量、性能优化和故障恢复的统一监控
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum, auto
import logging
import threading

from .enhanced_client import EnhancedTradingViewClient
from .data_quality_monitor import DataQualityEngine
from .connection_health import ConnectionHealthMonitor
from .performance_optimizer import PerformanceOptimizer
from .fault_recovery import FaultRecoveryManager
from .trading_integration import TradingCoreIntegrationManager
from .realtime_adapter import AdvancedRealtimeAdapter

from config.logging_config import get_logger

logger = get_logger(__name__)


class SystemStatus(Enum):
    """系统状态"""
    STARTING = auto()      # 启动中
    HEALTHY = auto()       # 健康
    DEGRADED = auto()      # 降级
    WARNING = auto()       # 警告
    CRITICAL = auto()      # 危险
    OFFLINE = auto()       # 离线


class AlertLevel(Enum):
    """告警级别"""
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class SystemAlert:
    """系统告警"""
    alert_id: str
    level: AlertLevel
    component: str
    title: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentStatus:
    """组件状态"""
    name: str
    status: SystemStatus = SystemStatus.STARTING
    last_update: float = field(default_factory=time.time)
    health_score: float = 1.0
    error_count: int = 0
    uptime_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """系统综合指标"""
    timestamp: float = field(default_factory=time.time)
    
    # 整体状态
    overall_status: SystemStatus = SystemStatus.STARTING
    overall_health_score: float = 1.0
    uptime_seconds: float = 0.0
    
    # 组件状态
    component_count: int = 0
    healthy_components: int = 0
    degraded_components: int = 0
    critical_components: int = 0
    
    # 性能指标
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    
    # 数据指标
    data_quality_score: float = 1.0
    data_throughput: int = 0
    cache_hit_rate: float = 0.0
    
    # 连接指标
    active_connections: int = 0
    connection_pool_utilization: float = 0.0
    
    # 故障指标
    active_incidents: int = 0
    resolved_incidents_today: int = 0
    
    # 资源指标
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class SystemMonitor:
    """系统综合监控管理器"""
    
    def __init__(self):
        # 核心组件
        self.enhanced_client: Optional[EnhancedTradingViewClient] = None
        self.data_quality_engine: Optional[DataQualityEngine] = None
        self.connection_monitor: Optional[ConnectionHealthMonitor] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        self.fault_recovery_manager: Optional[FaultRecoveryManager] = None
        self.integration_manager: Optional[TradingCoreIntegrationManager] = None
        self.realtime_adapter: Optional[AdvancedRealtimeAdapter] = None
        
        # 监控状态
        self.system_start_time = time.time()
        self.is_running = False
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # 组件状态跟踪
        self.component_status: Dict[str, ComponentStatus] = {}
        
        # 告警管理
        self.active_alerts: Dict[str, SystemAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_callbacks: List[Callable[[SystemAlert], None]] = []
        
        # 指标历史
        self.metrics_history: deque = deque(maxlen=1440)  # 24小时，每分钟一个
        
        # 监控配置
        self.monitoring_config = {
            'health_check_interval': 30,      # 健康检查间隔30秒
            'metrics_collection_interval': 60, # 指标收集间隔60秒
            'alert_check_interval': 10,        # 告警检查间隔10秒
            'component_timeout': 300,          # 组件超时5分钟
            
            # 告警阈值
            'health_score_warning': 0.8,
            'health_score_critical': 0.6,
            'response_time_warning': 1000,     # 1秒
            'response_time_critical': 3000,    # 3秒
            'error_rate_warning': 0.05,        # 5%
            'error_rate_critical': 0.15,       # 15%
            'data_quality_warning': 0.8,
            'data_quality_critical': 0.6,
        }
        
        # 统计信息
        self.monitoring_stats = {
            'total_health_checks': 0,
            'total_alerts_generated': 0,
            'total_metrics_collected': 0,
            'monitoring_uptime': 0.0
        }
    
    async def initialize(self, components: Dict[str, Any]) -> bool:
        """
        初始化系统监控
        
        Args:
            components: 要监控的组件字典
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("🚀 开始初始化系统监控...")
            
            # 初始化各个组件
            self.enhanced_client = components.get('enhanced_client')
            self.data_quality_engine = components.get('data_quality_engine') 
            self.connection_monitor = components.get('connection_monitor')
            self.performance_optimizer = components.get('performance_optimizer')
            self.fault_recovery_manager = components.get('fault_recovery_manager')
            self.integration_manager = components.get('integration_manager')
            self.realtime_adapter = components.get('realtime_adapter')
            
            # 注册组件状态
            for component_name in components.keys():
                self.component_status[component_name] = ComponentStatus(name=component_name)
            
            # 启动各个监控任务
            self.is_running = True
            
            # 健康检查任务
            health_task = asyncio.create_task(self._health_check_loop())
            self.monitoring_tasks.append(health_task)
            
            # 指标收集任务
            metrics_task = asyncio.create_task(self._metrics_collection_loop())
            self.monitoring_tasks.append(metrics_task)
            
            # 告警检查任务
            alert_task = asyncio.create_task(self._alert_check_loop())
            self.monitoring_tasks.append(alert_task)
            
            # 组件状态更新任务
            status_task = asyncio.create_task(self._component_status_loop())
            self.monitoring_tasks.append(status_task)
            
            logger.info("✅ 系统监控初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 系统监控初始化失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭系统监控"""
        try:
            logger.info("关闭系统监控...")
            
            self.is_running = False
            
            # 取消所有监控任务
            for task in self.monitoring_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.monitoring_tasks:
                await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
            self.monitoring_tasks.clear()
            
            logger.info("系统监控已关闭")
            
        except Exception as e:
            logger.error(f"关闭系统监控失败: {e}")
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.is_running:
            try:
                await self._perform_health_checks()
                self.monitoring_stats['total_health_checks'] += 1
                
                await asyncio.sleep(self.monitoring_config['health_check_interval'])
                
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        try:
            current_time = time.time()
            
            # 检查增强客户端
            if self.enhanced_client:
                await self._check_enhanced_client_health()
            
            # 检查数据质量引擎
            if self.data_quality_engine:
                await self._check_data_quality_health()
            
            # 检查连接监控器
            if self.connection_monitor:
                await self._check_connection_monitor_health()
            
            # 检查性能优化器
            if self.performance_optimizer:
                await self._check_performance_optimizer_health()
            
            # 检查故障恢复管理器
            if self.fault_recovery_manager:
                await self._check_fault_recovery_health()
            
            # 检查集成管理器
            if self.integration_manager:
                await self._check_integration_manager_health()
            
            # 检查实时适配器
            if self.realtime_adapter:
                await self._check_realtime_adapter_health()
            
            # 更新组件运行时间
            for component in self.component_status.values():
                component.uptime_seconds = current_time - self.system_start_time
                component.last_update = current_time
                
        except Exception as e:
            logger.error(f"执行健康检查失败: {e}")
    
    async def _check_enhanced_client_health(self) -> None:
        """检查增强客户端健康状态"""
        try:
            component_name = 'enhanced_client'
            status = self.component_status[component_name]
            
            # 获取连接统计
            connection_stats = self.enhanced_client.get_connection_stats()
            
            # 计算健康分数
            health_score = 1.0
            if connection_stats['state'] != 'connected':
                health_score *= 0.3
            
            quality_score = connection_stats.get('quality_score', 1.0)
            health_score *= quality_score
            
            # 更新状态
            status.health_score = health_score
            status.metrics = connection_stats
            
            if health_score >= 0.8:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.6:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查增强客户端健康状态失败: {e}")
            if 'enhanced_client' in self.component_status:
                self.component_status['enhanced_client'].status = SystemStatus.CRITICAL
    
    async def _check_data_quality_health(self) -> None:
        """检查数据质量引擎健康状态"""
        try:
            component_name = 'data_quality_engine'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取质量摘要
            quality_summary = self.data_quality_engine.get_quality_summary()
            
            # 计算健康分数
            avg_quality = quality_summary.get('average_quality_score', 1.0)
            health_score = avg_quality
            
            # 更新状态
            status.health_score = health_score
            status.metrics = quality_summary
            
            if health_score >= 0.9:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.7:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查数据质量引擎健康状态失败: {e}")
    
    async def _check_connection_monitor_health(self) -> None:
        """检查连接监控器健康状态"""
        try:
            component_name = 'connection_monitor'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取健康报告
            health_report = self.connection_monitor.get_health_report()
            
            # 计算健康分数
            current_health = health_report.get('current_health', {})
            health_score = current_health.get('score', 1.0)
            
            # 更新状态
            status.health_score = health_score
            status.metrics = health_report
            
            if health_score >= 0.9:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.7:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查连接监控器健康状态失败: {e}")
    
    async def _check_performance_optimizer_health(self) -> None:
        """检查性能优化器健康状态"""
        try:
            component_name = 'performance_optimizer'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取综合统计
            perf_stats = self.performance_optimizer.get_comprehensive_stats()
            
            # 计算健康分数
            cache_stats = perf_stats.get('cache_stats', {})
            hit_rate = cache_stats.get('hit_rate', 1.0)
            
            pool_stats = perf_stats.get('pool_stats', {})
            avg_wait_time = pool_stats.get('average_wait_time_ms', 0)
            
            health_score = hit_rate * (1.0 - min(0.5, avg_wait_time / 1000))
            
            # 更新状态
            status.health_score = health_score
            status.metrics = perf_stats
            
            if health_score >= 0.8:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.6:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查性能优化器健康状态失败: {e}")
    
    async def _check_fault_recovery_health(self) -> None:
        """检查故障恢复管理器健康状态"""
        try:
            component_name = 'fault_recovery_manager'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取系统健康报告
            health_report = self.fault_recovery_manager.get_system_health_report()
            
            # 计算健康分数
            health_ratio = health_report.get('overall_health_ratio', 1.0)
            active_incidents = health_report.get('active_incidents', 0)
            
            health_score = health_ratio * (1.0 - min(0.3, active_incidents * 0.1))
            
            # 更新状态
            status.health_score = health_score
            status.metrics = health_report
            
            if health_score >= 0.9:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.7:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查故障恢复管理器健康状态失败: {e}")
    
    async def _check_integration_manager_health(self) -> None:
        """检查集成管理器健康状态"""
        try:
            component_name = 'integration_manager'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取集成状态
            integration_status = self.integration_manager.get_integration_status()
            
            # 计算健康分数
            converter_stats = integration_status.get('converter_stats', {})
            success_rate = converter_stats.get('success_rate', 1.0)
            
            health_score = success_rate
            
            # 更新状态
            status.health_score = health_score
            status.metrics = integration_status
            
            if health_score >= 0.9:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.7:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查集成管理器健康状态失败: {e}")
    
    async def _check_realtime_adapter_health(self) -> None:
        """检查实时适配器健康状态"""
        try:
            component_name = 'realtime_adapter'
            if component_name not in self.component_status:
                return
                
            status = self.component_status[component_name]
            
            # 获取综合统计
            adapter_stats = self.realtime_adapter.get_comprehensive_stats()
            
            # 计算健康分数
            subscription_status = adapter_stats.get('subscription_status', {})
            active_subs = subscription_status.get('active_subscriptions', 0)
            total_subs = subscription_status.get('total_subscriptions', 1)
            
            health_score = active_subs / max(1, total_subs)
            
            # 更新状态
            status.health_score = health_score
            status.metrics = adapter_stats
            
            if health_score >= 0.9:
                status.status = SystemStatus.HEALTHY
            elif health_score >= 0.7:
                status.status = SystemStatus.DEGRADED
            else:
                status.status = SystemStatus.CRITICAL
                
        except Exception as e:
            logger.error(f"检查实时适配器健康状态失败: {e}")
    
    async def _metrics_collection_loop(self) -> None:
        """指标收集循环"""
        while self.is_running:
            try:
                await self._collect_system_metrics()
                self.monitoring_stats['total_metrics_collected'] += 1
                
                await asyncio.sleep(self.monitoring_config['metrics_collection_interval'])
                
            except Exception as e:
                logger.error(f"指标收集循环异常: {e}")
                await asyncio.sleep(10)
    
    async def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            current_time = time.time()
            
            # 创建系统指标
            metrics = SystemMetrics(timestamp=current_time)
            
            # 计算运行时间
            metrics.uptime_seconds = current_time - self.system_start_time
            
            # 统计组件状态
            metrics.component_count = len(self.component_status)
            for component in self.component_status.values():
                if component.status == SystemStatus.HEALTHY:
                    metrics.healthy_components += 1
                elif component.status == SystemStatus.DEGRADED:
                    metrics.degraded_components += 1
                elif component.status == SystemStatus.CRITICAL:
                    metrics.critical_components += 1
            
            # 计算整体健康分数
            if metrics.component_count > 0:
                metrics.overall_health_score = sum(
                    comp.health_score for comp in self.component_status.values()
                ) / metrics.component_count
            
            # 确定整体状态
            if metrics.overall_health_score >= 0.9:
                metrics.overall_status = SystemStatus.HEALTHY
            elif metrics.overall_health_score >= 0.7:
                metrics.overall_status = SystemStatus.DEGRADED
            elif metrics.overall_health_score >= 0.5:
                metrics.overall_status = SystemStatus.WARNING
            else:
                metrics.overall_status = SystemStatus.CRITICAL
            
            # 收集性能指标
            await self._collect_performance_metrics(metrics)
            
            # 收集数据指标
            await self._collect_data_metrics(metrics)
            
            # 收集连接指标
            await self._collect_connection_metrics(metrics)
            
            # 收集故障指标
            await self._collect_fault_metrics(metrics)
            
            # 保存指标历史
            self.metrics_history.append(metrics)
            
            # 更新监控统计
            self.monitoring_stats['monitoring_uptime'] = metrics.uptime_seconds
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    async def _collect_performance_metrics(self, metrics: SystemMetrics) -> None:
        """收集性能指标"""
        try:
            if self.performance_optimizer:
                perf_stats = self.performance_optimizer.get_comprehensive_stats()
                
                cache_stats = perf_stats.get('cache_stats', {})
                metrics.cache_hit_rate = cache_stats.get('hit_rate', 0.0)
                
                pool_stats = perf_stats.get('pool_stats', {})
                metrics.active_connections = pool_stats.get('current_active', 0)
                metrics.connection_pool_utilization = pool_stats.get('current_active', 0) / max(1, pool_stats.get('max_connections', 1))
                
                system_metrics = perf_stats.get('system_metrics', {})
                metrics.memory_usage_mb = system_metrics.get('memory_available_gb', 0) * 1024
                metrics.cpu_usage_percent = system_metrics.get('cpu_usage', 0)
                
        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")
    
    async def _collect_data_metrics(self, metrics: SystemMetrics) -> None:
        """收集数据指标"""
        try:
            if self.data_quality_engine:
                quality_summary = self.data_quality_engine.get_quality_summary()
                metrics.data_quality_score = quality_summary.get('average_quality_score', 1.0)
            
            if self.realtime_adapter:
                adapter_stats = self.realtime_adapter.get_comprehensive_stats()
                realtime_stats = adapter_stats.get('event_stats', {})
                metrics.data_throughput = realtime_stats.get('events_dispatched', 0)
                
        except Exception as e:
            logger.error(f"收集数据指标失败: {e}")
    
    async def _collect_connection_metrics(self, metrics: SystemMetrics) -> None:
        """收集连接指标"""
        try:
            if self.enhanced_client:
                connection_stats = self.enhanced_client.get_connection_stats()
                
                # 计算请求统计
                stats = connection_stats.get('stats', {})
                metrics.total_requests = stats.get('successful_connections', 0) + stats.get('failed_connections', 0)
                metrics.successful_requests = stats.get('successful_connections', 0)
                metrics.failed_requests = stats.get('failed_connections', 0)
                
                if metrics.total_requests > 0:
                    success_rate = metrics.successful_requests / metrics.total_requests
                else:
                    success_rate = 1.0
                    
                metrics.average_response_time_ms = connection_stats.get('average_latency', 0.0)
                
        except Exception as e:
            logger.error(f"收集连接指标失败: {e}")
    
    async def _collect_fault_metrics(self, metrics: SystemMetrics) -> None:
        """收集故障指标"""
        try:
            if self.fault_recovery_manager:
                health_report = self.fault_recovery_manager.get_system_health_report()
                metrics.active_incidents = health_report.get('active_incidents', 0)
                metrics.resolved_incidents_today = health_report.get('total_incidents_today', 0)
                
        except Exception as e:
            logger.error(f"收集故障指标失败: {e}")
    
    async def _alert_check_loop(self) -> None:
        """告警检查循环"""
        while self.is_running:
            try:
                await self._check_for_alerts()
                
                await asyncio.sleep(self.monitoring_config['alert_check_interval'])
                
            except Exception as e:
                logger.error(f"告警检查循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _check_for_alerts(self) -> None:
        """检查告警条件"""
        try:
            current_time = time.time()
            
            # 检查组件健康分数告警
            for component_name, component in self.component_status.items():
                if component.health_score < self.monitoring_config['health_score_critical']:
                    await self._create_alert(
                        AlertLevel.CRITICAL,
                        component_name,
                        "组件健康分数过低",
                        f"组件 {component_name} 健康分数: {component.health_score:.2f}",
                        {'health_score': component.health_score}
                    )
                elif component.health_score < self.monitoring_config['health_score_warning']:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        component_name,
                        "组件健康分数警告",
                        f"组件 {component_name} 健康分数: {component.health_score:.2f}",
                        {'health_score': component.health_score}
                    )
            
            # 检查响应时间告警
            if self.metrics_history:
                latest_metrics = self.metrics_history[-1]
                
                if latest_metrics.average_response_time_ms > self.monitoring_config['response_time_critical']:
                    await self._create_alert(
                        AlertLevel.CRITICAL,
                        "system",
                        "响应时间过长",
                        f"平均响应时间: {latest_metrics.average_response_time_ms:.1f}ms",
                        {'response_time_ms': latest_metrics.average_response_time_ms}
                    )
                elif latest_metrics.average_response_time_ms > self.monitoring_config['response_time_warning']:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        "system",
                        "响应时间警告",
                        f"平均响应时间: {latest_metrics.average_response_time_ms:.1f}ms",
                        {'response_time_ms': latest_metrics.average_response_time_ms}
                    )
                
                # 检查数据质量告警
                if latest_metrics.data_quality_score < self.monitoring_config['data_quality_critical']:
                    await self._create_alert(
                        AlertLevel.CRITICAL,
                        "data_quality",
                        "数据质量严重下降",
                        f"数据质量分数: {latest_metrics.data_quality_score:.2f}",
                        {'data_quality_score': latest_metrics.data_quality_score}
                    )
                elif latest_metrics.data_quality_score < self.monitoring_config['data_quality_warning']:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        "data_quality",
                        "数据质量警告",
                        f"数据质量分数: {latest_metrics.data_quality_score:.2f}",
                        {'data_quality_score': latest_metrics.data_quality_score}
                    )
                
                # 检查错误率告警
                if latest_metrics.total_requests > 0:
                    error_rate = latest_metrics.failed_requests / latest_metrics.total_requests
                    
                    if error_rate > self.monitoring_config['error_rate_critical']:
                        await self._create_alert(
                            AlertLevel.CRITICAL,
                            "system",
                            "错误率过高",
                            f"错误率: {error_rate:.1%}",
                            {'error_rate': error_rate}
                        )
                    elif error_rate > self.monitoring_config['error_rate_warning']:
                        await self._create_alert(
                            AlertLevel.WARNING,
                            "system",
                            "错误率警告",
                            f"错误率: {error_rate:.1%}",
                            {'error_rate': error_rate}
                        )
                
        except Exception as e:
            logger.error(f"检查告警条件失败: {e}")
    
    async def _create_alert(self, level: AlertLevel, component: str, title: str, 
                          message: str, metadata: Dict[str, Any]) -> None:
        """创建告警"""
        try:
            alert_id = f"{component}_{level.name}_{int(time.time())}"
            
            # 检查是否已存在相同类型的告警（防重复）
            existing_alerts = [
                alert for alert in self.active_alerts.values()
                if (alert.component == component and 
                    alert.level == level and 
                    alert.title == title and
                    not alert.resolved)
            ]
            
            if existing_alerts:
                # 更新现有告警的时间戳
                existing_alerts[0].timestamp = time.time()
                return
            
            # 创建新告警
            alert = SystemAlert(
                alert_id=alert_id,
                level=level,
                component=component,
                title=title,
                message=message,
                metadata=metadata
            )
            
            # 添加到活跃告警
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # 更新统计
            self.monitoring_stats['total_alerts_generated'] += 1
            
            # 记录日志
            log_level = {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.ERROR: logging.ERROR,
                AlertLevel.CRITICAL: logging.CRITICAL
            }.get(level, logging.INFO)
            
            logger.log(log_level, f"🚨 {level.name} 告警: {component} - {title}: {message}")
            
            # 通知回调
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"告警回调失败: {e}")
                    
        except Exception as e:
            logger.error(f"创建告警失败: {e}")
    
    async def _component_status_loop(self) -> None:
        """组件状态更新循环"""
        while self.is_running:
            try:
                await self._update_component_status()
                
                await asyncio.sleep(30)  # 每30秒更新一次
                
            except Exception as e:
                logger.error(f"组件状态更新循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _update_component_status(self) -> None:
        """更新组件状态"""
        try:
            current_time = time.time()
            timeout_threshold = self.monitoring_config['component_timeout']
            
            for component in self.component_status.values():
                # 检查组件是否超时
                if current_time - component.last_update > timeout_threshold:
                    component.status = SystemStatus.OFFLINE
                    component.health_score = 0.0
                    component.error_count += 1
                    
        except Exception as e:
            logger.error(f"更新组件状态失败: {e}")
    
    def add_alert_callback(self, callback: Callable[[SystemAlert], None]) -> None:
        """添加告警回调"""
        self.alert_callbacks.append(callback)
        logger.info(f"添加告警回调: {callback.__name__}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                logger.info(f"告警已确认: {alert_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"确认告警失败: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                del self.active_alerts[alert_id]
                logger.info(f"告警已解决: {alert_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False
    
    def get_system_dashboard(self) -> Dict[str, Any]:
        """获取系统仪表板数据"""
        try:
            current_time = time.time()
            
            # 最新指标
            latest_metrics = self.metrics_history[-1] if self.metrics_history else SystemMetrics()
            
            # 活跃告警按级别分组
            alerts_by_level = defaultdict(int)
            for alert in self.active_alerts.values():
                alerts_by_level[alert.level.name] += 1
            
            # 组件状态分布
            components_by_status = defaultdict(int)
            for component in self.component_status.values():
                components_by_status[component.status.name] += 1
            
            # 计算趋势（与1小时前对比）
            trends = self._calculate_trends()
            
            return {
                # 系统概览
                'system_overview': {
                    'status': latest_metrics.overall_status.name,
                    'health_score': latest_metrics.overall_health_score,
                    'uptime_seconds': latest_metrics.uptime_seconds,
                    'uptime_formatted': self._format_uptime(latest_metrics.uptime_seconds)
                },
                
                # 组件状态
                'component_summary': {
                    'total_components': latest_metrics.component_count,
                    'healthy': latest_metrics.healthy_components,
                    'degraded': latest_metrics.degraded_components,  
                    'critical': latest_metrics.critical_components,
                    'by_status': dict(components_by_status)
                },
                
                # 性能指标
                'performance_metrics': {
                    'total_requests': latest_metrics.total_requests,
                    'success_rate': (latest_metrics.successful_requests / max(1, latest_metrics.total_requests)),
                    'average_response_time_ms': latest_metrics.average_response_time_ms,
                    'requests_per_second': latest_metrics.requests_per_second,
                    'cache_hit_rate': latest_metrics.cache_hit_rate
                },
                
                # 数据指标
                'data_metrics': {
                    'data_quality_score': latest_metrics.data_quality_score,
                    'data_throughput': latest_metrics.data_throughput,
                    'active_connections': latest_metrics.active_connections,
                    'connection_pool_utilization': latest_metrics.connection_pool_utilization
                },
                
                # 故障指标
                'fault_metrics': {
                    'active_incidents': latest_metrics.active_incidents,
                    'resolved_incidents_today': latest_metrics.resolved_incidents_today,
                    'active_alerts': len(self.active_alerts),
                    'alerts_by_level': dict(alerts_by_level)
                },
                
                # 资源使用
                'resource_metrics': {
                    'memory_usage_mb': latest_metrics.memory_usage_mb,
                    'cpu_usage_percent': latest_metrics.cpu_usage_percent
                },
                
                # 趋势分析
                'trends': trends,
                
                # 最近告警
                'recent_alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'level': alert.level.name,
                        'component': alert.component,
                        'title': alert.title,
                        'message': alert.message,
                        'timestamp': alert.timestamp,
                        'acknowledged': alert.acknowledged
                    }
                    for alert in sorted(
                        self.active_alerts.values(),
                        key=lambda x: x.timestamp,
                        reverse=True
                    )[:10]
                ],
                
                # 监控统计
                'monitoring_stats': self.monitoring_stats,
                
                # 组件详细状态
                'component_details': {
                    name: {
                        'status': component.status.name,
                        'health_score': component.health_score,
                        'uptime_seconds': component.uptime_seconds,
                        'error_count': component.error_count,
                        'last_update': component.last_update
                    }
                    for name, component in self.component_status.items()
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统仪表板数据失败: {e}")
            return {}
    
    def _calculate_trends(self) -> Dict[str, float]:
        """计算趋势数据"""
        try:
            if len(self.metrics_history) < 2:
                return {}
            
            current = self.metrics_history[-1]
            
            # 找到1小时前的数据点
            one_hour_ago = current.timestamp - 3600
            historical = None
            
            for metrics in reversed(self.metrics_history):
                if metrics.timestamp <= one_hour_ago:
                    historical = metrics
                    break
            
            if not historical:
                return {}
            
            # 计算趋势
            trends = {}
            
            if historical.overall_health_score > 0:
                trends['health_score_trend'] = (
                    (current.overall_health_score - historical.overall_health_score) / 
                    historical.overall_health_score
                )
            
            if historical.average_response_time_ms > 0:
                trends['response_time_trend'] = (
                    (current.average_response_time_ms - historical.average_response_time_ms) / 
                    historical.average_response_time_ms
                )
            
            if historical.data_quality_score > 0:
                trends['data_quality_trend'] = (
                    (current.data_quality_score - historical.data_quality_score) / 
                    historical.data_quality_score
                )
            
            return trends
            
        except Exception as e:
            logger.error(f"计算趋势失败: {e}")
            return {}
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """格式化运行时间"""
        try:
            uptime_timedelta = timedelta(seconds=int(uptime_seconds))
            days = uptime_timedelta.days
            hours, remainder = divmod(uptime_timedelta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}天 {hours}小时 {minutes}分钟"
            elif hours > 0:
                return f"{hours}小时 {minutes}分钟"
            else:
                return f"{minutes}分钟 {seconds}秒"
                
        except Exception:
            return "未知"


# 便捷函数
def create_system_monitor() -> SystemMonitor:
    """创建系统监控管理器"""
    return SystemMonitor()


async def test_system_monitor():
    """测试系统监控"""
    monitor = create_system_monitor()
    
    try:
        # 模拟组件
        mock_components = {
            'enhanced_client': None,
            'data_quality_engine': None,
            'connection_monitor': None
        }
        
        # 初始化监控
        await monitor.initialize(mock_components)
        
        # 等待一段时间收集数据
        await asyncio.sleep(10)
        
        # 获取仪表板数据
        dashboard = monitor.get_system_dashboard()
        print(f"系统仪表板: {json.dumps(dashboard, indent=2, default=str)}")
        
    finally:
        await monitor.shutdown()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_system_monitor())