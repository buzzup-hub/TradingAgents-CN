#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView增强数据源统一入口
整合所有增强功能，提供完整的专业级数据源服务
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
import logging

# 导入所有增强模块
from .enhanced_client import EnhancedTradingViewClient, ConnectionState
from .data_quality_monitor import DataQualityEngine, QualityLevel
from .connection_health import ConnectionHealthMonitor, HealthStatus
from .performance_optimizer import PerformanceOptimizer
from .fault_recovery import FaultRecoveryManager, BackupDataSource
from .trading_integration import TradingCoreIntegrationManager, TradingViewDataConverter, MarketDataPoint
from .realtime_adapter import AdvancedRealtimeAdapter, SubscriptionType
from .system_monitor import SystemMonitor, SystemStatus
from .integration_test import IntegrationTestSuite

from config.logging_config import get_logger

logger = get_logger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    INITIALIZING = auto()
    RUNNING = auto()
    DEGRADED = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class EnhancedTradingViewConfig:
    """增强TradingView配置"""
    # 连接配置
    auto_reconnect: bool = True
    health_check_interval: int = 30
    connection_timeout: float = 30.0
    
    # 性能配置
    enable_caching: bool = True
    cache_size: int = 10000
    enable_connection_pool: bool = True
    min_connections: int = 5
    max_connections: int = 50
    
    # 数据质量配置
    quality_threshold: float = 0.8
    enable_quality_monitoring: bool = True
    
    # 故障恢复配置
    enable_fault_recovery: bool = True
    max_retry_attempts: int = 3
    circuit_breaker_enabled: bool = True
    
    # 监控配置
    enable_system_monitoring: bool = True
    metrics_collection_interval: int = 60
    
    # 测试配置
    enable_integration_test: bool = False
    test_symbols: List[str] = None
    
    def __post_init__(self):
        if self.test_symbols is None:
            self.test_symbols = ['BTC/USDT', 'ETH/USDT', 'XAU/USD']


