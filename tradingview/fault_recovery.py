#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView故障恢复和监控系统
实现故障检测、自动恢复、备用数据源切换和健康监控
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum, auto
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import traceback

from config.logging_config import get_logger

logger = get_logger(__name__)


class FaultType(Enum):
    """故障类型"""
    CONNECTION_LOST = auto()        # 连接丢失
    DATA_TIMEOUT = auto()          # 数据超时
    AUTHENTICATION_FAILED = auto()  # 认证失败
    RATE_LIMIT_EXCEEDED = auto()   # 频率限制
    DATA_CORRUPTION = auto()       # 数据损坏
    SYSTEM_OVERLOAD = auto()       # 系统过载
    NETWORK_ERROR = auto()         # 网络错误
    PROTOCOL_ERROR = auto()        # 协议错误
    UNKNOWN_ERROR = auto()         # 未知错误


class RecoveryStrategy(Enum):
    """恢复策略"""
    IMMEDIATE_RETRY = auto()       # 立即重试
    EXPONENTIAL_BACKOFF = auto()   # 指数退避
    CIRCUIT_BREAKER = auto()       # 断路器模式
    FALLBACK_SOURCE = auto()       # 切换备用源
    GRACEFUL_DEGRADATION = auto()  # 优雅降级
    MANUAL_INTERVENTION = auto()   # 人工干预


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = auto()               # 健康
    DEGRADED = auto()             # 降级
    UNHEALTHY = auto()            # 不健康
    CRITICAL = auto()             # 危险
    UNKNOWN = auto()              # 未知


@dataclass
class FaultIncident:
    """故障事件"""
    incident_id: str
    fault_type: FaultType
    component: str
    description: str
    occurred_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    severity: int = 1  # 1-5级，5最严重
    
    # 故障详情
    error_message: str = ""
    stack_trace: str = ""
    affected_symbols: List[str] = field(default_factory=list)
    
    # 恢复信息
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_attempts: int = 0
    is_resolved: bool = False
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def resolve(self) -> None:
        """标记故障已解决"""
        self.is_resolved = True
        self.resolved_at = time.time()
    
    def get_duration(self) -> float:
        """获取故障持续时间"""
        end_time = self.resolved_at or time.time()
        return end_time - self.occurred_at


@dataclass
class HealthMetrics:
    """健康指标"""
    component: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check_time: float = field(default_factory=time.time)
    
    # 性能指标
    response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    throughput: float = 0.0
    
    # 资源指标
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    connection_count: int = 0
    
    # 业务指标
    data_quality_score: float = 1.0
    data_freshness_seconds: float = 0.0
    
    # 趋势指标
    status_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_status(self, new_status: HealthStatus) -> None:
        """更新健康状态"""
        self.status_history.append({
            'status': self.status,
            'timestamp': time.time()
        })
        self.status = new_status
        self.last_check_time = time.time()


class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60,
                 success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        
        # 状态
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        # 统计
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过断路器调用函数"""
        self.total_calls += 1
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "HALF_OPEN"
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """异步版本的断路器调用"""
        self.total_calls += 1
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "HALF_OPEN"
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self) -> None:
        """成功回调"""
        self.total_successes += 1
        self.failure_count = 0
        
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """失败回调"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取断路器统计"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_calls': self.total_calls,
            'total_failures': self.total_failures,
            'total_successes': self.total_successes,
            'failure_rate': self.total_failures / max(1, self.total_calls),
            'last_failure_time': self.last_failure_time
        }


