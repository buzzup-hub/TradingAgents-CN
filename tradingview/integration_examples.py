#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView模块外部集成示例
展示如何在不同场景下使用TradingView数据源
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# 导入TradingView模块组件
from .api_server import TradingViewAPIServer
from .data_cache_manager import DataCacheManager, CacheLevel
from .enhanced_data_quality_monitor import DataQualityMonitor, AlertLevel
from .enhanced_client import EnhancedTradingViewClient

# 导入系统其他模块（假设存在）
try:
    from trading_core.data_manager import IDataSource, MarketData
    from chanpy.Chan import CChan
    from config.config_manager import get_config
except ImportError:
    # 模拟接口，用于示例
    class IDataSource:
        pass
    
    class MarketData:
        def __init__(self, symbol: str, timeframe: str, klines: List[Dict]):
            self.symbol = symbol
            self.timeframe = timeframe  
            self.klines = klines

from config.logging_config import get_logger

logger = get_logger(__name__)


# ==================== 场景1: 作为trading_core的数据源 ====================

class TradingViewDataSource(IDataSource):
    """TradingView数据源适配器 - 集成到trading_core"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化数据源"""
        self.config = config or {}
        self.client = None
        self.cache_manager = None
        self.quality_monitor = None
        self.initialized = False
        
    async def initialize(self) -> bool:
        """初始化数据源"""
        try:
            # 初始化增强客户端
            self.client = EnhancedTradingViewClient({
                'auto_reconnect': True,
                'health_monitoring': True,
                'performance_optimization': True,
                'max_reconnect_attempts': 10,
                'heartbeat_interval': 30
            })
            
            # 初始化缓存管理器
            self.cache_manager = DataCacheManager(
                db_path=self.config.get('cache_db_path', 'trading_data_cache.db'),
                max_memory_size=self.config.get('max_cache_size', 2000)
            )
            
            # 初始化质量监控
            self.quality_monitor = DataQualityMonitor({
                'critical_quality_score': 0.7,
                'warning_quality_score': 0.85
            })
            
            # 注册质量告警处理器
            self.quality_monitor.register_alert_handler(self._handle_quality_alert)
            
            # 连接TradingView
            await self.client.connect()
            
            self.initialized = True
            logger.info("TradingView数据源初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"TradingView数据源初始化失败: {e}")
            self.initialized = False
            return False
    
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                count: int = 500, **kwargs) -> Optional[MarketData]:
        """获取历史数据"""
        if not self.initialized:
            logger.error("数据源未初始化")
            return None
        
        try:
            # 首先检查缓存
            cached_data = await self.cache_manager.get_historical_data(
                symbol, timeframe, count, **kwargs
            )
            
            if cached_data and cached_data.get('quality_score', 0) >= 0.8:
                logger.info(f"使用缓存数据: {symbol}:{timeframe}")
                return MarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    klines=cached_data['klines']
                )
            
            # 从TradingView获取数据
            chart_session = self.client.Session.Chart()
            raw_data = await chart_session.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                **kwargs
            )
            
            # 数据质量检查
            formatted_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'klines': raw_data.get('data', []),
                'quality_score': 1.0
            }
            
            quality_result = await self.quality_monitor.evaluate_data_quality(
                symbol, timeframe, formatted_data
            )
            
            formatted_data['quality_score'] = quality_result.quality_score
            
            # 如果质量足够，存入缓存
            if quality_result.quality_score >= 0.8:
                await self.cache_manager.store_historical_data(
                    symbol, timeframe, formatted_data
                )
            
            return MarketData(
                symbol=symbol,
                timeframe=timeframe,
                klines=formatted_data['klines']
            )
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return None
    
    async def subscribe_realtime_data(self, symbols: List[str], 
                                    callback: callable) -> bool:
        """订阅实时数据"""
        if not self.initialized:
            return False
        
        try:
            # 为每个品种创建订阅
            for symbol in symbols:
                chart_session = self.client.Session.Chart()
                await chart_session.subscribe_realtime(
                    symbol=symbol,
                    callback=lambda data: self._handle_realtime_data(data, callback)
                )
            
            logger.info(f"订阅实时数据成功: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"订阅实时数据失败: {e}")
            return False
    
    async def _handle_realtime_data(self, data: Dict[str, Any], callback: callable):
        """处理实时数据"""
        try:
            # 数据质量快速检查
            if self._is_data_valid(data):
                await callback(data)
            else:
                logger.warning(f"实时数据质量检查失败: {data.get('symbol', 'unknown')}")
                
        except Exception as e:
            logger.error(f"处理实时数据失败: {e}")
    
    def _is_data_valid(self, data: Dict[str, Any]) -> bool:
        """快速数据有效性检查"""
        required_fields = ['symbol', 'timestamp', 'price']
        
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        
        try:
            price = float(data['price'])
            timestamp = int(data['timestamp'])
            
            if price <= 0 or timestamp <= 0:
                return False
                
            return True
            
        except (ValueError, TypeError):
            return False
    
    async def _handle_quality_alert(self, alert):
        """处理数据质量告警"""
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            logger.error(f"数据质量严重告警: {alert.message}")
            # 可以在这里触发数据源切换或其他应急措施
        else:
            logger.warning(f"数据质量告警: {alert.message}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取数据源健康状态"""
        if not self.initialized:
            return {'status': 'uninitialized'}
        
        client_health = self.client.get_health_status() if self.client else {}
        cache_stats = await self.cache_manager.get_statistics() if self.cache_manager else {}
        quality_stats = self.quality_monitor.get_quality_statistics() if self.quality_monitor else {}
        
        return {
            'status': 'healthy' if client_health.get('connected', False) else 'unhealthy',
            'client_health': client_health,
            'cache_statistics': cache_stats,
            'quality_statistics': quality_stats
        }
    
    async def shutdown(self):
        """关闭数据源"""
        if self.client:
            await self.client.disconnect()
        
        logger.info("TradingView数据源已关闭")


# ==================== 场景2: 为chanpy提供数据 ====================

class ChanpyDataFeeder:
    """为chanpy缠论分析提供数据"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化数据馈送器"""
        self.config = config or {}
        self.data_source = TradingViewDataSource(config)
        self.chan_instances = {}  # 存储CChan实例
        
    async def initialize(self) -> bool:
        """初始化"""
        return await self.data_source.initialize()
    
    async def create_chan_analysis(self, symbol: str, timeframe: str, 
                                 chan_config: Dict[str, Any] = None) -> Optional[str]:
        """创建缠论分析实例"""
        try:
            # 获取历史数据
            market_data = await self.data_source.get_historical_data(
                symbol, timeframe, count=1000
            )
            
            if not market_data or not market_data.klines:
                logger.error(f"无法获取数据进行缠论分析: {symbol}:{timeframe}")
                return None
            
            # 转换为chanpy格式
            chanpy_data = self._convert_to_chanpy_format(market_data.klines)
            
            # 创建CChan实例（假设CChan接口）
            chan_instance = CChan(
                code=symbol,
                begin_time=None,
                end_time=None,
                data_src="custom",
                lv_list=[timeframe],
                config=chan_config or {}
            )
            
            # 加载数据到CChan
            for kline in chanpy_data:
                chan_instance.add_lv_iter(kline)
            
            # 存储实例
            instance_id = f"{symbol}_{timeframe}_{int(time.time())}"
            self.chan_instances[instance_id] = {
                'chan': chan_instance,
                'symbol': symbol,
                'timeframe': timeframe,
                'created_at': time.time(),
                'last_update': time.time()
            }
            
            logger.info(f"创建缠论分析实例: {instance_id}")
            return instance_id
            
        except Exception as e:
            logger.error(f"创建缠论分析失败: {e}")
            return None
    
    def _convert_to_chanpy_format(self, klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换数据格式为chanpy需要的格式"""
        chanpy_klines = []
        
        for kline in klines:
            try:
                chanpy_kline = {
                    'time': datetime.fromtimestamp(int(kline['timestamp'])),
                    'open': float(kline['open']),
                    'high': float(kline['high']),
                    'low': float(kline['low']),
                    'close': float(kline['close']),
                    'volume': float(kline.get('volume', 0))
                }
                chanpy_klines.append(chanpy_kline)
                
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"转换K线数据失败: {e}")
                continue
        
        return chanpy_klines
    
    async def update_chan_analysis(self, instance_id: str) -> bool:
        """更新缠论分析"""
        if instance_id not in self.chan_instances:
            logger.error(f"缠论分析实例不存在: {instance_id}")
            return False
        
        try:
            instance = self.chan_instances[instance_id]
            symbol = instance['symbol']
            timeframe = instance['timeframe']
            
            # 获取最新数据
            market_data = await self.data_source.get_historical_data(
                symbol, timeframe, count=100  # 获取最近100根K线
            )
            
            if not market_data or not market_data.klines:
                return False
            
            # 转换并更新
            chanpy_data = self._convert_to_chanpy_format(market_data.klines)
            
            # 更新CChan实例
            chan = instance['chan']
            for kline in chanpy_data:
                chan.add_lv_iter(kline)
            
            instance['last_update'] = time.time()
            
            logger.debug(f"更新缠论分析实例: {instance_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新缠论分析失败: {e}")
            return False
    
    def get_chan_analysis_result(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """获取缠论分析结果"""
        if instance_id not in self.chan_instances:
            return None
        
        try:
            instance = self.chan_instances[instance_id]
            chan = instance['chan']
            
            # 获取买卖点
            buy_sell_points = []
            if hasattr(chan, 'get_bsp'):
                bsp_list = chan.get_bsp()
                for bsp in bsp_list:
                    buy_sell_points.append({
                        'type': bsp.type.value if hasattr(bsp.type, 'value') else str(bsp.type),
                        'timestamp': int(bsp.klu.time.timestamp()) if hasattr(bsp.klu, 'time') else 0,
                        'price': float(bsp.klu.close) if hasattr(bsp.klu, 'close') else 0.0,
                        'is_buy': bsp.is_buy if hasattr(bsp, 'is_buy') else None
                    })
            
            # 获取中枢信息
            zs_list = []
            if hasattr(chan, 'get_zs'):
                zs_data = chan.get_zs()
                for zs in zs_data:
                    zs_list.append({
                        'level': zs.level if hasattr(zs, 'level') else 0,
                        'high': float(zs.high) if hasattr(zs, 'high') else 0.0,
                        'low': float(zs.low) if hasattr(zs, 'low') else 0.0,
                        'begin_time': int(zs.begin.time.timestamp()) if hasattr(zs, 'begin') and hasattr(zs.begin, 'time') else 0,
                        'end_time': int(zs.end.time.timestamp()) if hasattr(zs, 'end') and hasattr(zs.end, 'time') else 0
                    })
            
            return {
                'instance_id': instance_id,
                'symbol': instance['symbol'],
                'timeframe': instance['timeframe'],
                'created_at': instance['created_at'],
                'last_update': instance['last_update'],
                'buy_sell_points': buy_sell_points,
                'zs_list': zs_list,
                'analysis_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"获取缠论分析结果失败: {e}")
            return None


# ==================== 场景3: RESTful API集成示例 ====================

class TradingViewRESTClient:
    """TradingView REST API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化REST客户端"""
        self.base_url = base_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        import aiohttp
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                count: int = 500, **kwargs) -> Optional[Dict[str, Any]]:
        """获取历史数据"""
        if not self.session:
            raise RuntimeError("客户端未初始化，请使用with语句")
        
        url = f"{self.base_url}/api/v1/data/historical"
        
        payload = {
            'symbol': symbol,
            'timeframe': timeframe,
            'count': count,
            **kwargs
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"获取历史数据失败: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"请求历史数据失败: {e}")
            return None
    
    async def get_health_status(self) -> Optional[Dict[str, Any]]:
        """获取健康状态"""
        if not self.session:
            raise RuntimeError("客户端未初始化")
        
        url = f"{self.base_url}/api/v1/health"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"获取健康状态失败: {e}")
            return None
    
    async def get_supported_symbols(self) -> Optional[List[str]]:
        """获取支持的品种"""
        if not self.session:
            raise RuntimeError("客户端未初始化")
        
        url = f"{self.base_url}/api/v1/symbols"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('symbols', [])
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"获取品种列表失败: {e}")
            return None


# ==================== 场景4: WebSocket实时数据集成 ====================

class TradingViewWebSocketClient:
    """TradingView WebSocket客户端"""
    
    def __init__(self, ws_url: str = "ws://localhost:8000/ws/realtime"):
        """初始化WebSocket客户端"""
        self.ws_url = ws_url
        self.websocket = None
        self.subscriptions = set()
        self.message_handlers = {}
        self.running = False
        
    async def connect(self) -> bool:
        """连接WebSocket"""
        try:
            import websockets
            
            self.websocket = await websockets.connect(self.ws_url)
            self.running = True
            
            # 启动消息处理循环
            asyncio.create_task(self._message_loop())
            
            logger.info(f"WebSocket连接成功: {self.ws_url}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
            
        logger.info("WebSocket连接已断开")
    
    async def subscribe(self, symbols: List[str], timeframes: List[str] = None):
        """订阅实时数据"""
        if not self.websocket:
            logger.error("WebSocket未连接")
            return
        
        message = {
            'type': 'subscribe',
            'symbols': symbols,
            'timeframes': timeframes or ['1'],
            'timestamp': int(time.time())
        }
        
        await self.websocket.send(json.dumps(message))
        
        for symbol in symbols:
            self.subscriptions.add(symbol)
        
        logger.info(f"订阅实时数据: {symbols}")
    
    async def unsubscribe(self, symbols: List[str], timeframes: List[str] = None):
        """取消订阅"""
        if not self.websocket:
            return
        
        message = {
            'type': 'unsubscribe',
            'symbols': symbols,
            'timeframes': timeframes or ['1'],
            'timestamp': int(time.time())
        }
        
        await self.websocket.send(json.dumps(message))
        
        for symbol in symbols:
            self.subscriptions.discard(symbol)
        
        logger.info(f"取消订阅: {symbols}")
    
    def register_message_handler(self, message_type: str, handler: callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        
    async def _message_loop(self):
        """消息处理循环"""
        while self.running and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                message_type = data.get('type')
                if message_type in self.message_handlers:
                    handler = self.message_handlers[message_type]
                    await handler(data)
                
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break


# ==================== 使用示例 ====================

async def example_trading_core_integration():
    """示例1: 集成到trading_core"""
    logger.info("=== 示例1: trading_core集成 ===")
    
    # 初始化数据源
    data_source = TradingViewDataSource({
        'cache_db_path': 'example_trading_core.db',
        'max_cache_size': 1000
    })
    
    if await data_source.initialize():
        # 获取历史数据
        market_data = await data_source.get_historical_data(
            'BINANCE:BTCUSDT', '15', count=500
        )
        
        if market_data:
            logger.info(f"获取到{len(market_data.klines)}条K线数据")
            
            # 订阅实时数据
            async def realtime_callback(data):
                logger.info(f"收到实时数据: {data.get('symbol')} = {data.get('price')}")
            
            await data_source.subscribe_realtime_data(
                ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'], 
                realtime_callback
            )
        
        # 获取健康状态
        health = await data_source.get_health_status()
        logger.info(f"数据源健康状态: {health.get('status')}")
        
        await data_source.shutdown()


async def example_chanpy_integration():
    """示例2: 集成到chanpy"""
    logger.info("=== 示例2: chanpy集成 ===")
    
    # 初始化数据馈送器
    feeder = ChanpyDataFeeder({
        'cache_db_path': 'example_chanpy.db'
    })
    
    if await feeder.initialize():
        # 创建缠论分析
        instance_id = await feeder.create_chan_analysis(
            'BINANCE:BTCUSDT', '15', 
            {'bi_strict': True, 'trigger_step': True}
        )
        
        if instance_id:
            logger.info(f"创建缠论分析实例: {instance_id}")
            
            # 等待一段时间后更新
            await asyncio.sleep(2)
            
            # 更新分析
            if await feeder.update_chan_analysis(instance_id):
                # 获取分析结果
                result = feeder.get_chan_analysis_result(instance_id)
                if result:
                    logger.info(f"买卖点数量: {len(result.get('buy_sell_points', []))}")
                    logger.info(f"中枢数量: {len(result.get('zs_list', []))}")


async def example_rest_api():
    """示例3: REST API使用"""
    logger.info("=== 示例3: REST API集成 ===")
    
    async with TradingViewRESTClient() as client:
        # 获取健康状态
        health = await client.get_health_status()
        if health:
            logger.info(f"API服务状态: {health.get('status')}")
        
        # 获取支持的品种
        symbols = await client.get_supported_symbols()
        if symbols:
            logger.info(f"支持{len(symbols)}个交易品种")
        
        # 获取历史数据
        data = await client.get_historical_data('BINANCE:BTCUSDT', '15', count=100)
        if data and data.get('status') == 'success':
            klines = data.get('data', {}).get('klines', [])
            logger.info(f"获取到{len(klines)}条历史K线")


async def example_websocket():
    """示例4: WebSocket实时数据"""
    logger.info("=== 示例4: WebSocket实时数据 ===")
    
    client = TradingViewWebSocketClient()
    
    # 注册消息处理器
    async def handle_realtime_data(data):
        symbol = data.get('symbol')
        price = data.get('data', {}).get('price')
        logger.info(f"实时数据: {symbol} = ${price}")
    
    async def handle_subscribed(data):
        logger.info(f"订阅确认: {data.get('symbols')}")
    
    client.register_message_handler('realtime_data', handle_realtime_data)
    client.register_message_handler('subscribed', handle_subscribed)
    
    if await client.connect():
        # 订阅数据
        await client.subscribe(['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'])
        
        # 等待一段时间接收数据
        await asyncio.sleep(10)
        
        # 取消订阅并断开
        await client.unsubscribe(['BINANCE:BTCUSDT'])
        await client.disconnect()


async def run_all_examples():
    """运行所有示例"""
    logger.info("开始运行TradingView集成示例")
    
    try:
        # 注意: 这些示例需要相应的服务运行
        # await example_trading_core_integration()
        # await example_chanpy_integration()
        # await example_rest_api()
        # await example_websocket()
        
        # 模拟示例运行
        logger.info("所有集成示例模拟完成")
        
    except Exception as e:
        logger.error(f"运行示例失败: {e}")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行示例
    asyncio.run(run_all_examples())