class EnhancedTradingViewService:
    """增强TradingView数据源服务"""
    
    def __init__(self, config: Optional[EnhancedTradingViewConfig] = None):
        self.config = config or EnhancedTradingViewConfig()
        self.status = ServiceStatus.INITIALIZING
        self.start_time = time.time()
        
        # 核心组件
        self.enhanced_client: Optional[EnhancedTradingViewClient] = None
        self.data_quality_engine: Optional[DataQualityEngine] = None
        self.connection_monitor: Optional[ConnectionHealthMonitor] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        self.fault_recovery_manager: Optional[FaultRecoveryManager] = None
        self.integration_manager: Optional[TradingCoreIntegrationManager] = None
        self.realtime_adapter: Optional[AdvancedRealtimeAdapter] = None
        self.system_monitor: Optional[SystemMonitor] = None
        
        # 服务状态
        self.initialization_errors: List[str] = []
        self.service_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'uptime_seconds': 0.0,
            'last_health_check': 0.0
        }
        
        # 回调函数
        self.data_callbacks: List[Callable[[MarketDataPoint], None]] = []
        self.status_callbacks: List[Callable[[ServiceStatus], None]] = []
        self.error_callbacks: List[Callable[[Exception], None]] = []
    
    async def initialize(self) -> bool:
        """
        初始化增强TradingView服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("🚀 开始初始化增强TradingView数据源服务...")
            self.status = ServiceStatus.INITIALIZING
            
            # 1. 初始化增强客户端
            await self._initialize_enhanced_client()
            
            # 2. 初始化数据质量引擎
            if self.config.enable_quality_monitoring:
                await self._initialize_data_quality_engine()
            
            # 3. 初始化连接健康监控
            await self._initialize_connection_monitor()
            
            # 4. 初始化性能优化器
            await self._initialize_performance_optimizer()
            
            # 5. 初始化故障恢复管理器
            if self.config.enable_fault_recovery:
                await self._initialize_fault_recovery_manager()
            
            # 6. 初始化集成管理器
            await self._initialize_integration_manager()
            
            # 7. 初始化实时适配器
            await self._initialize_realtime_adapter()
            
            # 8. 初始化系统监控
            if self.config.enable_system_monitoring:
                await self._initialize_system_monitor()
            
            # 9. 运行集成测试（如果启用）
            if self.config.enable_integration_test:
                await self._run_integration_test()
            
            # 10. 验证所有组件状态
            if not await self._validate_components():
                raise RuntimeError("组件验证失败")
            
            self.status = ServiceStatus.RUNNING
            self._notify_status_change(ServiceStatus.RUNNING)
            
            logger.info("✅ 增强TradingView数据源服务初始化成功")
            logger.info(f"🎯 启用功能: 数据质量监控={self.config.enable_quality_monitoring}, "
                       f"故障恢复={self.config.enable_fault_recovery}, "
                       f"系统监控={self.config.enable_system_monitoring}")
            
            return True
            
        except Exception as e:
            error_msg = f"增强TradingView服务初始化失败: {e}"
            logger.error(f"❌ {error_msg}")
            self.initialization_errors.append(error_msg)
            self.status = ServiceStatus.ERROR
            self._notify_error(e)
            return False
    
    async def _initialize_enhanced_client(self) -> None:
        """初始化增强客户端"""
        try:
            logger.info("初始化增强TradingView客户端...")
            self.enhanced_client = EnhancedTradingViewClient(
                auto_reconnect=self.config.auto_reconnect,
                health_check_interval=self.config.health_check_interval
            )
            
            # 注册连接状态回调
            self.enhanced_client.on_connection_state_change(self._on_connection_state_change)
            
            logger.info("✅ 增强TradingView客户端初始化成功")
            
        except Exception as e:
            error_msg = f"增强客户端初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_data_quality_engine(self) -> None:
        """初始化数据质量引擎"""
        try:
            logger.info("初始化数据质量引擎...")
            self.data_quality_engine = DataQualityEngine()
            logger.info("✅ 数据质量引擎初始化成功")
            
        except Exception as e:
            error_msg = f"数据质量引擎初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_connection_monitor(self) -> None:
        """初始化连接健康监控"""
        try:
            logger.info("初始化连接健康监控...")
            self.connection_monitor = ConnectionHealthMonitor(
                check_interval=self.config.health_check_interval
            )
            await self.connection_monitor.start_monitoring()
            logger.info("✅ 连接健康监控初始化成功")
            
        except Exception as e:
            error_msg = f"连接健康监控初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_performance_optimizer(self) -> None:
        """初始化性能优化器"""
        try:
            logger.info("初始化性能优化器...")
            self.performance_optimizer = PerformanceOptimizer()
            
            # 创建连接工厂（如果需要）
            connection_factory = None
            if self.config.enable_connection_pool:
                async def create_mock_connection():
                    # 这里应该实现真实的连接创建逻辑
                    return f"mock_connection_{time.time()}"
                connection_factory = create_mock_connection
            
            await self.performance_optimizer.initialize(connection_factory)
            logger.info("✅ 性能优化器初始化成功")
            
        except Exception as e:
            error_msg = f"性能优化器初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_fault_recovery_manager(self) -> None:
        """初始化故障恢复管理器"""
        try:
            logger.info("初始化故障恢复管理器...")
            self.fault_recovery_manager = FaultRecoveryManager()
            await self.fault_recovery_manager.start()
            
            # 注册组件健康检查
            if self.enhanced_client:
                async def client_health_check():
                    stats = self.enhanced_client.get_connection_stats()
                    return {
                        'response_time_ms': stats.get('average_latency', 0),
                        'success_rate': 0.95,  # 模拟值
                        'data_quality_score': 0.9  # 模拟值
                    }
                
                self.fault_recovery_manager.register_component('enhanced_client', client_health_check)
            
            logger.info("✅ 故障恢复管理器初始化成功")
            
        except Exception as e:
            error_msg = f"故障恢复管理器初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_integration_manager(self) -> None:
        """初始化集成管理器"""
        try:
            logger.info("初始化trading_core集成管理器...")
            self.integration_manager = TradingCoreIntegrationManager()
            await self.integration_manager.initialize_integration()
            logger.info("✅ trading_core集成管理器初始化成功")
            
        except Exception as e:
            error_msg = f"集成管理器初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_realtime_adapter(self) -> None:
        """初始化实时适配器"""
        try:
            logger.info("初始化实时数据适配器...")
            self.realtime_adapter = AdvancedRealtimeAdapter()
            await self.realtime_adapter.initialize()
            logger.info("✅ 实时数据适配器初始化成功")
            
        except Exception as e:
            error_msg = f"实时适配器初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _initialize_system_monitor(self) -> None:
        """初始化系统监控"""
        try:
            logger.info("初始化系统监控...")
            self.system_monitor = SystemMonitor()
            
            # 准备监控组件
            components = {}
            if self.enhanced_client:
                components['enhanced_client'] = self.enhanced_client
            if self.data_quality_engine:
                components['data_quality_engine'] = self.data_quality_engine
            if self.connection_monitor:
                components['connection_monitor'] = self.connection_monitor
            if self.performance_optimizer:
                components['performance_optimizer'] = self.performance_optimizer
            if self.fault_recovery_manager:
                components['fault_recovery_manager'] = self.fault_recovery_manager
            if self.integration_manager:
                components['integration_manager'] = self.integration_manager
            if self.realtime_adapter:
                components['realtime_adapter'] = self.realtime_adapter
            
            await self.system_monitor.initialize(components)
            
            # 注册告警回调
            self.system_monitor.add_alert_callback(self._on_system_alert)
            
            logger.info("✅ 系统监控初始化成功")
            
        except Exception as e:
            error_msg = f"系统监控初始化失败: {e}"
            logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            raise
    
    async def _run_integration_test(self) -> None:
        """运行集成测试"""
        try:
            logger.info("运行集成测试...")
            test_suite = IntegrationTestSuite()
            test_report = await test_suite.run_all_tests()
            
            summary = test_report.get('summary', {})
            success_rate = summary.get('success_rate', 0)
            
            if success_rate >= 0.8:
                logger.info(f"✅ 集成测试通过，成功率: {success_rate:.1%}")
            else:
                logger.warning(f"⚠️ 集成测试部分失败，成功率: {success_rate:.1%}")
                
        except Exception as e:
            logger.error(f"集成测试失败: {e}")
            # 集成测试失败不阻止服务启动
    
    async def _validate_components(self) -> bool:
        """验证所有组件状态"""
        try:
            validation_results = {}
            
            # 验证必需组件
            if self.enhanced_client:
                validation_results['enhanced_client'] = True
            else:
                validation_results['enhanced_client'] = False
                logger.error("增强客户端未初始化")
            
            if self.integration_manager:
                status = self.integration_manager.get_integration_status()
                validation_results['integration_manager'] = status.get('status') != 'ERROR'
            else:
                validation_results['integration_manager'] = False
                logger.error("集成管理器未初始化")
            
            # 验证可选组件
            if self.config.enable_quality_monitoring:
                validation_results['data_quality_engine'] = self.data_quality_engine is not None
            
            if self.config.enable_fault_recovery:
                validation_results['fault_recovery_manager'] = self.fault_recovery_manager is not None
            
            if self.config.enable_system_monitoring:
                validation_results['system_monitor'] = self.system_monitor is not None
            
            # 计算验证成功率
            total_checks = len(validation_results)
            passed_checks = sum(1 for result in validation_results.values() if result)
            validation_rate = passed_checks / total_checks if total_checks > 0 else 0
            
            logger.info(f"组件验证结果: {passed_checks}/{total_checks} 通过 ({validation_rate:.1%})")
            
            # 要求至少80%的组件验证通过
            return validation_rate >= 0.8
            
        except Exception as e:
            logger.error(f"组件验证失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭服务"""
        try:
            logger.info("关闭增强TradingView数据源服务...")
            self.status = ServiceStatus.STOPPED
            
            # 按相反顺序关闭组件
            if self.system_monitor:
                await self.system_monitor.shutdown()
            
            if self.realtime_adapter:
                await self.realtime_adapter.shutdown()
            
            if self.fault_recovery_manager:
                await self.fault_recovery_manager.stop()
            
            if self.performance_optimizer:
                await self.performance_optimizer.shutdown()
            
            if self.connection_monitor:
                await self.connection_monitor.stop_monitoring()
            
            if self.enhanced_client:
                await self.enhanced_client.disconnect()
            
            self._notify_status_change(ServiceStatus.STOPPED)
            logger.info("✅ 增强TradingView数据源服务已关闭")
            
        except Exception as e:
            logger.error(f"关闭服务失败: {e}")
            self._notify_error(e)
    
    # === 数据接口 ===
    
    async def get_market_data(self, symbol: str, timeframe: str = "15m", count: int = 100) -> List[MarketDataPoint]:
        """
        获取市场数据
        
        Args:
            symbol: 交易品种
            timeframe: 时间框架
            count: 数据数量
            
        Returns:
            List[MarketDataPoint]: 市场数据列表
        """
        try:
            self.service_metrics['total_requests'] += 1
            
            if not self.enhanced_client or self.status != ServiceStatus.RUNNING:
                raise RuntimeError("服务未就绪")
            
            # 转换符号格式（如果需要）
            tv_symbol = self._convert_symbol_format(symbol)
            
            # 从TradingView获取数据
            klines = await self.enhanced_client.get_klines(tv_symbol, timeframe, count)
            
            if not klines:
                self.service_metrics['failed_requests'] += 1
                return []
            
            # 转换为MarketDataPoint格式
            converter = TradingViewDataConverter()
            market_data_list = []
            
            for kline in klines:
                market_data = converter.convert_kline_to_market_data(kline, symbol, timeframe)
                if market_data:
                    # 数据质量评估
                    if self.data_quality_engine:
                        quality_metrics = await self.data_quality_engine.evaluate_data_quality(symbol, [kline])
                        market_data.quality_score = quality_metrics.overall_quality_score
                    
                    market_data_list.append(market_data)
            
            self.service_metrics['successful_requests'] += 1
            
            # 通知数据回调
            for market_data in market_data_list:
                for callback in self.data_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(market_data)
                        else:
                            callback(market_data)
                    except Exception as e:
                        logger.error(f"数据回调失败: {e}")
            
            return market_data_list
            
        except Exception as e:
            self.service_metrics['failed_requests'] += 1
            logger.error(f"获取市场数据失败 {symbol}: {e}")
            self._notify_error(e)
            return []
    
    async def subscribe_realtime_data(self, symbol: str, timeframe: str = "15m", 
                                    callback: Callable[[MarketDataPoint], None] = None) -> bool:
        """
        订阅实时数据
        
        Args:
            symbol: 交易品种
            timeframe: 时间框架
            callback: 数据回调函数
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.realtime_adapter or self.status != ServiceStatus.RUNNING:
                raise RuntimeError("实时适配器未就绪")
            
            # 转换时间框架
            subscription_type = self._convert_timeframe_to_subscription_type(timeframe)
            
            # 内部数据处理回调
            async def internal_callback(symbol: str, data: Dict[str, Any]):
                try:
                    # 转换数据格式
                    converter = TradingViewDataConverter()
                    market_data = converter.convert_kline_to_market_data(data, symbol, timeframe)
                    
                    if market_data:
                        # 数据质量评估
                        if self.data_quality_engine:
                            quality_metrics = await self.data_quality_engine.evaluate_data_quality(symbol, [data])
                            market_data.quality_score = quality_metrics.overall_quality_score
                        
                        market_data.is_realtime = True
                        
                        # 调用用户回调
                        if callback:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(market_data)
                            else:
                                callback(market_data)
                        
                        # 调用注册的数据回调
                        for registered_callback in self.data_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(registered_callback):
                                    await registered_callback(market_data)
                                else:
                                    registered_callback(market_data)
                            except Exception as e:
                                logger.error(f"注册数据回调失败: {e}")
                                
                except Exception as e:
                    logger.error(f"实时数据处理失败: {e}")
            
            # 订阅实时数据
            success = await self.realtime_adapter.subscribe_symbol_data(
                symbol, subscription_type, internal_callback
            )
            
            if success:
                logger.info(f"✅ 订阅实时数据成功: {symbol} {timeframe}")
            else:
                logger.error(f"❌ 订阅实时数据失败: {symbol} {timeframe}")
            
            return success
            
        except Exception as e:
            logger.error(f"订阅实时数据失败 {symbol}: {e}")
            self._notify_error(e)
            return False
    
    async def unsubscribe_realtime_data(self, symbol: str, timeframe: str = "15m") -> bool:
        """
        取消订阅实时数据
        
        Args:
            symbol: 交易品种
            timeframe: 时间框架
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            if not self.realtime_adapter:
                return False
            
            subscription_type = self._convert_timeframe_to_subscription_type(timeframe)
            success = await self.realtime_adapter.unsubscribe_symbol_data(symbol, subscription_type)
            
            if success:
                logger.info(f"✅ 取消订阅成功: {symbol} {timeframe}")
            
            return success
            
        except Exception as e:
            logger.error(f"取消订阅失败 {symbol}: {e}")
            return False
    
    # === 监控和状态接口 ===
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            uptime = time.time() - self.start_time
            self.service_metrics['uptime_seconds'] = uptime
            
            status_info = {
                'status': self.status.name,
                'uptime_seconds': uptime,
                'uptime_formatted': self._format_uptime(uptime),
                'start_time': self.start_time,
                'metrics': self.service_metrics.copy(),
                'initialization_errors': self.initialization_errors.copy()
            }
            
            # 添加组件状态
            if self.system_monitor:
                dashboard = self.system_monitor.get_system_dashboard()
                status_info['system_dashboard'] = dashboard
            
            # 添加健康检查信息
            if self.connection_monitor:
                health_report = self.connection_monitor.get_health_report()
                status_info['connection_health'] = health_report
            
            # 添加性能信息
            if self.performance_optimizer:
                perf_stats = self.performance_optimizer.get_comprehensive_stats()
                status_info['performance_stats'] = perf_stats
            
            return status_info
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {e}")
            return {'error': str(e)}
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告"""
        try:
            if not self.data_quality_engine:
                return {'error': '数据质量引擎未启用'}
            
            return {
                'quality_summary': self.data_quality_engine.get_quality_summary(),
                'anomaly_report': self.data_quality_engine.get_anomaly_report()
            }
            
        except Exception as e:
            logger.error(f"获取数据质量报告失败: {e}")
            return {'error': str(e)}
    
    def get_fault_recovery_report(self) -> Dict[str, Any]:
        """获取故障恢复报告"""
        try:
            if not self.fault_recovery_manager:
                return {'error': '故障恢复管理器未启用'}
            
            return self.fault_recovery_manager.get_system_health_report()
            
        except Exception as e:
            logger.error(f"获取故障恢复报告失败: {e}")
            return {'error': str(e)}
    
    # === 回调管理 ===
    
    def add_data_callback(self, callback: Callable[[MarketDataPoint], None]) -> None:
        """添加数据回调"""
        self.data_callbacks.append(callback)
        logger.info(f"添加数据回调: {callback.__name__}")
    
    def add_status_callback(self, callback: Callable[[ServiceStatus], None]) -> None:
        """添加状态回调"""
        self.status_callbacks.append(callback)
        logger.info(f"添加状态回调: {callback.__name__}")
    
    def add_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """添加错误回调"""
        self.error_callbacks.append(callback)
        logger.info(f"添加错误回调: {callback.__name__}")
    
    # === 内部工具方法 ===
    
    def _convert_symbol_format(self, symbol: str) -> str:
        """转换符号格式为TradingView格式"""
        if "/" in symbol:
            base, quote = symbol.split("/")
            return f"BINANCE:{base}{quote}"
        return symbol
    
    def _convert_timeframe_to_subscription_type(self, timeframe: str) -> SubscriptionType:
        """转换时间框架为订阅类型"""
        mapping = {
            "1m": SubscriptionType.KLINE_1M,
            "5m": SubscriptionType.KLINE_5M,
            "15m": SubscriptionType.KLINE_15M,
            "1h": SubscriptionType.KLINE_1H,
            "1d": SubscriptionType.KLINE_1D
        }
        return mapping.get(timeframe, SubscriptionType.KLINE_15M)
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """格式化运行时间"""
        try:
            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{hours}小时{minutes}分钟"
            elif minutes > 0:
                return f"{minutes}分钟{seconds}秒"
            else:
                return f"{seconds}秒"
        except:
            return "未知"
    
    def _on_connection_state_change(self, state: ConnectionState) -> None:
        """连接状态变更回调"""
        logger.info(f"连接状态变更: {state.value}")
        
        if state == ConnectionState.CONNECTED:
            if self.status == ServiceStatus.DEGRADED:
                self.status = ServiceStatus.RUNNING
                self._notify_status_change(ServiceStatus.RUNNING)
        elif state in [ConnectionState.DISCONNECTED, ConnectionState.FAILED]:
            if self.status == ServiceStatus.RUNNING:
                self.status = ServiceStatus.DEGRADED
                self._notify_status_change(ServiceStatus.DEGRADED)
    
    async def _on_system_alert(self, alert) -> None:
        """系统告警回调"""
        logger.warning(f"系统告警: {alert.level.name} - {alert.title}: {alert.message}")
        
        # 根据告警级别调整服务状态
        if alert.level.name == 'CRITICAL' and self.status == ServiceStatus.RUNNING:
            self.status = ServiceStatus.DEGRADED
            self._notify_status_change(ServiceStatus.DEGRADED)
    
    def _notify_status_change(self, new_status: ServiceStatus) -> None:
        """通知状态变更"""
        for callback in self.status_callbacks:
            try:
                callback(new_status)
            except Exception as e:
                logger.error(f"状态回调失败: {e}")
    
    def _notify_error(self, error: Exception) -> None:
        """通知错误"""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"错误回调失败: {e}")


# 便捷函数和工厂方法

def create_enhanced_tradingview_service(config: Optional[EnhancedTradingViewConfig] = None) -> EnhancedTradingViewService:
    """创建增强TradingView服务"""
    return EnhancedTradingViewService(config)


async def create_and_start_service(config: Optional[EnhancedTradingViewConfig] = None) -> EnhancedTradingViewService:
    """创建并启动增强TradingView服务"""
    service = create_enhanced_tradingview_service(config)
    
    success = await service.initialize()
    if not success:
        raise RuntimeError("服务初始化失败")
    
    return service


# 示例使用
async def example_usage():
    """使用示例"""
    try:
        # 1. 创建配置
        config = EnhancedTradingViewConfig(
            enable_quality_monitoring=True,
            enable_fault_recovery=True,
            enable_system_monitoring=True,
            enable_integration_test=True,
            cache_size=5000
        )
        
        # 2. 创建并启动服务
        service = await create_and_start_service(config)
        
        # 3. 注册回调
        def on_data_received(market_data: MarketDataPoint):
            print(f"收到数据: {market_data.symbol} {market_data.close}")
        
        def on_status_change(status: ServiceStatus):
            print(f"状态变更: {status.name}")
        
        service.add_data_callback(on_data_received)
        service.add_status_callback(on_status_change)
        
        # 4. 获取历史数据
        print("获取历史数据...")
        market_data = await service.get_market_data("BTC/USDT", "15m", 100)
        print(f"获取到 {len(market_data)} 条历史数据")
        
        # 5. 订阅实时数据
        print("订阅实时数据...")
        success = await service.subscribe_realtime_data("BTC/USDT", "15m")
        if success:
            print("✅ 实时数据订阅成功")
        
        # 6. 运行一段时间
        print("运行30秒，观察数据...")
        await asyncio.sleep(30)
        
        # 7. 获取服务状态
        status = service.get_service_status()
        print(f"服务状态: {json.dumps(status, indent=2, default=str)}")
        
        # 8. 获取数据质量报告
        quality_report = service.get_data_quality_report()
        print(f"数据质量报告: {json.dumps(quality_report, indent=2, default=str)}")
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
    finally:
        # 9. 关闭服务
        if 'service' in locals():
            await service.shutdown()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())