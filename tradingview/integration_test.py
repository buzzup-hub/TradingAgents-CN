#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView数据源模块完整集成测试套件
验证所有增强功能的集成和性能表现
"""

import asyncio
import time
import json
import random
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
import logging
import traceback

# 导入所有增强模块
from .enhanced_client import EnhancedTradingViewClient, ConnectionState
from .data_quality_monitor import DataQualityEngine, QualityLevel
from .connection_health import ConnectionHealthMonitor, HealthStatus
from .performance_optimizer import PerformanceOptimizer, IntelligentCache, ConnectionPool
from .fault_recovery import FaultRecoveryManager, FaultType, RecoveryStrategy, BackupDataSource
from .trading_integration import TradingCoreIntegrationManager, TradingViewDataConverter
from .realtime_adapter import AdvancedRealtimeAdapter, SubscriptionType
from .system_monitor import SystemMonitor, SystemStatus, AlertLevel

from config.logging_config import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """测试状态"""
    PENDING = auto()
    RUNNING = auto()
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()


class TestCategory(Enum):
    """测试分类"""
    UNIT = auto()           # 单元测试
    INTEGRATION = auto()    # 集成测试
    PERFORMANCE = auto()    # 性能测试
    STRESS = auto()         # 压力测试
    FAULT = auto()          # 故障测试


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    category: TestCategory
    status: TestStatus
    duration_ms: float
    error_message: str = ""
    details: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.details is None:
            self.details = {}


class IntegrationTestSuite:
    """集成测试套件"""
    
    def __init__(self):
        # 测试组件
        self.enhanced_client: Optional[EnhancedTradingViewClient] = None
        self.data_quality_engine: Optional[DataQualityEngine] = None
        self.connection_monitor: Optional[ConnectionHealthMonitor] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        self.fault_recovery_manager: Optional[FaultRecoveryManager] = None
        self.integration_manager: Optional[TradingCoreIntegrationManager] = None
        self.realtime_adapter: Optional[AdvancedRealtimeAdapter] = None
        self.system_monitor: Optional[SystemMonitor] = None
        
        # 测试结果
        self.test_results: List[TestResult] = []
        self.test_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,  
            'skipped_tests': 0,
            'total_duration_ms': 0.0
        }
        
        # 测试配置
        self.test_config = {
            'timeout_seconds': 30,
            'max_retry_attempts': 3,
            'test_symbols': ['BTC/USDT', 'ETH/USDT', 'XAU/USD'],
            'stress_test_duration': 60,
            'performance_threshold_ms': 1000,
            'quality_threshold': 0.8,
            'health_threshold': 0.8
        }
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        try:
            logger.info("🚀 开始运行完整集成测试套件...")
            start_time = time.time()
            
            # 1. 初始化测试环境
            await self._setup_test_environment()
            
            # 2. 运行单元测试
            await self._run_unit_tests()
            
            # 3. 运行集成测试
            await self._run_integration_tests()
            
            # 4. 运行性能测试
            await self._run_performance_tests()
            
            # 5. 运行故障测试
            await self._run_fault_tests()
            
            # 6. 运行压力测试
            await self._run_stress_tests()
            
            # 7. 清理测试环境
            await self._cleanup_test_environment()
            
            # 8. 生成测试报告
            total_duration = (time.time() - start_time) * 1000
            self.test_stats['total_duration_ms'] = total_duration
            
            test_report = self._generate_test_report()
            
            logger.info(f"✅ 集成测试完成，总耗时: {total_duration:.1f}ms")
            return test_report
            
        except Exception as e:
            logger.error(f"❌ 集成测试失败: {e}")
            logger.error(traceback.format_exc())
            return {'error': str(e), 'traceback': traceback.format_exc()}
    
    async def _setup_test_environment(self) -> None:
        """设置测试环境"""
        try:
            logger.info("设置测试环境...")
            
            # 初始化增强客户端
            self.enhanced_client = EnhancedTradingViewClient()
            
            # 初始化数据质量引擎
            self.data_quality_engine = DataQualityEngine()
            
            # 初始化连接健康监控
            self.connection_monitor = ConnectionHealthMonitor()
            await self.connection_monitor.start_monitoring()
            
            # 初始化性能优化器
            self.performance_optimizer = PerformanceOptimizer()
            await self.performance_optimizer.initialize()
            
            # 初始化故障恢复管理器
            self.fault_recovery_manager = FaultRecoveryManager()
            await self.fault_recovery_manager.start()
            
            # 初始化集成管理器
            self.integration_manager = TradingCoreIntegrationManager()
            await self.integration_manager.initialize_integration()
            
            # 初始化实时适配器
            self.realtime_adapter = AdvancedRealtimeAdapter()
            await self.realtime_adapter.initialize()
            
            # 初始化系统监控
            self.system_monitor = SystemMonitor()
            components = {
                'enhanced_client': self.enhanced_client,
                'data_quality_engine': self.data_quality_engine,
                'connection_monitor': self.connection_monitor,
                'performance_optimizer': self.performance_optimizer,
                'fault_recovery_manager': self.fault_recovery_manager,
                'integration_manager': self.integration_manager,
                'realtime_adapter': self.realtime_adapter
            }
            await self.system_monitor.initialize(components)
            
            logger.info("✅ 测试环境设置完成")
            
        except Exception as e:
            logger.error(f"❌ 测试环境设置失败: {e}")
            raise
    
    async def _cleanup_test_environment(self) -> None:
        """清理测试环境"""
        try:
            logger.info("清理测试环境...")
            
            # 关闭所有组件
            if self.system_monitor:
                await self.system_monitor.shutdown()
            
            if self.realtime_adapter:
                await self.realtime_adapter.shutdown()
            
            if self.integration_manager:
                # integration_manager 没有 shutdown 方法，跳过
                pass
            
            if self.fault_recovery_manager:
                await self.fault_recovery_manager.stop()
            
            if self.performance_optimizer:
                await self.performance_optimizer.shutdown()
            
            if self.connection_monitor:
                await self.connection_monitor.stop_monitoring()
            
            if self.enhanced_client:
                await self.enhanced_client.disconnect()
            
            logger.info("✅ 测试环境清理完成")
            
        except Exception as e:
            logger.error(f"⚠️ 测试环境清理失败: {e}")
    
    async def _run_unit_tests(self) -> None:
        """运行单元测试"""
        logger.info("🧪 运行单元测试...")
        
        # 测试数据转换器
        await self._test_data_converter()
        
        # 测试缓存系统
        await self._test_intelligent_cache()
        
        # 测试连接池
        await self._test_connection_pool()
        
        # 测试断路器
        await self._test_circuit_breaker()
        
        # 测试数据质量评估
        await self._test_data_quality_evaluation()
    
    async def _test_data_converter(self) -> None:
        """测试数据转换器"""
        test_name = "数据转换器测试"
        start_time = time.perf_counter()
        
        try:
            converter = TradingViewDataConverter()
            
            # 测试正常数据转换
            tv_data = {
                'time': time.time(),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49500.0,
                'close': 50500.0,
                'volume': 1000.0
            }
            
            market_data = converter.convert_kline_to_market_data(tv_data, "BTC/USDT")
            assert market_data is not None, "正常数据转换失败"
            assert market_data.symbol == "BTC/USDT", "符号转换错误"
            assert market_data.close == 50500.0, "价格转换错误"
            
            # 测试异常数据处理
            invalid_data = {'invalid': 'data'}
            result = converter.convert_kline_to_market_data(invalid_data, "BTC/USDT")
            assert result is None, "异常数据应该返回None"
            
            # 测试转换统计
            stats = converter.get_conversion_stats()
            assert 'success_rate' in stats, "缺少转换统计"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_intelligent_cache(self) -> None:
        """测试智能缓存"""
        test_name = "智能缓存测试"
        start_time = time.perf_counter()
        
        try:
            cache = IntelligentCache(max_size=100)
            await cache.start()
            
            try:
                # 测试基本缓存操作
                test_key = "test_key"
                test_value = {"data": "test_value"}
                
                # 测试设置和获取
                result = await cache.put(test_key, test_value)
                assert result is True, "缓存设置失败"
                
                cached_value = cache.get(test_key)
                assert cached_value is not None, "缓存获取失败"
                assert cached_value["data"] == "test_value", "缓存值不匹配"
                
                # 测试缓存统计
                stats = cache.get_cache_stats()
                assert stats['hits'] > 0, "缓存命中统计错误"
                assert stats['entry_count'] > 0, "缓存条目统计错误"
                
                # 测试缓存清理
                cache.clear()
                assert cache.get(test_key) is None, "缓存清理失败"
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_test_result(test_name, TestCategory.UNIT, TestStatus.PASSED, duration_ms)
                
            finally:
                await cache.stop()
                
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_connection_pool(self) -> None:
        """测试连接池"""
        test_name = "连接池测试"
        start_time = time.perf_counter()
        
        try:
            # 模拟连接工厂
            async def mock_connection_factory():
                await asyncio.sleep(0.01)  # 模拟连接创建时间
                return f"mock_connection_{time.time()}"
            
            pool = ConnectionPool(min_connections=2, max_connections=10)
            await pool.initialize(mock_connection_factory)
            
            try:
                # 测试获取连接
                connection = await pool.get_connection()
                assert connection is not None, "获取连接失败"
                
                # 测试归还连接
                result = await pool.return_connection(connection)
                assert result is True, "归还连接失败"
                
                # 测试连接池统计
                stats = pool.get_pool_stats()
                assert 'current_active' in stats, "缺少连接池统计"
                assert 'total_created' in stats, "缺少连接创建统计"
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_test_result(test_name, TestCategory.UNIT, TestStatus.PASSED, duration_ms)
                
            finally:
                await pool.shutdown()
                
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_circuit_breaker(self) -> None:
        """测试断路器"""
        test_name = "断路器测试"
        start_time = time.perf_counter()
        
        try:
            from .fault_recovery import CircuitBreaker
            
            circuit_breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=1)
            
            # 测试正常调用
            def success_func():
                return "success"
            
            result = circuit_breaker.call(success_func)
            assert result == "success", "正常调用失败"
            
            # 测试失败调用
            def failure_func():
                raise Exception("test failure")
            
            # 触发断路器打开
            for _ in range(4):
                try:
                    circuit_breaker.call(failure_func)
                except:
                    pass
            
            # 断路器应该已打开
            assert circuit_breaker.state == "OPEN", "断路器未打开"
            
            # 测试断路器统计
            stats = circuit_breaker.get_stats()
            assert stats['total_failures'] >= 3, "失败统计错误"
            assert stats['state'] == "OPEN", "断路器状态错误"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_data_quality_evaluation(self) -> None:
        """测试数据质量评估"""
        test_name = "数据质量评估测试"
        start_time = time.perf_counter()
        
        try:
            engine = self.data_quality_engine
            
            # 测试高质量数据
            good_data = [{
                'time': time.time(),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49500.0,
                'close': 50500.0,
                'volume': 1000.0
            }]
            
            metrics = await engine.evaluate_data_quality("BTC/USDT", good_data)
            assert metrics.overall_quality_score > 0.8, f"高质量数据评分过低: {metrics.overall_quality_score}"
            assert metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD], "质量等级错误"
            
            # 测试低质量数据
            bad_data = [{
                'time': time.time(),
                'open': -1.0,  # 负价格
                'high': 0.0,   # 零价格
                'low': 100.0,  # 逻辑错误的价格关系
                'close': 50.0
            }]
            
            metrics = await engine.evaluate_data_quality("BTC/USDT", bad_data)
            assert metrics.overall_quality_score < 0.5, f"低质量数据评分过高: {metrics.overall_quality_score}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.UNIT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _run_integration_tests(self) -> None:
        """运行集成测试"""
        logger.info("🔗 运行集成测试...")
        
        # 测试端到端数据流
        await self._test_end_to_end_data_flow()
        
        # 测试组件间通信
        await self._test_component_communication()
        
        # 测试系统监控集成
        await self._test_system_monitoring_integration()
        
        # 测试配置管理集成
        await self._test_configuration_integration()
    
    async def _test_end_to_end_data_flow(self) -> None:
        """测试端到端数据流"""
        test_name = "端到端数据流测试"
        start_time = time.perf_counter()
        
        try:
            # 模拟完整的数据流：TradingView -> 数据质量 -> 转换 -> 实时适配
            
            # 1. 模拟TradingView数据
            tv_data = {
                'time': time.time(),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49500.0,
                'close': 50500.0,
                'volume': 1000.0
            }
            
            # 2. 数据质量评估
            quality_metrics = await self.data_quality_engine.evaluate_data_quality("BTC/USDT", [tv_data])
            assert quality_metrics.overall_quality_score > 0.7, "数据质量评估失败"
            
            # 3. 数据格式转换
            converter = TradingViewDataConverter()
            market_data = converter.convert_kline_to_market_data(tv_data, "BTC/USDT")
            assert market_data is not None, "数据转换失败"
            
            # 4. 实时适配器处理
            success = await self.realtime_adapter.process_realtime_data(
                "BTC/USDT", tv_data, SubscriptionType.KLINE_15M
            )
            assert success is True, "实时适配器处理失败"
            
            # 5. 验证数据完整性
            assert market_data.symbol == "BTC/USDT", "符号不匹配"
            assert market_data.close == 50500.0, "价格不匹配"
            assert market_data.quality_score > 0.7, "质量分数过低"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_component_communication(self) -> None:
        """测试组件间通信"""
        test_name = "组件间通信测试"
        start_time = time.perf_counter()
        
        try:
            # 测试故障恢复管理器与其他组件的通信
            
            # 1. 注册组件健康检查
            async def mock_health_check():
                return {
                    'response_time_ms': 100,
                    'success_rate': 0.95,
                    'data_quality_score': 0.9
                }
            
            self.fault_recovery_manager.register_component('test_component', mock_health_check)
            
            # 2. 等待健康检查执行
            await asyncio.sleep(2)
            
            # 3. 验证健康报告
            health_report = self.fault_recovery_manager.get_system_health_report()
            assert 'component_health' in health_report, "缺少组件健康信息"
            
            # 4. 测试系统监控数据收集
            dashboard = self.system_monitor.get_system_dashboard()
            assert 'system_overview' in dashboard, "缺少系统概览"
            assert 'component_summary' in dashboard, "缺少组件摘要"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_system_monitoring_integration(self) -> None:
        """测试系统监控集成"""
        test_name = "系统监控集成测试"
        start_time = time.perf_counter()
        
        try:
            # 等待监控收集数据
            await asyncio.sleep(3)
            
            # 获取仪表板数据
            dashboard = self.system_monitor.get_system_dashboard()
            
            # 验证基本结构
            required_sections = [
                'system_overview', 'component_summary', 'performance_metrics',
                'data_metrics', 'fault_metrics', 'monitoring_stats'
            ]
            
            for section in required_sections:
                assert section in dashboard, f"缺少仪表板部分: {section}"
            
            # 验证系统概览
            system_overview = dashboard['system_overview']
            assert 'status' in system_overview, "缺少系统状态"
            assert 'health_score' in system_overview, "缺少健康分数"
            assert 'uptime_seconds' in system_overview, "缺少运行时间"
            
            # 验证组件摘要
            component_summary = dashboard['component_summary']
            assert component_summary['total_components'] > 0, "组件数量为0"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_configuration_integration(self) -> None:
        """测试配置管理集成"""
        test_name = "配置管理集成测试"
        start_time = time.perf_counter()
        
        try:
            # 测试各组件的配置是否正确加载
            
            # 1. 验证性能优化器配置
            if self.performance_optimizer:
                perf_stats = self.performance_optimizer.get_comprehensive_stats()
                assert 'cache_stats' in perf_stats, "缓存统计缺失"
                assert 'pool_stats' in perf_stats, "连接池统计缺失"
            
            # 2. 验证故障恢复管理器配置
            if self.fault_recovery_manager:
                health_report = self.fault_recovery_manager.get_system_health_report()
                assert 'recovery_stats' in health_report, "恢复统计缺失"
            
            # 3. 验证实时适配器配置
            if self.realtime_adapter:
                adapter_stats = self.realtime_adapter.get_comprehensive_stats()
                assert 'subscription_status' in adapter_stats, "订阅状态缺失"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.PASSED, duration_ms)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.INTEGRATION, TestStatus.FAILED, duration_ms, str(e))
    
    async def _run_performance_tests(self) -> None:
        """运行性能测试"""
        logger.info("⚡ 运行性能测试...")
        
        # 测试数据处理性能
        await self._test_data_processing_performance()
        
        # 测试缓存性能
        await self._test_cache_performance()
        
        # 测试并发处理性能
        await self._test_concurrent_performance()
        
        # 测试内存使用
        await self._test_memory_usage()
    
    async def _test_data_processing_performance(self) -> None:
        """测试数据处理性能"""
        test_name = "数据处理性能测试"
        start_time = time.perf_counter()
        
        try:
            converter = TradingViewDataConverter()
            data_count = 1000
            
            # 生成测试数据
            test_data = []
            for i in range(data_count):
                test_data.append({
                    'time': time.time() + i,
                    'open': 50000.0 + random.uniform(-100, 100),
                    'high': 51000.0 + random.uniform(-100, 100),
                    'low': 49500.0 + random.uniform(-100, 100),
                    'close': 50500.0 + random.uniform(-100, 100),
                    'volume': 1000.0 + random.uniform(-100, 100)
                })
            
            # 测试转换性能
            conversion_start = time.perf_counter()
            successful_conversions = 0
            
            for data in test_data:
                result = converter.convert_kline_to_market_data(data, "BTC/USDT")
                if result:
                    successful_conversions += 1
            
            conversion_time = (time.perf_counter() - conversion_start) * 1000
            avg_conversion_time = conversion_time / data_count
            
            # 验证性能指标
            assert avg_conversion_time < 1.0, f"平均转换时间过长: {avg_conversion_time:.2f}ms"
            assert successful_conversions / data_count > 0.95, f"转换成功率过低: {successful_conversions/data_count:.1%}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'data_count': data_count,
                'total_conversion_time_ms': conversion_time,
                'avg_conversion_time_ms': avg_conversion_time,
                'success_rate': successful_conversions / data_count
            }
            
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_cache_performance(self) -> None:
        """测试缓存性能"""
        test_name = "缓存性能测试"
        start_time = time.perf_counter()
        
        try:
            cache = IntelligentCache(max_size=1000)
            await cache.start()
            
            try:
                # 测试大量写入操作
                write_count = 1000
                write_start = time.time()
                
                for i in range(write_count):
                    await cache.put(f"key_{i}", f"value_{i}")
                
                write_time = (time.time() - write_start) * 1000
                avg_write_time = write_time / write_count
                
                # 测试大量读取操作
                read_start = time.time()
                hits = 0
                
                for i in range(write_count):
                    value = cache.get(f"key_{i}")
                    if value:
                        hits += 1
                
                read_time = (time.time() - read_start) * 1000
                avg_read_time = read_time / write_count
                hit_rate = hits / write_count
                
                # 验证性能指标
                assert avg_write_time < 0.1, f"平均写入时间过长: {avg_write_time:.3f}ms"
                assert avg_read_time < 0.05, f"平均读取时间过长: {avg_read_time:.3f}ms"
                assert hit_rate > 0.99, f"缓存命中率过低: {hit_rate:.1%}"
                
                duration_ms = (time.perf_counter() - start_time) * 1000
                details = {
                    'write_count': write_count,
                    'avg_write_time_ms': avg_write_time,
                    'avg_read_time_ms': avg_read_time,
                    'hit_rate': hit_rate
                }
                
                self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.PASSED, duration_ms, details=details)
                
            finally:
                await cache.stop()
                
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_concurrent_performance(self) -> None:
        """测试并发处理性能"""
        test_name = "并发处理性能测试"
        start_time = time.perf_counter()
        
        try:
            # 创建多个并发任务
            concurrent_tasks = 100
            tasks = []
            
            async def data_processing_task(task_id: int):
                """单个数据处理任务"""
                converter = TradingViewDataConverter()
                
                for i in range(10):  # 每个任务处理10条数据
                    data = {
                        'time': time.time() + i,
                        'open': 50000.0 + random.uniform(-100, 100),
                        'high': 51000.0 + random.uniform(-100, 100),
                        'low': 49500.0 + random.uniform(-100, 100),
                        'close': 50500.0 + random.uniform(-100, 100),
                        'volume': 1000.0
                    }
                    
                    result = converter.convert_kline_to_market_data(data, f"SYMBOL_{task_id}")
                    if not result:
                        raise Exception(f"Task {task_id} conversion failed")
                
                return task_id
            
            # 启动所有并发任务
            concurrent_start = time.time()
            
            for i in range(concurrent_tasks):
                task = asyncio.create_task(data_processing_task(i))
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_time = (time.time() - concurrent_start) * 1000
            
            # 统计结果
            successful_tasks = sum(1 for r in results if not isinstance(r, Exception))
            failed_tasks = len(results) - successful_tasks
            
            # 验证并发性能
            assert concurrent_time < 5000, f"并发处理时间过长: {concurrent_time:.1f}ms"
            assert successful_tasks / concurrent_tasks > 0.95, f"并发成功率过低: {successful_tasks/concurrent_tasks:.1%}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'concurrent_tasks': concurrent_tasks,
                'concurrent_time_ms': concurrent_time,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': successful_tasks / concurrent_tasks
            }
            
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_memory_usage(self) -> None:
        """测试内存使用"""
        test_name = "内存使用测试"
        start_time = time.perf_counter()
        
        try:
            import psutil
            import gc
            
            # 记录初始内存使用
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建大量数据进行处理
            converter = TradingViewDataConverter()
            data_count = 10000
            processed_data = []
            
            for i in range(data_count):
                data = {
                    'time': time.time() + i,
                    'open': 50000.0 + random.uniform(-100, 100),
                    'high': 51000.0 + random.uniform(-100, 100),
                    'low': 49500.0 + random.uniform(-100, 100),
                    'close': 50500.0 + random.uniform(-100, 100),
                    'volume': 1000.0
                }
                
                result = converter.convert_kline_to_market_data(data, "BTC/USDT")
                if result:
                    processed_data.append(result)
            
            # 记录峰值内存使用
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 清理数据
            processed_data.clear()
            gc.collect()
            
            # 记录清理后内存使用
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 计算内存使用指标
            memory_increase = peak_memory - initial_memory
            memory_per_item = memory_increase / data_count * 1024  # KB per item
            memory_cleanup_ratio = (peak_memory - final_memory) / memory_increase if memory_increase > 0 else 0
            
            # 验证内存使用合理性
            assert memory_per_item < 1.0, f"单项内存使用过高: {memory_per_item:.2f}KB"
            assert memory_cleanup_ratio > 0.8, f"内存清理效果不佳: {memory_cleanup_ratio:.1%}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'data_count': data_count,
                'initial_memory_mb': initial_memory,
                'peak_memory_mb': peak_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'memory_per_item_kb': memory_per_item,
                'memory_cleanup_ratio': memory_cleanup_ratio
            }
            
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.PERFORMANCE, TestStatus.FAILED, duration_ms, str(e))
    
    async def _run_fault_tests(self) -> None:
        """运行故障测试"""
        logger.info("🛡️ 运行故障测试...")
        
        # 测试故障检测
        await self._test_fault_detection()
        
        # 测试故障恢复
        await self._test_fault_recovery()
        
        # 测试断路器
        await self._test_circuit_breaker_fault_handling()
        
        # 测试备用数据源切换
        await self._test_backup_source_switching()
    
    async def _test_fault_detection(self) -> None:
        """测试故障检测"""
        test_name = "故障检测测试"
        start_time = time.perf_counter()
        
        try:
            # 模拟故障条件
            fault_metrics = {
                'component': 'test_component',
                'response_time_ms': 6000,  # 超过5秒阈值
                'success_rate': 0.3,       # 低于80%阈值
                'data_quality_score': 0.4  # 低于50%阈值
            }
            
            # 触发故障检测
            detected_faults = await self.fault_recovery_manager.fault_detector.check_for_faults(fault_metrics)
            
            # 验证故障检测结果
            assert len(detected_faults) > 0, "未检测到故障"
            
            # 验证故障类型
            fault_types = [fault.fault_type for fault in detected_faults]
            expected_types = [FaultType.DATA_TIMEOUT, FaultType.SYSTEM_OVERLOAD, FaultType.DATA_CORRUPTION]
            
            for expected_type in expected_types:
                assert expected_type in fault_types, f"未检测到预期故障类型: {expected_type}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'detected_faults_count': len(detected_faults),
                'fault_types': [f.fault_type.name for f in detected_faults]
            }
            
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_fault_recovery(self) -> None:
        """测试故障恢复"""
        test_name = "故障恢复测试"
        start_time = time.perf_counter()
        
        try:
            from .fault_recovery import FaultIncident
            
            # 创建模拟故障
            incident = FaultIncident(
                incident_id="test_recovery_001",
                fault_type=FaultType.CONNECTION_LOST,
                component="test_component",
                description="模拟连接丢失故障",
                severity=3
            )
            
            # 记录活跃故障数量
            initial_active_incidents = len(self.fault_recovery_manager.active_incidents)
            
            # 触发故障处理
            await self.fault_recovery_manager._handle_detected_fault(incident)
            
            # 等待恢复尝试
            await asyncio.sleep(2)
            
            # 验证故障已被记录
            assert len(self.fault_recovery_manager.active_incidents) > initial_active_incidents, "故障未被记录"
            
            # 验证恢复策略已设置
            assert incident.recovery_strategy is not None, "未设置恢复策略"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'incident_id': incident.incident_id,
                'recovery_strategy': incident.recovery_strategy.name if incident.recovery_strategy else None,
                'recovery_attempts': incident.recovery_attempts
            }
            
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_circuit_breaker_fault_handling(self) -> None:
        """测试断路器故障处理"""
        test_name = "断路器故障处理测试"
        start_time = time.perf_counter()
        
        try:
            circuit_breaker = self.fault_recovery_manager.get_circuit_breaker("test_component")
            
            # 模拟连续失败
            def failing_function():
                raise Exception("模拟失败")
            
            failure_count = 0
            for i in range(10):
                try:
                    circuit_breaker.call(failing_function)
                except:
                    failure_count += 1
            
            # 验证断路器状态
            stats = circuit_breaker.get_stats()
            assert stats['state'] == 'OPEN', f"断路器状态错误: {stats['state']}"
            assert stats['total_failures'] >= 5, f"失败计数错误: {stats['total_failures']}"
            
            # 测试断路器阻止后续调用
            try:
                circuit_breaker.call(lambda: "success")
                assert False, "断路器未阻止调用"
            except Exception as e:
                assert "Circuit breaker is OPEN" in str(e), "断路器错误消息不正确"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'circuit_breaker_state': stats['state'],
                'total_failures': stats['total_failures'],
                'failure_rate': stats['failure_rate']
            }
            
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_backup_source_switching(self) -> None:
        """测试备用数据源切换"""
        test_name = "备用数据源切换测试"
        start_time = time.perf_counter()
        
        try:
            # 创建模拟备用数据源
            async def mock_backup_client():
                return "mock_backup_client"
            
            backup_source = BackupDataSource(
                name="mock_backup",
                priority=1,
                client_factory=mock_backup_client
            )
            
            # 添加备用数据源
            self.fault_recovery_manager.add_backup_source("test_component", backup_source)
            
            # 模拟故障需要切换备用源
            from .fault_recovery import FaultIncident
            
            incident = FaultIncident(
                incident_id="backup_test_001",
                fault_type=FaultType.DATA_TIMEOUT,
                component="test_component",
                description="需要切换备用数据源",
                severity=2
            )
            
            # 执行备用源恢复
            await self.fault_recovery_manager._fallback_source_recovery(incident)
            
            # 验证备用源状态
            backup_stats = backup_source.get_stats()
            assert backup_source.is_active or incident.is_resolved, "备用源切换失败"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'backup_source_name': backup_source.name,
                'is_active': backup_source.is_active,
                'incident_resolved': incident.is_resolved
            }
            
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.FAULT, TestStatus.FAILED, duration_ms, str(e))
    
    async def _run_stress_tests(self) -> None:
        """运行压力测试"""
        logger.info("💪 运行压力测试...")
        
        # 测试高频数据处理
        await self._test_high_frequency_data_processing()
        
        # 测试长时间运行稳定性
        await self._test_long_running_stability()
        
        # 测试资源耗尽场景
        await self._test_resource_exhaustion()
    
    async def _test_high_frequency_data_processing(self) -> None:
        """测试高频数据处理"""
        test_name = "高频数据处理压力测试"
        start_time = time.perf_counter()
        
        try:
            # 配置高频测试参数
            data_rate = 100  # 每秒100条数据
            test_duration = 30  # 测试30秒
            total_expected = data_rate * test_duration
            
            processed_count = 0
            error_count = 0
            
            async def data_generator():
                """数据生成器"""
                nonlocal processed_count, error_count
                
                end_time = time.time() + test_duration
                while time.time() < end_time:
                    try:
                        # 生成模拟数据
                        data = {
                            'time': time.time(),
                            'open': 50000.0 + random.uniform(-100, 100),
                            'high': 51000.0 + random.uniform(-100, 100),
                            'low': 49500.0 + random.uniform(-100, 100),
                            'close': 50500.0 + random.uniform(-100, 100),
                            'volume': 1000.0
                        }
                        
                        # 处理数据
                        success = await self.realtime_adapter.process_realtime_data(
                            "BTC/USDT", data, SubscriptionType.KLINE_15M
                        )
                        
                        if success:
                            processed_count += 1
                        else:
                            error_count += 1
                        
                        # 控制数据频率
                        await asyncio.sleep(1.0 / data_rate)
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"数据处理错误: {e}")
            
            # 启动数据生成器
            await data_generator()
            
            # 验证处理结果
            success_rate = processed_count / (processed_count + error_count) if (processed_count + error_count) > 0 else 0
            processing_rate = processed_count / test_duration
            
            assert success_rate > 0.95, f"高频处理成功率过低: {success_rate:.1%}"
            assert processing_rate >= data_rate * 0.9, f"处理速率不足: {processing_rate:.1f}/s (期望: {data_rate}/s)"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'test_duration_s': test_duration,
                'target_data_rate': data_rate,
                'processed_count': processed_count,
                'error_count': error_count,
                'success_rate': success_rate,
                'actual_processing_rate': processing_rate
            }
            
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_long_running_stability(self) -> None:
        """测试长时间运行稳定性"""
        test_name = "长时间运行稳定性测试"
        start_time = time.perf_counter()
        
        try:
            # 配置长时间测试参数
            test_duration = 60  # 测试60秒
            check_interval = 5   # 每5秒检查一次
            
            initial_stats = {
                'system_health': 0,
                'memory_usage': 0,
                'active_connections': 0
            }
            
            # 记录初始状态
            if self.system_monitor:
                dashboard = self.system_monitor.get_system_dashboard()
                initial_stats['system_health'] = dashboard.get('system_overview', {}).get('health_score', 0)
            
            stability_checks = []
            end_time = time.time() + test_duration
            
            # 定期稳定性检查
            while time.time() < end_time:
                try:
                    check_time = time.time()
                    
                    # 检查系统状态
                    if self.system_monitor:
                        dashboard = self.system_monitor.get_system_dashboard()
                        system_overview = dashboard.get('system_overview', {})
                        
                        check_result = {
                            'timestamp': check_time,
                            'health_score': system_overview.get('health_score', 0),
                            'status': system_overview.get('status', 'UNKNOWN'),
                            'uptime': system_overview.get('uptime_seconds', 0)
                        }
                        
                        stability_checks.append(check_result)
                    
                    await asyncio.sleep(check_interval)
                    
                except Exception as e:
                    logger.error(f"稳定性检查错误: {e}")
            
            # 分析稳定性数据
            if stability_checks:
                health_scores = [check['health_score'] for check in stability_checks]
                avg_health = sum(health_scores) / len(health_scores)
                min_health = min(health_scores)
                health_variance = sum((h - avg_health) ** 2 for h in health_scores) / len(health_scores)
                
                # 验证稳定性指标
                assert avg_health > 0.7, f"平均健康分数过低: {avg_health:.2f}"
                assert min_health > 0.5, f"最低健康分数过低: {min_health:.2f}"
                assert health_variance < 0.1, f"健康分数波动过大: {health_variance:.3f}"
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'test_duration_s': test_duration,
                'stability_checks': len(stability_checks),
                'avg_health_score': avg_health if stability_checks else 0,
                'min_health_score': min_health if stability_checks else 0,
                'health_variance': health_variance if stability_checks else 0
            }
            
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.FAILED, duration_ms, str(e))
    
    async def _test_resource_exhaustion(self) -> None:
        """测试资源耗尽场景"""
        test_name = "资源耗尽场景测试"
        start_time = time.perf_counter()
        
        try:
            # 测试缓存容量限制
            cache = IntelligentCache(max_size=100)  # 小容量缓存
            await cache.start()
            
            try:
                # 写入超过容量的数据
                write_count = 200
                for i in range(write_count):
                    await cache.put(f"key_{i}", f"large_value_{i}" * 100)  # 较大的值
                
                # 验证缓存大小限制
                stats = cache.get_cache_stats()
                assert stats['current_size'] <= 100, f"缓存大小超限: {stats['current_size']}"
                assert stats['evictions'] > 0, "未发生缓存清理"
                
                # 测试缓存在资源压力下的性能
                hit_count = 0
                test_reads = 50
                
                for i in range(test_reads):
                    value = cache.get(f"key_{i + write_count - test_reads}")  # 读取最近的数据
                    if value:
                        hit_count += 1
                
                hit_rate = hit_count / test_reads
                assert hit_rate > 0.8, f"资源压力下缓存命中率过低: {hit_rate:.1%}"
                
            finally:
                await cache.stop()
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            details = {
                'cache_max_size': 100,
                'data_written': write_count,
                'evictions': stats.get('evictions', 0),
                'final_cache_size': stats.get('current_size', 0),
                'hit_rate_under_pressure': hit_rate
            }
            
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.PASSED, duration_ms, details=details)
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_test_result(test_name, TestCategory.STRESS, TestStatus.FAILED, duration_ms, str(e))
    
    def _record_test_result(self, test_name: str, category: TestCategory, status: TestStatus, 
                          duration_ms: float, error_message: str = "", details: Dict[str, Any] = None) -> None:
        """记录测试结果"""
        result = TestResult(
            test_name=test_name,
            category=category,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            details=details or {}
        )
        
        self.test_results.append(result)
        
        # 更新统计
        self.test_stats['total_tests'] += 1
        if status == TestStatus.PASSED:
            self.test_stats['passed_tests'] += 1
        elif status == TestStatus.FAILED:
            self.test_stats['failed_tests'] += 1
        elif status == TestStatus.SKIPPED:
            self.test_stats['skipped_tests'] += 1
        
        # 记录日志
        status_emoji = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌", 
            TestStatus.SKIPPED: "⏭️"
        }
        
        emoji = status_emoji.get(status, "❓")
        logger.info(f"{emoji} {test_name} ({category.name}): {status.name} ({duration_ms:.1f}ms)")
        
        if error_message:
            logger.error(f"   错误: {error_message}")
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        try:
            # 按类别统计
            category_stats = {}
            for category in TestCategory:
                category_results = [r for r in self.test_results if r.category == category]
                category_stats[category.name] = {
                    'total': len(category_results),
                    'passed': len([r for r in category_results if r.status == TestStatus.PASSED]),
                    'failed': len([r for r in category_results if r.status == TestStatus.FAILED]),
                    'skipped': len([r for r in category_results if r.status == TestStatus.SKIPPED]),
                    'avg_duration_ms': sum(r.duration_ms for r in category_results) / len(category_results) if category_results else 0
                }
            
            # 失败测试详情
            failed_tests = [r for r in self.test_results if r.status == TestStatus.FAILED]
            
            # 性能统计
            performance_tests = [r for r in self.test_results if r.category == TestCategory.PERFORMANCE]
            performance_summary = {}
            
            if performance_tests:
                performance_summary = {
                    'avg_duration_ms': sum(r.duration_ms for r in performance_tests) / len(performance_tests),
                    'max_duration_ms': max(r.duration_ms for r in performance_tests),
                    'min_duration_ms': min(r.duration_ms for r in performance_tests)
                }
            
            # 计算总体成功率
            success_rate = self.test_stats['passed_tests'] / max(1, self.test_stats['total_tests'])
            
            return {
                'summary': {
                    'total_tests': self.test_stats['total_tests'],
                    'passed_tests': self.test_stats['passed_tests'],
                    'failed_tests': self.test_stats['failed_tests'],
                    'skipped_tests': self.test_stats['skipped_tests'],
                    'success_rate': success_rate,
                    'total_duration_ms': self.test_stats['total_duration_ms']
                },
                'category_breakdown': category_stats,
                'performance_summary': performance_summary,
                'failed_tests': [
                    {
                        'name': test.test_name,
                        'category': test.category.name,
                        'error': test.error_message,
                        'duration_ms': test.duration_ms
                    }
                    for test in failed_tests
                ],
                'detailed_results': [
                    {
                        'name': test.test_name,
                        'category': test.category.name,
                        'status': test.status.name,
                        'duration_ms': test.duration_ms,
                        'timestamp': test.timestamp,
                        'details': test.details
                    }
                    for test in self.test_results
                ],
                'test_environment': {
                    'components_tested': [
                        'enhanced_client', 'data_quality_engine', 'connection_monitor',
                        'performance_optimizer', 'fault_recovery_manager', 
                        'integration_manager', 'realtime_adapter', 'system_monitor'
                    ],
                    'test_symbols': self.test_config['test_symbols'],
                    'performance_threshold_ms': self.test_config['performance_threshold_ms'],
                    'quality_threshold': self.test_config['quality_threshold']
                }
            }
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")
            return {'error': f'生成测试报告失败: {e}'}


# 便捷函数
def create_integration_test_suite() -> IntegrationTestSuite:
    """创建集成测试套件"""
    return IntegrationTestSuite()


async def run_complete_integration_test():
    """运行完整的集成测试"""
    logger.info("🚀 启动TradingView数据源模块完整集成测试")
    
    # 创建测试套件
    test_suite = create_integration_test_suite()
    
    try:
        # 运行所有测试
        test_report = await test_suite.run_all_tests()
        
        # 输出测试报告
        print("\n" + "="*80)
        print("📊 TradingView数据源模块集成测试报告")
        print("="*80)
        
        summary = test_report.get('summary', {})
        print(f"测试总数: {summary.get('total_tests', 0)}")
        print(f"通过: {summary.get('passed_tests', 0)}")
        print(f"失败: {summary.get('failed_tests', 0)}")
        print(f"跳过: {summary.get('skipped_tests', 0)}")
        print(f"成功率: {summary.get('success_rate', 0):.1%}")
        print(f"总耗时: {summary.get('total_duration_ms', 0):.1f}ms")
        
        # 分类统计
        print("\n📋 分类统计:")
        category_breakdown = test_report.get('category_breakdown', {})
        for category, stats in category_breakdown.items():
            print(f"  {category}: {stats['passed']}/{stats['total']} 通过 "
                  f"(平均耗时: {stats['avg_duration_ms']:.1f}ms)")
        
        # 失败测试
        failed_tests = test_report.get('failed_tests', [])
        if failed_tests:
            print("\n❌ 失败测试:")
            for test in failed_tests:
                print(f"  - {test['name']} ({test['category']}): {test['error']}")
        
        # 性能摘要
        performance_summary = test_report.get('performance_summary', {})
        if performance_summary:
            print(f"\n⚡ 性能摘要:")
            print(f"  平均耗时: {performance_summary.get('avg_duration_ms', 0):.1f}ms")
            print(f"  最大耗时: {performance_summary.get('max_duration_ms', 0):.1f}ms")
            print(f"  最小耗时: {performance_summary.get('min_duration_ms', 0):.1f}ms")
        
        print("="*80)
        
        # 判断整体测试结果
        if summary.get('success_rate', 0) >= 0.9:
            print("🎉 集成测试整体通过！TradingView数据源模块增强功能运行良好。")
            return True
        else:
            print("⚠️ 集成测试发现问题，需要进一步调试和优化。")
            return False
        
    except Exception as e:
        logger.error(f"集成测试执行失败: {e}")
        print(f"❌ 集成测试执行失败: {e}")
        return False


if __name__ == "__main__":
    # 运行完整集成测试
    asyncio.run(run_complete_integration_test())