class FaultDetector:
    """故障检测器"""
    
    def __init__(self):
        self.detection_rules: List[Callable] = []
        self.fault_callbacks: List[Callable] = []
        self.detection_stats = {
            'total_checks': 0,
            'faults_detected': 0,
            'false_positives': 0
        }
        
    def add_detection_rule(self, rule: Callable[[Dict[str, Any]], Optional[FaultIncident]]) -> None:
        """添加故障检测规则"""
        self.detection_rules.append(rule)
        logger.info(f"添加故障检测规则: {rule.__name__}")
    
    def add_fault_callback(self, callback: Callable[[FaultIncident], None]) -> None:
        """添加故障回调"""
        self.fault_callbacks.append(callback)
        logger.info(f"添加故障回调: {callback.__name__}")
    
    async def check_for_faults(self, metrics: Dict[str, Any]) -> List[FaultIncident]:
        """检查故障"""
        self.detection_stats['total_checks'] += 1
        detected_faults = []
        
        try:
            for rule in self.detection_rules:
                try:
                    fault = rule(metrics)
                    if fault:
                        detected_faults.append(fault)
                        self.detection_stats['faults_detected'] += 1
                        
                        # 通知回调
                        for callback in self.fault_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(fault)
                                else:
                                    callback(fault)
                            except Exception as e:
                                logger.error(f"故障回调失败: {e}")
                                
                except Exception as e:
                    logger.error(f"故障检测规则失败: {e}")
            
            return detected_faults
            
        except Exception as e:
            logger.error(f"故障检测失败: {e}")
            return []
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计"""
        return self.detection_stats.copy()


class BackupDataSource:
    """备用数据源"""
    
    def __init__(self, name: str, priority: int, client_factory: Callable):
        self.name = name
        self.priority = priority
        self.client_factory = client_factory
        self.client: Optional[Any] = None
        self.is_active = False
        self.last_used_time = 0.0
        
        # 性能指标
        self.success_count = 0
        self.failure_count = 0
        self.average_latency_ms = 0.0
        
    async def activate(self) -> bool:
        """激活备用数据源"""
        try:
            if not self.client:
                self.client = await self.client_factory()
            
            if self.client:
                self.is_active = True
                self.last_used_time = time.time()
                logger.info(f"✅ 激活备用数据源: {self.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 激活备用数据源失败 {self.name}: {e}")
            return False
    
    async def deactivate(self) -> None:
        """停用备用数据源"""
        try:
            if self.client and hasattr(self.client, 'disconnect'):
                await self.client.disconnect()
            
            self.is_active = False
            self.client = None
            logger.info(f"停用备用数据源: {self.name}")
            
        except Exception as e:
            logger.error(f"停用备用数据源失败 {self.name}: {e}")
    
    def record_success(self, latency_ms: float) -> None:
        """记录成功"""
        self.success_count += 1
        self.last_used_time = time.time()
        
        # 更新平均延迟
        total_calls = self.success_count + self.failure_count
        if total_calls > 0:
            self.average_latency_ms = (
                (self.average_latency_ms * (total_calls - 1) + latency_ms) / total_calls
            )
    
    def record_failure(self) -> None:
        """记录失败"""
        self.failure_count += 1
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / max(1, total)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'name': self.name,
            'priority': self.priority,
            'is_active': self.is_active,
            'last_used_time': self.last_used_time,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.get_success_rate(),
            'average_latency_ms': self.average_latency_ms
        }


class FaultRecoveryManager:
    """故障恢复管理器"""
    
    def __init__(self):
        # 核心组件
        self.fault_detector = FaultDetector()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.backup_sources: Dict[str, List[BackupDataSource]] = defaultdict(list)
        
        # 故障管理
        self.active_incidents: Dict[str, FaultIncident] = {}
        self.resolved_incidents: deque = deque(maxlen=1000)
        
        # 健康监控
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.health_check_callbacks: Dict[str, Callable] = {}
        
        # 恢复策略配置
        self.recovery_config = {
            'max_retry_attempts': 3,
            'backoff_base_seconds': 2,
            'max_backoff_seconds': 300,
            'health_check_interval': 30,
            'circuit_breaker_enabled': True
        }
        
        # 运行状态
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.recovery_tasks: Set[asyncio.Task] = set()
        
        # 统计信息
        self.recovery_stats = {
            'total_incidents': 0,
            'resolved_incidents': 0,
            'active_incidents': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'backup_source_switches': 0
        }
        
        # 添加默认检测规则
        self._setup_default_detection_rules()
        
    def _setup_default_detection_rules(self) -> None:
        """设置默认检测规则"""
        
        def connection_timeout_rule(metrics: Dict[str, Any]) -> Optional[FaultIncident]:
            """连接超时检测"""
            response_time = metrics.get('response_time_ms', 0)
            if response_time > 5000:  # 5秒超时
                return FaultIncident(
                    incident_id=f"timeout_{int(time.time())}",
                    fault_type=FaultType.DATA_TIMEOUT,
                    component=metrics.get('component', 'unknown'),
                    description=f"响应时间过长: {response_time}ms",
                    severity=3
                )
            return None
        
        def success_rate_rule(metrics: Dict[str, Any]) -> Optional[FaultIncident]:
            """成功率检测"""
            success_rate = metrics.get('success_rate', 1.0)
            if success_rate < 0.8:  # 成功率低于80%
                return FaultIncident(
                    incident_id=f"low_success_{int(time.time())}",
                    fault_type=FaultType.SYSTEM_OVERLOAD,
                    component=metrics.get('component', 'unknown'),
                    description=f"成功率过低: {success_rate:.1%}",
                    severity=4
                )
            return None
        
        def data_quality_rule(metrics: Dict[str, Any]) -> Optional[FaultIncident]:
            """数据质量检测"""
            quality_score = metrics.get('data_quality_score', 1.0)
            if quality_score < 0.5:  # 质量分数低于50%
                return FaultIncident(
                    incident_id=f"poor_quality_{int(time.time())}",
                    fault_type=FaultType.DATA_CORRUPTION,
                    component=metrics.get('component', 'unknown'),
                    description=f"数据质量过低: {quality_score:.1%}",
                    severity=3
                )
            return None
        
        # 注册检测规则
        self.fault_detector.add_detection_rule(connection_timeout_rule)
        self.fault_detector.add_detection_rule(success_rate_rule)
        self.fault_detector.add_detection_rule(data_quality_rule)
        
        # 注册故障回调
        self.fault_detector.add_fault_callback(self._handle_detected_fault)
    
    async def start(self) -> None:
        """启动故障恢复管理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("✅ 故障恢复管理器已启动")
    
    async def stop(self) -> None:
        """停止故障恢复管理器"""
        self.is_running = False
        
        # 停止监控任务
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # 停止所有恢复任务
        for task in list(self.recovery_tasks):
            task.cancel()
        
        if self.recovery_tasks:
            await asyncio.gather(*self.recovery_tasks, return_exceptions=True)
        
        # 停用所有备用数据源
        for sources in self.backup_sources.values():
            for source in sources:
                await source.deactivate()
        
        logger.info("故障恢复管理器已停止")
    
    def register_component(self, component_name: str, health_check_callback: Callable) -> None:
        """注册组件健康检查"""
        self.health_check_callbacks[component_name] = health_check_callback
        self.health_metrics[component_name] = HealthMetrics(component=component_name)
        logger.info(f"注册组件健康检查: {component_name}")
    
    def add_backup_source(self, component: str, source: BackupDataSource) -> None:
        """添加备用数据源"""
        self.backup_sources[component].append(source)
        # 按优先级排序
        self.backup_sources[component].sort(key=lambda x: x.priority)
        logger.info(f"添加备用数据源: {component} -> {source.name} (优先级: {source.priority})")
    
    def get_circuit_breaker(self, component: str) -> CircuitBreaker:
        """获取组件的断路器"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreaker()
        return self.circuit_breakers[component]
    
    async def _monitoring_loop(self) -> None:
        """监控主循环"""
        while self.is_running:
            try:
                # 检查所有组件健康状态
                for component_name, health_callback in self.health_check_callbacks.items():
                    try:
                        # 执行健康检查
                        if asyncio.iscoroutinefunction(health_callback):
                            metrics = await health_callback()
                        else:
                            metrics = health_callback()
                        
                        # 更新健康指标
                        if component_name in self.health_metrics:
                            health_metric = self.health_metrics[component_name]
                            self._update_health_metrics(health_metric, metrics)
                        
                        # 检查故障
                        metrics['component'] = component_name
                        await self.fault_detector.check_for_faults(metrics)
                        
                    except Exception as e:
                        logger.error(f"健康检查失败 {component_name}: {e}")
                        
                        # 创建故障事件
                        incident = FaultIncident(
                            incident_id=f"health_check_fail_{component_name}_{int(time.time())}",
                            fault_type=FaultType.UNKNOWN_ERROR,
                            component=component_name,
                            description=f"健康检查失败: {str(e)}",
                            error_message=str(e),
                            stack_trace=traceback.format_exc(),
                            severity=2
                        )
                        
                        await self._handle_detected_fault(incident)
                
                await asyncio.sleep(self.recovery_config['health_check_interval'])
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(5)
    
    def _update_health_metrics(self, health_metric: HealthMetrics, metrics: Dict[str, Any]) -> None:
        """更新健康指标"""
        try:
            # 更新各项指标
            health_metric.response_time_ms = metrics.get('response_time_ms', 0.0)
            health_metric.success_rate = metrics.get('success_rate', 1.0)
            health_metric.error_count = metrics.get('error_count', 0)
            health_metric.throughput = metrics.get('throughput', 0.0)
            health_metric.memory_usage_mb = metrics.get('memory_usage_mb', 0.0)
            health_metric.cpu_usage_percent = metrics.get('cpu_usage_percent', 0.0)
            health_metric.connection_count = metrics.get('connection_count', 0)
            health_metric.data_quality_score = metrics.get('data_quality_score', 1.0)
            health_metric.data_freshness_seconds = metrics.get('data_freshness_seconds', 0.0)
            
            # 计算综合健康状态
            new_status = self._calculate_health_status(health_metric)
            health_metric.update_status(new_status)
            
        except Exception as e:
            logger.error(f"更新健康指标失败: {e}")
    
    def _calculate_health_status(self, metrics: HealthMetrics) -> HealthStatus:
        """计算健康状态"""
        try:
            # 检查关键指标
            if metrics.success_rate < 0.5:
                return HealthStatus.CRITICAL
            elif metrics.success_rate < 0.8:
                return HealthStatus.UNHEALTHY
            elif metrics.response_time_ms > 5000:
                return HealthStatus.DEGRADED
            elif metrics.data_quality_score < 0.7:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
                
        except Exception as e:
            logger.error(f"计算健康状态失败: {e}")
            return HealthStatus.UNKNOWN
    
    async def _handle_detected_fault(self, incident: FaultIncident) -> None:
        """处理检测到的故障"""
        try:
            logger.warning(f"🚨 检测到故障: {incident.fault_type.name} - {incident.description}")
            
            # 记录故障
            self.active_incidents[incident.incident_id] = incident
            self.recovery_stats['total_incidents'] += 1
            self.recovery_stats['active_incidents'] = len(self.active_incidents)
            
            # 确定恢复策略
            recovery_strategy = self._determine_recovery_strategy(incident)
            incident.recovery_strategy = recovery_strategy
            
            # 启动恢复任务
            recovery_task = asyncio.create_task(
                self._execute_recovery_strategy(incident)
            )
            self.recovery_tasks.add(recovery_task)
            
            # 清理完成的任务
            recovery_task.add_done_callback(self.recovery_tasks.discard)
            
        except Exception as e:
            logger.error(f"处理故障失败: {e}")
    
    def _determine_recovery_strategy(self, incident: FaultIncident) -> RecoveryStrategy:
        """确定恢复策略"""
        try:
            # 根据故障类型确定策略
            if incident.fault_type in [FaultType.CONNECTION_LOST, FaultType.NETWORK_ERROR]:
                return RecoveryStrategy.EXPONENTIAL_BACKOFF
            elif incident.fault_type == FaultType.RATE_LIMIT_EXCEEDED:
                return RecoveryStrategy.CIRCUIT_BREAKER
            elif incident.fault_type in [FaultType.DATA_TIMEOUT, FaultType.DATA_CORRUPTION]:
                return RecoveryStrategy.FALLBACK_SOURCE
            elif incident.severity >= 4:
                return RecoveryStrategy.MANUAL_INTERVENTION
            else:
                return RecoveryStrategy.IMMEDIATE_RETRY
                
        except Exception as e:
            logger.error(f"确定恢复策略失败: {e}")
            return RecoveryStrategy.IMMEDIATE_RETRY
    
    async def _execute_recovery_strategy(self, incident: FaultIncident) -> None:
        """执行恢复策略"""
        try:
            strategy = incident.recovery_strategy
            component = incident.component
            
            logger.info(f"执行恢复策略: {strategy.name} for {component}")
            
            if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                await self._immediate_retry_recovery(incident)
            elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                await self._exponential_backoff_recovery(incident)
            elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                await self._circuit_breaker_recovery(incident)
            elif strategy == RecoveryStrategy.FALLBACK_SOURCE:
                await self._fallback_source_recovery(incident)
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                await self._graceful_degradation_recovery(incident)
            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                await self._manual_intervention_recovery(incident)
                
        except Exception as e:
            logger.error(f"执行恢复策略失败: {e}")
            incident.recovery_attempts += 1
            self.recovery_stats['failed_recoveries'] += 1
    
    async def _immediate_retry_recovery(self, incident: FaultIncident) -> None:
        """立即重试恢复"""
        max_attempts = self.recovery_config['max_retry_attempts']
        
        for attempt in range(max_attempts):
            try:
                incident.recovery_attempts += 1
                
                # 执行重试逻辑
                component = incident.component
                if component in self.health_check_callbacks:
                    callback = self.health_check_callbacks[component]
                    
                    if asyncio.iscoroutinefunction(callback):
                        metrics = await callback()
                    else:
                        metrics = callback()
                    
                    # 检查是否恢复
                    if metrics.get('success_rate', 0) > 0.8:
                        incident.resolve()
                        self._mark_incident_resolved(incident)
                        logger.info(f"✅ 立即重试恢复成功: {incident.component}")
                        return
                
                # 短暂等待后重试
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"立即重试失败 (尝试 {attempt + 1}/{max_attempts}): {e}")
        
        # 所有重试都失败了
        self.recovery_stats['failed_recoveries'] += 1
        logger.error(f"❌ 立即重试恢复失败: {incident.component}")
    
    async def _exponential_backoff_recovery(self, incident: FaultIncident) -> None:
        """指数退避恢复"""
        max_attempts = self.recovery_config['max_retry_attempts']
        base_delay = self.recovery_config['backoff_base_seconds']
        max_delay = self.recovery_config['max_backoff_seconds']
        
        for attempt in range(max_attempts):
            try:
                incident.recovery_attempts += 1
                
                # 计算延迟时间
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.info(f"指数退避恢复 (尝试 {attempt + 1}/{max_attempts}): {delay}秒后重试")
                
                await asyncio.sleep(delay)
                
                # 执行恢复检查
                component = incident.component
                if component in self.health_check_callbacks:
                    callback = self.health_check_callbacks[component]
                    
                    if asyncio.iscoroutinefunction(callback):
                        metrics = await callback()
                    else:
                        metrics = callback()
                    
                    # 检查是否恢复
                    if metrics.get('success_rate', 0) > 0.8:
                        incident.resolve()
                        self._mark_incident_resolved(incident)
                        logger.info(f"✅ 指数退避恢复成功: {incident.component}")
                        return
                        
            except Exception as e:
                logger.error(f"指数退避恢复失败 (尝试 {attempt + 1}/{max_attempts}): {e}")
        
        # 所有重试都失败了
        self.recovery_stats['failed_recoveries'] += 1
        logger.error(f"❌ 指数退避恢复失败: {incident.component}")
    
    async def _fallback_source_recovery(self, incident: FaultIncident) -> None:
        """备用数据源恢复"""
        try:
            component = incident.component
            backup_sources = self.backup_sources.get(component, [])
            
            if not backup_sources:
                logger.warning(f"没有可用的备用数据源: {component}")
                self.recovery_stats['failed_recoveries'] += 1
                return
            
            # 尝试激活备用数据源
            for source in backup_sources:
                try:
                    logger.info(f"尝试激活备用数据源: {source.name}")
                    
                    if await source.activate():
                        incident.resolve()
                        self._mark_incident_resolved(incident)
                        self.recovery_stats['backup_source_switches'] += 1
                        logger.info(f"✅ 切换到备用数据源成功: {source.name}")
                        return
                        
                except Exception as e:
                    logger.error(f"激活备用数据源失败 {source.name}: {e}")
                    source.record_failure()
            
            # 所有备用数据源都失败了
            self.recovery_stats['failed_recoveries'] += 1
            logger.error(f"❌ 所有备用数据源都不可用: {component}")
            
        except Exception as e:
            logger.error(f"备用数据源恢复失败: {e}")
            self.recovery_stats['failed_recoveries'] += 1
    
    async def _circuit_breaker_recovery(self, incident: FaultIncident) -> None:
        """断路器恢复"""
        try:
            component = incident.component
            circuit_breaker = self.get_circuit_breaker(component)
            
            # 强制打开断路器
            circuit_breaker.state = "OPEN"
            circuit_breaker.last_failure_time = time.time()
            
            logger.info(f"断路器已打开: {component}")
            
            # 等待超时后尝试半开
            await asyncio.sleep(circuit_breaker.timeout_seconds)
            
            circuit_breaker.state = "HALF_OPEN"
            circuit_breaker.success_count = 0
            
            incident.resolve()
            self._mark_incident_resolved(incident)
            logger.info(f"✅ 断路器恢复: {component}")
            
        except Exception as e:
            logger.error(f"断路器恢复失败: {e}")
            self.recovery_stats['failed_recoveries'] += 1
    
    async def _graceful_degradation_recovery(self, incident: FaultIncident) -> None:
        """优雅降级恢复"""
        try:
            # 实现优雅降级逻辑
            # 例如：降低数据更新频率、减少功能等
            logger.info(f"启动优雅降级: {incident.component}")
            
            # 标记为已解决（虽然是降级状态）
            incident.resolve()
            self._mark_incident_resolved(incident)
            
        except Exception as e:
            logger.error(f"优雅降级失败: {e}")
            self.recovery_stats['failed_recoveries'] += 1
    
    async def _manual_intervention_recovery(self, incident: FaultIncident) -> None:
        """人工干预恢复"""
        try:
            # 发送告警通知
            logger.critical(f"🚨 需要人工干预: {incident.description}")
            logger.critical(f"组件: {incident.component}, 严重程度: {incident.severity}")
            logger.critical(f"故障ID: {incident.incident_id}")
            
            # 这里可以集成告警系统，如邮件、短信、Slack等
            # await self._send_alert_notification(incident)
            
        except Exception as e:
            logger.error(f"人工干预处理失败: {e}")
    
    def _mark_incident_resolved(self, incident: FaultIncident) -> None:
        """标记故障已解决"""
        try:
            if incident.incident_id in self.active_incidents:
                del self.active_incidents[incident.incident_id]
                self.resolved_incidents.append(incident)
                
                self.recovery_stats['resolved_incidents'] += 1
                self.recovery_stats['active_incidents'] = len(self.active_incidents)
                self.recovery_stats['successful_recoveries'] += 1
                
                logger.info(f"故障已解决: {incident.incident_id} (持续时间: {incident.get_duration():.1f}秒)")
                
        except Exception as e:
            logger.error(f"标记故障解决失败: {e}")
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """获取系统健康报告"""
        try:
            # 计算整体健康状态
            healthy_components = sum(1 for m in self.health_metrics.values() 
                                   if m.status == HealthStatus.HEALTHY)
            total_components = len(self.health_metrics)
            overall_health_ratio = healthy_components / max(1, total_components)
            
            # 确定整体健康状态
            if overall_health_ratio >= 0.9:
                overall_status = HealthStatus.HEALTHY
            elif overall_health_ratio >= 0.7:
                overall_status = HealthStatus.DEGRADED
            elif overall_health_ratio >= 0.5:
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.CRITICAL
            
            return {
                'overall_status': overall_status.name,
                'overall_health_ratio': overall_health_ratio,
                'total_components': total_components,
                'healthy_components': healthy_components,
                'active_incidents': len(self.active_incidents),
                'total_incidents_today': self._count_incidents_today(),
                'recovery_stats': self.recovery_stats,
                'component_health': {
                    component: {
                        'status': metrics.status.name,
                        'success_rate': metrics.success_rate,
                        'response_time_ms': metrics.response_time_ms,
                        'data_quality_score': metrics.data_quality_score,
                        'last_check_time': metrics.last_check_time
                    }
                    for component, metrics in self.health_metrics.items()
                },
                'circuit_breaker_stats': {
                    component: breaker.get_stats()
                    for component, breaker in self.circuit_breakers.items()
                },
                'backup_source_stats': {
                    component: [source.get_stats() for source in sources]
                    for component, sources in self.backup_sources.items()
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统健康报告失败: {e}")
            return {}
    
    def _count_incidents_today(self) -> int:
        """统计今天的故障数量"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_timestamp = today_start.timestamp()
            
            count = 0
            
            # 统计活跃故障
            for incident in self.active_incidents.values():
                if incident.occurred_at >= today_timestamp:
                    count += 1
            
            # 统计已解决故障
            for incident in self.resolved_incidents:
                if incident.occurred_at >= today_timestamp:
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"统计今日故障数量失败: {e}")
            return 0


