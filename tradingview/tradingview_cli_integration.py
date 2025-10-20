# tradingview/tradingview_cli_integration.py
# 缠论交易系统 - TradingView模块CLI集成

"""
TradingView CLI Integration - 数据源引擎CLI集成

实现tradingview模块的完整CLI操作集成:
- 🎯 8种核心操作: start/stop/status/monitor/debug/test/config/help
- 🔍 5种调试模式: basic/connection/quality/performance/cache
- 📊 数据质量管理: 四级验证体系，质量等级控制
- 🔗 连接管理监控: 健康检查、自动重连、状态追踪
- ⚡ 性能分析优化: 响应时间、吞吐量、缓存效率
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import click

# 导入enhanced_tradingview_manager
try:
    from tradingview.enhanced_tradingview_manager import (
        EnhancedTradingViewManager, DataRequest, DataQualityLevel, 
        DataRequestType, DataSourceStatus, create_enhanced_tradingview_manager,
        create_data_request
    )
except ImportError as e:
    logging.warning(f"无法导入enhanced_tradingview_manager: {e}")
    EnhancedTradingViewManager = None

# =============================================================================
# TradingView CLI集成管理器
# =============================================================================

class TradingViewCLIIntegration:
    """TradingView模块CLI集成管理器"""
    
    def __init__(self, config_dir: str = "tradingview"):
        self.config_dir = Path(config_dir)
        self.manager: Optional[EnhancedTradingViewManager] = None
        self.logger = logging.getLogger(__name__)
        
        # CLI操作映射
        self.operations = {
            'start': self._start_operation,
            'stop': self._stop_operation,
            'status': self._status_operation,
            'monitor': self._monitor_operation,
            'debug': self._debug_operation,
            'test': self._test_operation,
            'config': self._config_operation,
            'help': self._help_operation
        }
        
        # 调试模式映射
        self.debug_modes = {
            'basic': self._debug_basic,
            'connection': self._debug_connection,
            'quality': self._debug_quality,
            'performance': self._debug_performance,
            'cache': self._debug_cache
        }
        
    # =========================================================================
    # 核心操作实现 (8种操作)
    # =========================================================================
    
    async def _start_operation(self, **kwargs) -> Dict[str, Any]:
        """启动TradingView管理器"""
        try:
            if self.manager and self.manager.is_running:
                return {"status": "already_running", "message": "TradingView管理器已在运行"}
                
            self.manager = create_enhanced_tradingview_manager(str(self.config_dir))
            await self.manager.start()
            
            # 等待初始化完成
            await asyncio.sleep(3)
            
            status = self.manager.get_system_status()
            
            return {
                "status": "success",
                "message": "TradingView管理器启动成功",
                "details": {
                    "connections": status['connections'],
                    "system_health": status['system_health']['overall_health'],
                    "startup_time": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": f"启动失败: {e}"}
            
    async def _stop_operation(self, **kwargs) -> Dict[str, Any]:
        """停止TradingView管理器"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            await self.manager.stop()
            self.manager = None
            
            return {
                "status": "success",
                "message": "TradingView管理器已停止",
                "shutdown_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"停止失败: {e}"}
            
    async def _status_operation(self, **kwargs) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            if not self.manager:
                return {"status": "not_initialized", "message": "TradingView管理器未初始化"}
                
            system_status = self.manager.get_system_status()
            performance_report = self.manager.get_performance_report()
            
            return {
                "status": "success",
                "system_overview": {
                    "is_running": system_status['is_running'],
                    "overall_health": system_status['system_health']['overall_health'],
                    "active_connections": system_status['connections']['active'],
                    "total_connections": system_status['connections']['total']
                },
                "data_quality": {
                    "overall_quality": system_status['quality_metrics']['current_metrics']['overall_quality'],
                    "completeness_rate": system_status['quality_metrics']['current_metrics']['completeness_rate'],
                    "accuracy_rate": system_status['quality_metrics']['current_metrics']['accuracy_rate']
                },
                "performance_summary": {
                    "avg_response_time_ms": performance_report['current_metrics']['avg_response_time_ms'],
                    "requests_per_second": performance_report['current_metrics']['requests_per_second'],
                    "error_rate": performance_report['current_metrics']['error_rate']
                },
                "cache_info": {
                    "cache_usage": system_status['cache']['usage_percentage'],
                    "cache_size": system_status['cache']['size']
                },
                "issues_and_recommendations": {
                    "issues": system_status['system_health']['issues'],
                    "recommendations": system_status['system_health']['recommendations']
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"获取状态失败: {e}"}
            
    async def _monitor_operation(self, duration: int = 60, **kwargs) -> Dict[str, Any]:
        """监控系统运行状态"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            monitoring_data = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                timestamp = datetime.now()
                status = self.manager.get_system_status()
                
                monitoring_data.append({
                    "timestamp": timestamp.isoformat(),
                    "overall_health": status['system_health']['overall_health'],
                    "connection_health": status['system_health']['connection_health'],
                    "data_quality_health": status['system_health']['data_quality_health'],
                    "performance_health": status['system_health']['performance_health'],
                    "active_connections": status['connections']['active'],
                    "cache_usage": status['cache']['usage_percentage'],
                    "avg_response_time": status['performance_metrics']['avg_response_time_ms'],
                    "error_rate": status['performance_metrics']['error_rate']
                })
                
                await asyncio.sleep(5)  # 每5秒采集一次数据
                
            # 计算监控期间的统计数据
            if monitoring_data:
                avg_health = sum(d['overall_health'] for d in monitoring_data) / len(monitoring_data)
                avg_response_time = sum(d['avg_response_time'] for d in monitoring_data) / len(monitoring_data)
                max_error_rate = max(d['error_rate'] for d in monitoring_data)
                
                return {
                    "status": "success",
                    "monitoring_duration": duration,
                    "data_points": len(monitoring_data),
                    "summary": {
                        "avg_overall_health": round(avg_health, 2),
                        "avg_response_time_ms": round(avg_response_time, 2),
                        "max_error_rate": round(max_error_rate, 4),
                        "monitoring_completed": datetime.now().isoformat()
                    },
                    "trend_analysis": self._analyze_monitoring_trends(monitoring_data),
                    "detailed_data": monitoring_data
                }
            else:
                return {"status": "no_data", "message": "监控期间未收集到数据"}
                
        except Exception as e:
            return {"status": "error", "message": f"监控失败: {e}"}
            
    async def _debug_operation(self, mode: str = "basic", **kwargs) -> Dict[str, Any]:
        """调试操作"""
        try:
            if mode not in self.debug_modes:
                return {
                    "status": "invalid_mode",
                    "message": f"无效的调试模式: {mode}",
                    "available_modes": list(self.debug_modes.keys())
                }
                
            debug_func = self.debug_modes[mode]
            return await debug_func(**kwargs)
            
        except Exception as e:
            return {"status": "error", "message": f"调试失败: {e}"}
            
    async def _test_operation(self, test_type: str = "basic", **kwargs) -> Dict[str, Any]:
        """测试操作"""
        try:
            if not self.manager:
                return {"status": "not_initialized", "message": "TradingView管理器未初始化"}
                
            test_results = {}
            
            if test_type == "basic" or test_type == "all":
                test_results["basic"] = await self._test_basic_functionality()
                
            if test_type == "connection" or test_type == "all":
                test_results["connection"] = await self._test_connection_management()
                
            if test_type == "data_quality" or test_type == "all":
                test_results["data_quality"] = await self._test_data_quality()
                
            if test_type == "performance" or test_type == "all":
                test_results["performance"] = await self._test_performance()
                
            return {
                "status": "success",
                "test_type": test_type,
                "results": test_results,
                "test_completed": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"测试失败: {e}"}
            
    async def _config_operation(self, action: str = "show", **kwargs) -> Dict[str, Any]:
        """配置操作"""
        try:
            if action == "show":
                return await self._show_config()
            elif action == "validate":
                return await self._validate_config()
            elif action == "update":
                return await self._update_config(kwargs)
            else:
                return {
                    "status": "invalid_action",
                    "message": f"无效的配置操作: {action}",
                    "available_actions": ["show", "validate", "update"]
                }
                
        except Exception as e:
            return {"status": "error", "message": f"配置操作失败: {e}"}
            
    async def _help_operation(self, **kwargs) -> Dict[str, Any]:
        """帮助信息"""
        return {
            "status": "success",
            "tradingview_cli_help": {
                "operations": {
                    "start": "启动TradingView数据源引擎",
                    "stop": "停止TradingView数据源引擎",
                    "status": "获取系统状态和健康信息",
                    "monitor": "监控系统运行 (参数: duration=60)",
                    "debug": "调试系统 (参数: mode=basic/connection/quality/performance/cache)",
                    "test": "测试功能 (参数: test_type=basic/connection/data_quality/performance/all)",
                    "config": "配置管理 (参数: action=show/validate/update)",
                    "help": "显示帮助信息"
                },
                "debug_modes": {
                    "basic": "基本系统信息调试",
                    "connection": "连接管理调试",
                    "quality": "数据质量调试",
                    "performance": "性能分析调试",
                    "cache": "缓存系统调试"
                },
                "data_quality_levels": {
                    "development": "开发级质量 (≥90%)",
                    "production": "生产级质量 (≥95%)",
                    "financial": "金融级质量 (≥98%)"
                },
                "examples": [
                    "python -m tradingview.tradingview_cli_integration start",
                    "python -m tradingview.tradingview_cli_integration debug mode=connection",
                    "python -m tradingview.tradingview_cli_integration test test_type=all",
                    "python -m tradingview.tradingview_cli_integration monitor duration=300"
                ]
            }
        }
        
    # =========================================================================
    # 调试模式实现 (5种调试模式)
    # =========================================================================
    
    async def _debug_basic(self, **kwargs) -> Dict[str, Any]:
        """基本调试信息"""
        try:
            if not self.manager:
                return {"status": "not_initialized", "message": "TradingView管理器未初始化"}
                
            system_status = self.manager.get_system_status()
            
            debug_info = {
                "manager_status": {
                    "is_running": system_status['is_running'],
                    "config_dir": str(self.config_dir),
                    "database_path": self.manager.db_path
                },
                "component_status": {
                    "connection_manager": "active" if self.manager.connection_manager else "inactive",
                    "quality_manager": "active" if self.manager.quality_manager else "inactive",
                    "cache_manager": "active" if self.manager.cache_manager else "inactive",
                    "data_converter": "active" if self.manager.data_converter else "inactive"
                },
                "system_resources": {
                    "memory_usage": f"{self._get_memory_usage():.2f} MB",
                    "thread_count": self._get_thread_count(),
                    "active_connections": system_status['connections']['active'],
                    "cache_entries": system_status['cache']['size']
                },
                "health_summary": {
                    "overall_health": system_status['system_health']['overall_health'],
                    "connection_health": system_status['system_health']['connection_health'],
                    "data_quality_health": system_status['system_health']['data_quality_health'],
                    "performance_health": system_status['system_health']['performance_health']
                }
            }
            
            return {
                "status": "success",
                "debug_mode": "basic",
                "debug_info": debug_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"基本调试失败: {e}"}
            
    async def _debug_connection(self, **kwargs) -> Dict[str, Any]:
        """连接管理调试"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            connection_manager = self.manager.connection_manager
            
            # 连接详细信息
            connection_details = {}
            for conn_id, client in connection_manager.connections.items():
                status = connection_manager.connection_status.get(conn_id, DataSourceStatus.OFFLINE)
                health = connection_manager.connection_health.get(conn_id, 0.0)
                
                connection_details[conn_id] = {
                    "status": status.value,
                    "health_score": health,
                    "client_type": type(client).__name__,
                    "is_connected": hasattr(client, 'is_connected') and client.is_connected if hasattr(client, 'is_connected') else "unknown",
                    "last_activity": "N/A",  # 需要客户端支持
                    "reconnect_count": getattr(client, 'reconnect_count', 0) if hasattr(client, 'reconnect_count') else 0
                }
                
            # 连接统计分析
            connection_analysis = {
                "total_connections": len(connection_manager.connections),
                "healthy_connections": len([h for h in connection_manager.connection_health.values() if h > 80]),
                "degraded_connections": len([h for h in connection_manager.connection_health.values() if 50 < h <= 80]),
                "failed_connections": len([h for h in connection_manager.connection_health.values() if h <= 50]),
                "avg_health_score": statistics.mean(connection_manager.connection_health.values()) if connection_manager.connection_health else 0,
                "connection_distribution": {
                    status.value: sum(1 for s in connection_manager.connection_status.values() if s == status)
                    for status in DataSourceStatus
                }
            }
            
            # 连接配置信息
            connection_config = {
                "max_connections": connection_manager.max_connections,
                "connection_timeout": connection_manager.connection_timeout,
                "auto_reconnect_enabled": True,  # 假设启用
                "health_check_interval": 60     # 假设值
            }
            
            return {
                "status": "success",
                "debug_mode": "connection",
                "connection_analysis": {
                    "connection_details": connection_details,
                    "statistical_analysis": connection_analysis,
                    "configuration": connection_config,
                    "recommendations": self._generate_connection_recommendations(connection_analysis)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"连接调试失败: {e}"}
            
    async def _debug_quality(self, **kwargs) -> Dict[str, Any]:
        """数据质量调试"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            quality_report = self.manager.quality_manager.get_quality_report()
            
            # 质量分析
            quality_analysis = {
                "current_quality_metrics": quality_report['current_metrics'],
                "quality_grade": self._grade_quality(quality_report['current_metrics']['overall_quality']),
                "quality_breakdown": {
                    "completeness": {
                        "rate": quality_report['current_metrics']['completeness_rate'],
                        "grade": self._grade_metric(quality_report['current_metrics']['completeness_rate']),
                        "description": "数据完整性 - 包含所有必需字段的数据比例"
                    },
                    "accuracy": {
                        "rate": quality_report['current_metrics']['accuracy_rate'],
                        "grade": self._grade_metric(quality_report['current_metrics']['accuracy_rate']),
                        "description": "数据准确性 - 通过逻辑验证的数据比例"
                    },
                    "success_rate": {
                        "rate": quality_report['current_metrics']['success_rate'],
                        "grade": self._grade_metric(quality_report['current_metrics']['success_rate']),
                        "description": "请求成功率 - 成功获取数据的请求比例"
                    }
                }
            }
            
            # 质量阈值分析
            threshold_analysis = {}
            for level, threshold in quality_report['quality_thresholds'].items():
                current_quality = quality_report['current_metrics']['overall_quality']
                meets_threshold = current_quality >= threshold
                
                threshold_analysis[level] = {
                    "threshold": threshold,
                    "current_quality": current_quality,
                    "meets_requirement": meets_threshold,
                    "gap": max(0, threshold - current_quality) if not meets_threshold else 0
                }
                
            # 质量趋势分析
            quality_trends = self._analyze_quality_trends()
            
            return {
                "status": "success",
                "debug_mode": "quality",
                "quality_analysis": {
                    "overall_assessment": quality_analysis,
                    "threshold_compliance": threshold_analysis,
                    "trend_analysis": quality_trends,
                    "improvement_suggestions": self._generate_quality_suggestions(quality_analysis),
                    "statistics": quality_report['statistics']
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"质量调试失败: {e}"}
            
    async def _debug_performance(self, **kwargs) -> Dict[str, Any]:
        """性能分析调试"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            performance_report = self.manager.get_performance_report()
            
            # 性能指标分析
            performance_analysis = {
                "response_time_analysis": {
                    "avg_response_time_ms": performance_report['current_metrics']['avg_response_time_ms'],
                    "p95_response_time_ms": performance_report['current_metrics']['p95_response_time_ms'],
                    "p99_response_time_ms": performance_report['current_metrics']['p99_response_time_ms'],
                    "response_time_grade": self._grade_response_time(performance_report['current_metrics']['avg_response_time_ms']),
                    "latency_consistency": self._analyze_latency_consistency(performance_report['current_metrics'])
                },
                "throughput_analysis": {
                    "requests_per_second": performance_report['current_metrics']['requests_per_second'],
                    "concurrent_connections": performance_report['current_metrics']['concurrent_connections'],
                    "throughput_grade": self._grade_throughput(performance_report['current_metrics']['requests_per_second']),
                    "capacity_utilization": self._calculate_capacity_utilization(performance_report['current_metrics'])
                },
                "reliability_analysis": {
                    "error_rate": performance_report['current_metrics']['error_rate'],
                    "uptime_percentage": performance_report['current_metrics']['uptime_percentage'],
                    "reliability_grade": self._grade_reliability(performance_report['current_metrics']['error_rate']),
                    "availability_assessment": self._assess_availability(performance_report['current_metrics']['uptime_percentage'])
                }
            }
            
            # 性能瓶颈分析
            bottleneck_analysis = self._identify_performance_bottlenecks(performance_report)
            
            # 性能优化建议
            optimization_suggestions = self._generate_performance_optimizations(performance_analysis)
            
            return {
                "status": "success",
                "debug_mode": "performance",
                "performance_analysis": {
                    "metrics_breakdown": performance_analysis,
                    "bottleneck_identification": bottleneck_analysis,
                    "optimization_recommendations": optimization_suggestions,
                    "performance_trends": self._analyze_performance_trends(),
                    "sla_compliance": self._check_sla_compliance(performance_report['current_metrics'])
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"性能调试失败: {e}"}
            
    async def _debug_cache(self, **kwargs) -> Dict[str, Any]:
        """缓存系统调试"""
        try:
            if not self.manager or not self.manager.is_running:
                return {"status": "not_running", "message": "TradingView管理器未运行"}
                
            cache_manager = self.manager.cache_manager
            system_status = self.manager.get_system_status()
            
            # 缓存统计分析
            cache_analysis = {
                "basic_statistics": {
                    "cache_size": len(cache_manager.cache),
                    "max_cache_size": cache_manager.cache_size,
                    "usage_percentage": system_status['cache']['usage_percentage'],
                    "total_entries": len(cache_manager.cache_timestamps),
                    "ttl_seconds": cache_manager.cache_ttl.total_seconds()
                },
                "cache_distribution": self._analyze_cache_distribution(cache_manager),
                "expiry_analysis": self._analyze_cache_expiry(cache_manager),
                "memory_efficiency": self._analyze_cache_memory_efficiency(cache_manager)
            }
            
            # 缓存性能分析
            cache_performance = {
                "theoretical_hit_rate": "需要额外统计",
                "cache_effectiveness": self._assess_cache_effectiveness(cache_analysis),
                "cleanup_frequency": "每5分钟",
                "memory_usage_estimate": f"{self._estimate_cache_memory_usage(cache_manager):.2f} MB"
            }
            
            # 缓存优化建议
            cache_optimization = self._generate_cache_optimizations(cache_analysis)
            
            return {
                "status": "success",
                "debug_mode": "cache",
                "cache_analysis": {
                    "statistical_overview": cache_analysis,
                    "performance_metrics": cache_performance,
                    "optimization_recommendations": cache_optimization,
                    "cache_health_score": self._calculate_cache_health_score(cache_analysis)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": f"缓存调试失败: {e}"}
            
    # =========================================================================
    # 测试功能实现
    # =========================================================================
    
    async def _test_basic_functionality(self) -> Dict[str, Any]:
        """测试基本功能"""
        try:
            test_results = {"tests": [], "summary": {"passed": 0, "failed": 0}}
            
            # 测试1: 系统状态获取
            try:
                status = self.manager.get_system_status()
                if status and 'is_running' in status:
                    test_results["tests"].append({
                        "name": "get_system_status",
                        "status": "PASSED",
                        "details": f"系统运行状态: {status['is_running']}"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "get_system_status",
                        "status": "FAILED",
                        "error": "状态数据不完整"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "get_system_status",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            # 测试2: 性能报告获取
            try:
                report = self.manager.get_performance_report()
                if report and 'current_metrics' in report:
                    test_results["tests"].append({
                        "name": "get_performance_report",
                        "status": "PASSED",
                        "details": f"平均响应时间: {report['current_metrics']['avg_response_time_ms']}ms"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "get_performance_report",
                        "status": "FAILED",
                        "error": "性能报告数据不完整"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "get_performance_report",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            # 测试3: 历史数据获取 (模拟)
            try:
                # 由于实际获取数据可能需要网络连接，这里进行模拟测试
                symbol = "BINANCE:BTCUSDT"
                timeframe = "15"
                
                # 检查连接状态
                conn_id = self.manager.connection_manager.get_available_connection()
                if conn_id:
                    test_results["tests"].append({
                        "name": "data_connection_available",
                        "status": "PASSED",
                        "details": f"可用连接: {conn_id}"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "data_connection_available",
                        "status": "FAILED",
                        "error": "没有可用连接"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "data_connection_available",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            return test_results
            
        except Exception as e:
            return {"error": f"基本功能测试失败: {e}"}
            
    async def _test_connection_management(self) -> Dict[str, Any]:
        """测试连接管理"""
        try:
            test_results = {"tests": [], "summary": {"passed": 0, "failed": 0}}
            
            connection_manager = self.manager.connection_manager
            
            # 测试1: 连接创建
            try:
                test_conn_id = "test_connection"
                config = {
                    "auto_reconnect": True,
                    "heartbeat_interval": 30,
                    "max_retries": 2
                }
                
                success = await connection_manager.create_connection(test_conn_id, config)
                
                if success and test_conn_id in connection_manager.connections:
                    test_results["tests"].append({
                        "name": "create_connection",
                        "status": "PASSED",
                        "details": f"成功创建连接: {test_conn_id}"
                    })
                    test_results["summary"]["passed"] += 1
                    
                    # 清理测试连接
                    await connection_manager.close_connection(test_conn_id)
                else:
                    test_results["tests"].append({
                        "name": "create_connection",
                        "status": "FAILED",
                        "error": "连接创建失败"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "create_connection",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            # 测试2: 连接健康检查
            try:
                await connection_manager.check_connections_health()
                
                health_scores = list(connection_manager.connection_health.values())
                if health_scores:
                    avg_health = sum(health_scores) / len(health_scores)
                    test_results["tests"].append({
                        "name": "connection_health_check",
                        "status": "PASSED",
                        "details": f"平均健康分数: {avg_health:.2f}"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "connection_health_check",
                        "status": "FAILED",
                        "error": "没有健康分数数据"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "connection_health_check",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            return test_results
            
        except Exception as e:
            return {"error": f"连接管理测试失败: {e}"}
            
    async def _test_data_quality(self) -> Dict[str, Any]:
        """测试数据质量"""
        try:
            test_results = {"tests": [], "summary": {"passed": 0, "failed": 0}}
            
            quality_manager = self.manager.quality_manager
            
            # 测试1: 质量验证功能
            try:
                # 构造测试数据
                test_klines = [
                    {
                        "timestamp": 1699123456,
                        "open": 35000.0,
                        "high": 35200.0,
                        "low": 34800.0,
                        "close": 35100.0,
                        "volume": 123.456
                    },
                    {
                        "timestamp": 1699123516,  # 60秒后
                        "open": 35100.0,
                        "high": 35300.0,
                        "low": 34900.0,
                        "close": 35250.0,
                        "volume": 234.567
                    }
                ]
                
                quality_score = quality_manager.validate_kline_data(test_klines)
                
                if quality_score > 0.8:  # 80%以上质量
                    test_results["tests"].append({
                        "name": "data_quality_validation",
                        "status": "PASSED",
                        "details": f"质量评分: {quality_score:.3f}"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "data_quality_validation",
                        "status": "FAILED",
                        "error": f"质量评分过低: {quality_score:.3f}"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "data_quality_validation",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            # 测试2: 质量阈值检查
            try:
                test_score = 0.96
                
                for level in DataQualityLevel:
                    meets_threshold = quality_manager.check_quality_level(test_score, level)
                    expected = test_score >= quality_manager.quality_thresholds[level]
                    
                    if meets_threshold == expected:
                        test_results["tests"].append({
                            "name": f"quality_threshold_{level.value}",
                            "status": "PASSED",
                            "details": f"阈值检查正确: {test_score} vs {quality_manager.quality_thresholds[level]}"
                        })
                        test_results["summary"]["passed"] += 1
                    else:
                        test_results["tests"].append({
                            "name": f"quality_threshold_{level.value}",
                            "status": "FAILED",
                            "error": f"阈值检查错误: 期望 {expected}, 实际 {meets_threshold}"
                        })
                        test_results["summary"]["failed"] += 1
                        
            except Exception as e:
                test_results["tests"].append({
                    "name": "quality_threshold_check",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            return test_results
            
        except Exception as e:
            return {"error": f"数据质量测试失败: {e}"}
            
    async def _test_performance(self) -> Dict[str, Any]:
        """测试性能"""
        try:
            test_results = {"tests": [], "summary": {"passed": 0, "failed": 0}}
            
            # 测试1: 响应时间测试
            start_time = time.time()
            try:
                status = self.manager.get_system_status()
                response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                if response_time < 100:  # 100ms以内
                    test_results["tests"].append({
                        "name": "response_time_test",
                        "status": "PASSED",
                        "details": f"响应时间: {response_time:.2f}ms"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "response_time_test",
                        "status": "FAILED",
                        "error": f"响应时间过长: {response_time:.2f}ms"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "response_time_test",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            # 测试2: 缓存性能测试
            try:
                cache_manager = self.manager.cache_manager
                
                # 测试缓存写入性能
                start_time = time.time()
                test_data = {"test": "data", "timestamp": time.time()}
                cache_manager.set_cached_data("TEST", "15", 100, test_data)
                write_time = (time.time() - start_time) * 1000
                
                # 测试缓存读取性能
                start_time = time.time()
                cached_data = cache_manager.get_cached_data("TEST", "15", 100)
                read_time = (time.time() - start_time) * 1000
                
                if write_time < 10 and read_time < 5 and cached_data:  # 写入<10ms, 读取<5ms
                    test_results["tests"].append({
                        "name": "cache_performance_test",
                        "status": "PASSED",
                        "details": f"写入: {write_time:.2f}ms, 读取: {read_time:.2f}ms"
                    })
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["tests"].append({
                        "name": "cache_performance_test",
                        "status": "FAILED",
                        "error": f"缓存性能不达标 - 写入: {write_time:.2f}ms, 读取: {read_time:.2f}ms"
                    })
                    test_results["summary"]["failed"] += 1
                    
            except Exception as e:
                test_results["tests"].append({
                    "name": "cache_performance_test",
                    "status": "FAILED",
                    "error": str(e)
                })
                test_results["summary"]["failed"] += 1
                
            return test_results
            
        except Exception as e:
            return {"error": f"性能测试失败: {e}"}
            
    # =========================================================================
    # 配置管理功能
    # =========================================================================
    
    async def _show_config(self) -> Dict[str, Any]:
        """显示配置"""
        try:
            config_info = {
                "config_directory": str(self.config_dir),
                "database_path": self.manager.db_path if self.manager else "not_initialized",
                "cache_configuration": {
                    "cache_size": self.manager.cache_manager.cache_size if self.manager else "N/A",
                    "cache_ttl_minutes": self.manager.cache_manager.cache_ttl.total_seconds() / 60 if self.manager else "N/A"
                },
                "connection_configuration": {
                    "max_connections": self.manager.connection_manager.max_connections if self.manager else "N/A",
                    "connection_timeout": self.manager.connection_manager.connection_timeout if self.manager else "N/A"
                },
                "quality_thresholds": self.manager.quality_manager.quality_thresholds if self.manager else {}
            }
            
            return {"status": "success", "config": config_info}
            
        except Exception as e:
            return {"status": "error", "message": f"显示配置失败: {e}"}
            
    async def _validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        try:
            validation_results = {"checks": [], "summary": {"passed": 0, "failed": 0}}
            
            # 检查配置目录
            if self.config_dir.exists():
                validation_results["checks"].append({
                    "check": "config_directory_exists",
                    "status": "PASSED"
                })
                validation_results["summary"]["passed"] += 1
            else:
                validation_results["checks"].append({
                    "check": "config_directory_exists",
                    "status": "FAILED",
                    "message": f"配置目录不存在: {self.config_dir}"
                })
                validation_results["summary"]["failed"] += 1
                
            # 检查数据库路径
            if self.manager:
                db_path = Path(self.manager.db_path)
                if db_path.parent.exists():
                    validation_results["checks"].append({
                        "check": "database_path_valid",
                        "status": "PASSED"
                    })
                    validation_results["summary"]["passed"] += 1
                else:
                    validation_results["checks"].append({
                        "check": "database_path_valid",
                        "status": "FAILED",
                        "message": f"数据库目录不存在: {db_path.parent}"
                    })
                    validation_results["summary"]["failed"] += 1
                    
            # 检查质量阈值
            if self.manager and self.manager.quality_manager:
                thresholds = self.manager.quality_manager.quality_thresholds
                valid_thresholds = all(0 <= v <= 1 for v in thresholds.values())
                
                if valid_thresholds:
                    validation_results["checks"].append({
                        "check": "quality_thresholds_valid",
                        "status": "PASSED"
                    })
                    validation_results["summary"]["passed"] += 1
                else:
                    validation_results["checks"].append({
                        "check": "quality_thresholds_valid",
                        "status": "FAILED",
                        "message": "质量阈值应在0-1范围内"
                    })
                    validation_results["summary"]["failed"] += 1
                    
            return {"status": "success", "validation": validation_results}
            
        except Exception as e:
            return {"status": "error", "message": f"配置验证失败: {e}"}
            
    async def _update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        try:
            if not self.manager:
                return {"status": "not_initialized", "message": "TradingView管理器未初始化"}
                
            updated_items = []
            
            # 更新缓存配置
            if "cache_size" in config_updates:
                new_cache_size = int(config_updates["cache_size"])
                if new_cache_size > 0:
                    self.manager.cache_manager.cache_size = new_cache_size
                    updated_items.append("cache_size")
                    
            # 更新质量阈值
            if "quality_thresholds" in config_updates:
                new_thresholds = config_updates["quality_thresholds"]
                for level, threshold in new_thresholds.items():
                    if level in [l.value for l in DataQualityLevel] and 0 <= threshold <= 1:
                        quality_level = DataQualityLevel(level)
                        self.manager.quality_manager.quality_thresholds[quality_level] = threshold
                        updated_items.append(f"quality_threshold_{level}")
                        
            # 更新连接配置
            if "max_connections" in config_updates:
                new_max_conn = int(config_updates["max_connections"])
                if new_max_conn > 0:
                    self.manager.connection_manager.max_connections = new_max_conn
                    updated_items.append("max_connections")
                    
            return {
                "status": "success",
                "updated_items": updated_items,
                "message": f"成功更新 {len(updated_items)} 项配置"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"配置更新失败: {e}"}
            
    # =========================================================================
    # 辅助工具函数
    # =========================================================================
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量 (MB)"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
            
    def _get_thread_count(self) -> int:
        """获取线程数量"""
        try:
            import threading
            return threading.active_count()
        except:
            return 0
            
    def _analyze_monitoring_trends(self, monitoring_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析监控趋势"""
        if len(monitoring_data) < 2:
            return {"trend": "insufficient_data"}
            
        # 健康趋势
        health_values = [d['overall_health'] for d in monitoring_data]
        health_trend = "improving" if health_values[-1] > health_values[0] else "declining" if health_values[-1] < health_values[0] else "stable"
        
        # 响应时间趋势
        response_times = [d['avg_response_time'] for d in monitoring_data]
        response_trend = "improving" if response_times[-1] < response_times[0] else "declining" if response_times[-1] > response_times[0] else "stable"
        
        return {
            "health_trend": health_trend,
            "response_time_trend": response_trend,
            "overall_assessment": "stable" if health_trend == "stable" and response_trend == "stable" else "changing"
        }
        
    def _grade_quality(self, quality_score: float) -> str:
        """评估质量等级"""
        if quality_score >= 0.98:
            return "A+"
        elif quality_score >= 0.95:
            return "A"
        elif quality_score >= 0.90:
            return "B"
        elif quality_score >= 0.80:
            return "C"
        else:
            return "D"
            
    def _grade_metric(self, metric_value: float) -> str:
        """评估指标等级"""
        if metric_value >= 0.95:
            return "Excellent"
        elif metric_value >= 0.90:
            return "Good"
        elif metric_value >= 0.80:
            return "Fair"
        else:
            return "Poor"
            
    def _grade_response_time(self, response_time_ms: float) -> str:
        """评估响应时间等级"""
        if response_time_ms < 50:
            return "Excellent"
        elif response_time_ms < 100:
            return "Good"
        elif response_time_ms < 200:
            return "Fair"
        else:
            return "Poor"
            
    def _grade_throughput(self, rps: float) -> str:
        """评估吞吐量等级"""
        if rps > 10:
            return "High"
        elif rps > 5:
            return "Medium"
        elif rps > 1:
            return "Low"
        else:
            return "Very Low"
            
    def _grade_reliability(self, error_rate: float) -> str:
        """评估可靠性等级"""
        if error_rate < 0.01:
            return "Excellent"
        elif error_rate < 0.05:
            return "Good"
        elif error_rate < 0.10:
            return "Fair"
        else:
            return "Poor"
            
    def _analyze_latency_consistency(self, metrics: Dict[str, Any]) -> str:
        """分析延迟一致性"""
        avg_latency = metrics.get('avg_response_time_ms', 0)
        p95_latency = metrics.get('p95_response_time_ms', 0)
        
        if avg_latency == 0 or p95_latency == 0:
            return "insufficient_data"
            
        consistency_ratio = p95_latency / avg_latency
        
        if consistency_ratio < 1.5:
            return "very_consistent"
        elif consistency_ratio < 2.0:
            return "consistent"
        elif consistency_ratio < 3.0:
            return "moderate"
        else:
            return "inconsistent"
            
    def _calculate_capacity_utilization(self, metrics: Dict[str, Any]) -> str:
        """计算容量利用率"""
        concurrent_connections = metrics.get('concurrent_connections', 0)
        max_connections = 10  # 假设最大连接数
        
        utilization = concurrent_connections / max_connections
        
        if utilization > 0.8:
            return "high"
        elif utilization > 0.5:
            return "medium"
        else:
            return "low"
            
    def _assess_availability(self, uptime_percentage: float) -> str:
        """评估可用性"""
        if uptime_percentage >= 99.9:
            return "excellent"
        elif uptime_percentage >= 99.0:
            return "good"
        elif uptime_percentage >= 95.0:
            return "acceptable"
        else:
            return "poor"
            
    def _identify_performance_bottlenecks(self, performance_report: Dict[str, Any]) -> Dict[str, Any]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        metrics = performance_report['current_metrics']
        
        if metrics['avg_response_time_ms'] > 200:
            bottlenecks.append("high_response_time")
            
        if metrics['error_rate'] > 0.05:
            bottlenecks.append("high_error_rate")
            
        if metrics['concurrent_connections'] < 2:
            bottlenecks.append("insufficient_connections")
            
        return {
            "identified_bottlenecks": bottlenecks,
            "severity": "high" if len(bottlenecks) > 2 else "medium" if len(bottlenecks) > 0 else "low"
        }
        
    def _generate_performance_optimizations(self, performance_analysis: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        suggestions = []
        
        response_analysis = performance_analysis['response_time_analysis']
        if response_analysis['response_time_grade'] in ['Fair', 'Poor']:
            suggestions.append("优化网络连接配置或启用更多并发连接")
            
        throughput_analysis = performance_analysis['throughput_analysis']
        if throughput_analysis['throughput_grade'] in ['Low', 'Very Low']:
            suggestions.append("增加连接数或优化数据处理效率")
            
        reliability_analysis = performance_analysis['reliability_analysis']
        if reliability_analysis['reliability_grade'] in ['Fair', 'Poor']:
            suggestions.append("检查网络稳定性和系统配置，降低错误率")
            
        return suggestions
        
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """分析性能趋势"""
        return {
            "trend_period": "last_hour",
            "response_time_trend": "stable",
            "throughput_trend": "stable",
            "error_rate_trend": "stable",
            "note": "需要历史数据进行详细趋势分析"
        }
        
    def _check_sla_compliance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """检查SLA合规性"""
        sla_targets = {
            "response_time_ms": 100,
            "error_rate": 0.01,
            "uptime_percentage": 99.9
        }
        
        compliance = {}
        for metric, target in sla_targets.items():
            current_value = metrics.get(metric, 0)
            if metric == "response_time_ms":
                meets_sla = current_value <= target
            elif metric == "error_rate":
                meets_sla = current_value <= target
            else:  # uptime_percentage
                meets_sla = current_value >= target
                
            compliance[metric] = {
                "target": target,
                "current": current_value,
                "meets_sla": meets_sla
            }
            
        return compliance
        
    def _analyze_cache_distribution(self, cache_manager) -> Dict[str, Any]:
        """分析缓存分布"""
        if not cache_manager.cache:
            return {"distribution": "empty"}
            
        # 按时间框架分析
        timeframe_counts = {}
        for cache_key in cache_manager.cache.keys():
            parts = cache_key.split(':')
            if len(parts) >= 2:
                timeframe = parts[1]
                timeframe_counts[timeframe] = timeframe_counts.get(timeframe, 0) + 1
                
        return {
            "by_timeframe": timeframe_counts,
            "total_entries": len(cache_manager.cache)
        }
        
    def _analyze_cache_expiry(self, cache_manager) -> Dict[str, Any]:
        """分析缓存过期情况"""
        if not cache_manager.cache_timestamps:
            return {"expiry_analysis": "no_data"}
            
        current_time = datetime.now()
        expired_count = 0
        expiring_soon_count = 0  # 1分钟内过期
        
        for timestamp in cache_manager.cache_timestamps.values():
            age = current_time - timestamp
            if age > cache_manager.cache_ttl:
                expired_count += 1
            elif age > cache_manager.cache_ttl - timedelta(minutes=1):
                expiring_soon_count += 1
                
        return {
            "expired_entries": expired_count,
            "expiring_soon": expiring_soon_count,
            "healthy_entries": len(cache_manager.cache_timestamps) - expired_count - expiring_soon_count
        }
        
    def _analyze_cache_memory_efficiency(self, cache_manager) -> Dict[str, Any]:
        """分析缓存内存效率"""
        return {
            "estimated_memory_per_entry": "1-5 KB",
            "total_estimated_memory": f"{len(cache_manager.cache) * 3} KB",
            "efficiency_assessment": "good" if len(cache_manager.cache) < cache_manager.cache_size * 0.8 else "needs_optimization"
        }
        
    def _assess_cache_effectiveness(self, cache_analysis: Dict[str, Any]) -> str:
        """评估缓存有效性"""
        usage_percentage = cache_analysis['basic_statistics']['usage_percentage']
        
        if usage_percentage > 80:
            return "high_utilization"
        elif usage_percentage > 50:
            return "moderate_utilization"
        else:
            return "low_utilization"
            
    def _estimate_cache_memory_usage(self, cache_manager) -> float:
        """估算缓存内存使用量"""
        # 简单估算：每个缓存条目约3KB
        return len(cache_manager.cache) * 3 / 1024  # 转换为MB
        
    def _generate_cache_optimizations(self, cache_analysis: Dict[str, Any]) -> List[str]:
        """生成缓存优化建议"""
        suggestions = []
        
        usage_percentage = cache_analysis['basic_statistics']['usage_percentage']
        
        if usage_percentage > 90:
            suggestions.append("缓存使用率过高，建议增加缓存大小")
            
        if usage_percentage < 30:
            suggestions.append("缓存使用率较低，可以考虑减少缓存大小以节省内存")
            
        suggestions.append("定期清理过期缓存以维持性能")
        suggestions.append("考虑实现LRU策略以提高缓存效率")
        
        return suggestions
        
    def _calculate_cache_health_score(self, cache_analysis: Dict[str, Any]) -> float:
        """计算缓存健康评分"""
        usage_percentage = cache_analysis['basic_statistics']['usage_percentage']
        
        # 理想使用率在50-80%之间
        if 50 <= usage_percentage <= 80:
            health_score = 100.0
        elif usage_percentage < 50:
            health_score = 80.0 + (usage_percentage / 50) * 20
        else:  # > 80%
            health_score = 100.0 - (usage_percentage - 80) * 2
            
        return max(0.0, min(100.0, health_score))
        
    def _generate_connection_recommendations(self, connection_analysis: Dict[str, Any]) -> List[str]:
        """生成连接优化建议"""
        recommendations = []
        
        total_connections = connection_analysis['total_connections']
        healthy_connections = connection_analysis['healthy_connections']
        
        if total_connections == 0:
            recommendations.append("建议创建至少一个连接")
        elif healthy_connections / total_connections < 0.5:
            recommendations.append("健康连接比例偏低，建议检查网络状态")
            
        if connection_analysis['avg_health_score'] < 80:
            recommendations.append("平均健康分数偏低，建议优化连接配置")
            
        return recommendations
        
    def _analyze_quality_trends(self) -> Dict[str, Any]:
        """分析质量趋势"""
        return {
            "trend_period": "last_hour",
            "completeness_trend": "stable",
            "accuracy_trend": "stable",
            "overall_trend": "stable",
            "note": "需要历史数据进行详细趋势分析"
        }
        
    def _generate_quality_suggestions(self, quality_analysis: Dict[str, Any]) -> List[str]:
        """生成质量改善建议"""
        suggestions = []
        
        overall_grade = quality_analysis['quality_grade']
        
        if overall_grade in ['C', 'D']:
            suggestions.append("整体数据质量需要改善，建议检查数据源连接")
            
        completeness = quality_analysis['quality_breakdown']['completeness']
        if completeness['grade'] in ['Fair', 'Poor']:
            suggestions.append("数据完整性有待提高，检查数据格式和字段完整性")
            
        accuracy = quality_analysis['quality_breakdown']['accuracy']
        if accuracy['grade'] in ['Fair', 'Poor']:
            suggestions.append("数据准确性需要改善，检查数据验证规则")
            
        return suggestions

# =============================================================================
# CLI接口函数
# =============================================================================

async def execute_cli_operation(operation: str, **kwargs) -> Dict[str, Any]:
    """执行CLI操作"""
    cli = TradingViewCLIIntegration()
    
    if operation not in cli.operations:
        return {
            "status": "invalid_operation",
            "message": f"无效的操作: {operation}",
            "available_operations": list(cli.operations.keys())
        }
        
    operation_func = cli.operations[operation]
    return await operation_func(**kwargs)

# =============================================================================
# Click CLI接口 (可选)
# =============================================================================

@click.group()
def cli():
    """TradingView模块CLI管理工具"""
    pass

@cli.command()
@click.option('--config-dir', default='tradingview', help='配置目录路径')
def start(config_dir):
    """启动TradingView管理器"""
    result = asyncio.run(execute_cli_operation('start', config_dir=config_dir))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
def stop():
    """停止TradingView管理器"""
    result = asyncio.run(execute_cli_operation('stop'))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
def status():
    """获取系统状态"""
    result = asyncio.run(execute_cli_operation('status'))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
@click.option('--duration', default=60, help='监控持续时间(秒)')
def monitor(duration):
    """监控系统运行"""
    result = asyncio.run(execute_cli_operation('monitor', duration=duration))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
@click.option('--mode', default='basic', help='调试模式: basic/connection/quality/performance/cache')
def debug(mode):
    """调试系统"""
    result = asyncio.run(execute_cli_operation('debug', mode=mode))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
@click.option('--test-type', default='basic', help='测试类型: basic/connection/data_quality/performance/all')
def test(test_type):
    """测试功能"""
    result = asyncio.run(execute_cli_operation('test', test_type=test_type))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
@click.option('--action', default='show', help='配置操作: show/validate/update')
def config(action):
    """配置管理"""
    result = asyncio.run(execute_cli_operation('config', action=action))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

@cli.command()
def help():
    """显示帮助信息"""
    result = asyncio.run(execute_cli_operation('help'))
    click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    # 直接调用测试
    import sys
    
    if len(sys.argv) > 1:
        operation = sys.argv[1]
        kwargs = {}
        
        # 解析参数
        for arg in sys.argv[2:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                # 尝试转换数字
                try:
                    if '.' in value:
                        kwargs[key] = float(value)
                    else:
                        kwargs[key] = int(value)
                except ValueError:
                    kwargs[key] = value
                    
        # 执行操作
        result = asyncio.run(execute_cli_operation(operation, **kwargs))
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        # 显示可用操作
        cli_integration = TradingViewCLIIntegration()
        print("可用操作:", list(cli_integration.operations.keys()))
        print("调试模式:", list(cli_integration.debug_modes.keys()))