# 便捷函数
def create_fault_recovery_manager() -> FaultRecoveryManager:
    """创建故障恢复管理器"""
    return FaultRecoveryManager()


async def test_fault_recovery():
    """测试故障恢复系统"""
    manager = create_fault_recovery_manager()
    
    try:
        # 启动管理器
        await manager.start()
        
        # 注册测试组件
        async def mock_health_check():
            return {
                'response_time_ms': 100,
                'success_rate': 0.95,
                'data_quality_score': 0.9,
                'error_count': 1
            }
        
        manager.register_component('test_component', mock_health_check)
        
        # 添加备用数据源
        async def mock_backup_client():
            return "mock_backup_client"
        
        backup_source = BackupDataSource(
            name='backup_test',
            priority=1,
            client_factory=mock_backup_client
        )
        
        manager.add_backup_source('test_component', backup_source)
        
        # 等待一段时间观察监控
        await asyncio.sleep(5)
        
        # 模拟故障
        fault_incident = FaultIncident(
            incident_id="test_fault_001",
            fault_type=FaultType.CONNECTION_LOST,
            component="test_component",
            description="模拟连接丢失故障",
            severity=3
        )
        
        await manager._handle_detected_fault(fault_incident)
        
        # 等待恢复完成
        await asyncio.sleep(10)
        
        # 获取健康报告
        health_report = manager.get_system_health_report()
        print(f"系统健康报告: {json.dumps(health_report, indent=2, default=str)}")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_fault_recovery())