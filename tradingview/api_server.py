#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView模块外部API服务器
提供RESTful API、WebSocket API和数据管理接口
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from fastapi import FastAPI, WebSocket, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .enhanced_client import EnhancedTradingViewClient, ConnectionState
from .data_cache_manager import DataCacheManager, CacheStatus
from .data_quality_monitor import DataQualityEngine
from config.logging_config import get_logger

logger = get_logger(__name__)


# ==================== 数据模型定义 ====================

class DataRequest(BaseModel):
    """数据请求模型"""
    symbol: str = Field(..., description="交易品种")
    timeframe: str = Field(..., description="时间框架")
    count: int = Field(default=500, description="数据数量")
    start_time: Optional[int] = Field(None, description="开始时间戳")
    end_time: Optional[int] = Field(None, description="结束时间戳")
    quality_check: bool = Field(default=True, description="是否进行质量检查")
    use_cache: bool = Field(default=True, description="是否使用缓存")


class KlineData(BaseModel):
    """K线数据模型"""
    timestamp: int
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    """市场数据响应模型"""
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: int


class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str
    uptime: float
    connection_state: str
    data_quality_score: float
    cache_status: str
    metrics: Dict[str, Any]


class SubscriptionRequest(BaseModel):
    """订阅请求模型"""
    symbols: List[str]
    timeframes: List[str]
    data_types: List[str] = ["kline", "quote"]


# ==================== API服务器类 ====================

class TradingViewAPIServer:
    """TradingView API服务器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化API服务器"""
        self.config = config or {}
        self.app = FastAPI(
            title="TradingView Data API",
            description="专业级TradingView数据源API服务",
            version="2.0.0"
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 初始化组件
        self.client = None
        self.cache_manager = None
        self.quality_engine = None
        self.websocket_connections = set()
        self.subscription_manager = {}
        
        # 启动时间
        self.start_time = time.time()
        
        # 注册路由
        self._register_routes()
        
    async def initialize(self):
        """初始化服务组件"""
        try:
            # 初始化增强客户端
            self.client = EnhancedTradingViewClient({
                'auto_reconnect': True,
                'health_monitoring': True,
                'performance_optimization': True
            })
            
            # 初始化缓存管理器
            self.cache_manager = DataCacheManager(
                db_path=self.config.get('cache_db_path', 'tradingview_cache.db'),
                max_memory_size=self.config.get('max_memory_cache', 1000)
            )
            
            # 初始化质量引擎
            self.quality_engine = DataQualityEngine()
            
            # 连接客户端
            await self.client.connect()
            
            logger.info("TradingView API服务器初始化成功")
            
        except Exception as e:
            logger.error(f"API服务器初始化失败: {e}")
            raise
    
    def _register_routes(self):
        """注册API路由"""
        
        # ==================== RESTful API ====================
        
        @self.app.get("/api/v1/health", response_model=HealthStatus)
        async def get_health_status():
            """获取健康状态"""
            try:
                uptime = time.time() - self.start_time
                
                # 获取连接状态
                connection_state = "unknown"
                if self.client and hasattr(self.client, 'monitor'):
                    connection_state = self.client.monitor.state.value
                
                # 获取数据质量评分
                quality_score = 0.0
                if self.quality_engine:
                    quality_score = self.quality_engine.get_overall_quality_score()
                
                # 获取缓存状态
                cache_status = "unknown"
                if self.cache_manager:
                    cache_status = self.cache_manager.get_status().value
                
                # 获取详细指标
                metrics = {
                    "total_symbols": len(self.subscription_manager),
                    "active_connections": len(self.websocket_connections),
                    "cache_hit_rate": self.cache_manager.get_hit_rate() if self.cache_manager else 0.0,
                    "average_latency": self.client.monitor.get_average_latency() if self.client and hasattr(self.client, 'monitor') else 0.0
                }
                
                return HealthStatus(
                    status="healthy" if connection_state == "connected" else "unhealthy",
                    uptime=uptime,
                    connection_state=connection_state,
                    data_quality_score=quality_score,
                    cache_status=cache_status,
                    metrics=metrics
                )
                
            except Exception as e:
                logger.error(f"获取健康状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v1/data/historical", response_model=MarketDataResponse)
        async def get_historical_data(request: DataRequest):
            """获取历史数据"""
            try:
                logger.info(f"收到历史数据请求: {request.symbol} {request.timeframe}")
                
                # 检查缓存
                cached_data = None
                if request.use_cache and self.cache_manager:
                    cached_data = await self.cache_manager.get_historical_data(
                        request.symbol, 
                        request.timeframe,
                        request.count
                    )
                
                if cached_data and cached_data['quality_score'] >= 0.9:
                    logger.info(f"使用缓存数据: {request.symbol}")
                    return MarketDataResponse(
                        status="success",
                        message="Data from cache",
                        data=cached_data,
                        metadata={
                            "source": "cache",
                            "total_count": len(cached_data.get('klines', [])),
                            "quality_score": cached_data.get('quality_score', 0.0)
                        },
                        timestamp=int(time.time())
                    )
                
                # 从TradingView获取数据
                if not self.client:
                    raise HTTPException(status_code=503, detail="TradingView客户端未连接")
                
                chart_session = self.client.Session.Chart()
                
                # 构建请求参数
                params = {
                    'symbol': request.symbol,
                    'timeframe': request.timeframe,
                    'count': request.count
                }
                
                if request.start_time:
                    params['from_timestamp'] = request.start_time
                if request.end_time:
                    params['to_timestamp'] = request.end_time
                
                # 获取数据
                raw_data = await chart_session.get_historical_data(**params)
                
                # 数据质量检查
                quality_score = 1.0
                if request.quality_check and self.quality_engine:
                    quality_result = await self.quality_engine.validate_kline_data(raw_data)
                    quality_score = quality_result.quality_score
                    
                    if quality_score < 0.8:
                        logger.warning(f"数据质量较低: {quality_score:.2f}")
                
                # 格式化数据
                formatted_data = {
                    'symbol': request.symbol,
                    'timeframe': request.timeframe,
                    'klines': raw_data.get('data', []),
                    'quality_score': quality_score
                }
                
                # 更新缓存
                if self.cache_manager and quality_score >= 0.8:
                    await self.cache_manager.store_historical_data(
                        request.symbol,
                        request.timeframe,
                        formatted_data
                    )
                
                return MarketDataResponse(
                    status="success",
                    message="Data retrieved successfully",
                    data=formatted_data,
                    metadata={
                        "source": "tradingview",
                        "total_count": len(formatted_data.get('klines', [])),
                        "quality_score": quality_score,
                        "cache_updated": True
                    },
                    timestamp=int(time.time())
                )
                
            except Exception as e:
                logger.error(f"获取历史数据失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/symbols", response_model=Dict[str, Any])
        async def get_supported_symbols():
            """获取支持的交易品种"""
            try:
                # 从缓存获取品种列表
                symbols = []
                if self.cache_manager:
                    symbols = await self.cache_manager.get_cached_symbols()
                
                return {
                    "status": "success",
                    "data": {
                        "symbols": symbols,
                        "total": len(symbols),
                        "categories": {
                            "crypto": [s for s in symbols if "BINANCE:" in s or "COINBASE:" in s],
                            "forex": [s for s in symbols if "FX:" in s or "OANDA:" in s],
                            "stocks": [s for s in symbols if "NASDAQ:" in s or "NYSE:" in s],
                            "indices": [s for s in symbols if "TVC:" in s]
                        }
                    }
                }
                
            except Exception as e:
                logger.error(f"获取品种列表失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/cache/stats", response_model=Dict[str, Any])
        async def get_cache_statistics():
            """获取缓存统计信息"""
            try:
                if not self.cache_manager:
                    raise HTTPException(status_code=503, detail="缓存管理器未初始化")
                
                stats = await self.cache_manager.get_statistics()
                
                return {
                    "status": "success",
                    "data": stats
                }
                
            except Exception as e:
                logger.error(f"获取缓存统计失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # ==================== WebSocket API ====================
        
        @self.app.websocket("/ws/realtime")
        async def websocket_realtime_data(websocket: WebSocket):
            """实时数据WebSocket端点"""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            
            try:
                logger.info("新的WebSocket连接建立")
                
                while True:
                    # 接收客户端消息
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    message_type = message.get('type')
                    
                    if message_type == 'subscribe':
                        # 处理订阅请求
                        await self._handle_subscribe(websocket, message)
                    elif message_type == 'unsubscribe':
                        # 处理取消订阅
                        await self._handle_unsubscribe(websocket, message)
                    elif message_type == 'ping':
                        # 心跳响应
                        await websocket.send_text(json.dumps({
                            'type': 'pong',
                            'timestamp': int(time.time())
                        }))
                    
            except Exception as e:
                logger.error(f"WebSocket连接错误: {e}")
            finally:
                self.websocket_connections.remove(websocket)
                logger.info("WebSocket连接关闭")
        
        @self.app.delete("/api/v1/cache/clear")
        async def clear_cache():
            """清空缓存"""
            try:
                if not self.cache_manager:
                    raise HTTPException(status_code=503, detail="缓存管理器未初始化")
                
                await self.cache_manager.clear_all_cache()
                
                return {
                    "status": "success",
                    "message": "缓存已清空"
                }
                
            except Exception as e:
                logger.error(f"清空缓存失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _handle_subscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理订阅请求"""
        try:
            symbols = message.get('symbols', [])
            timeframes = message.get('timeframes', ['1'])
            
            for symbol in symbols:
                for tf in timeframes:
                    subscription_key = f"{symbol}:{tf}"
                    
                    if subscription_key not in self.subscription_manager:
                        self.subscription_manager[subscription_key] = set()
                    
                    self.subscription_manager[subscription_key].add(websocket)
            
            # 发送确认消息
            await websocket.send_text(json.dumps({
                'type': 'subscribed',
                'symbols': symbols,
                'timeframes': timeframes,
                'timestamp': int(time.time())
            }))
            
            logger.info(f"WebSocket订阅成功: {symbols}")
            
        except Exception as e:
            logger.error(f"处理订阅请求失败: {e}")
    
    async def _handle_unsubscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理取消订阅请求"""
        try:
            symbols = message.get('symbols', [])
            timeframes = message.get('timeframes', ['1'])
            
            for symbol in symbols:
                for tf in timeframes:
                    subscription_key = f"{symbol}:{tf}"
                    
                    if subscription_key in self.subscription_manager:
                        self.subscription_manager[subscription_key].discard(websocket)
                        
                        # 如果没有订阅者了，删除这个key
                        if not self.subscription_manager[subscription_key]:
                            del self.subscription_manager[subscription_key]
            
            # 发送确认消息
            await websocket.send_text(json.dumps({
                'type': 'unsubscribed',
                'symbols': symbols,
                'timeframes': timeframes,
                'timestamp': int(time.time())
            }))
            
            logger.info(f"WebSocket取消订阅成功: {symbols}")
            
        except Exception as e:
            logger.error(f"处理取消订阅请求失败: {e}")
    
    async def broadcast_realtime_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """广播实时数据"""
        subscription_key = f"{symbol}:{timeframe}"
        
        if subscription_key in self.subscription_manager:
            message = json.dumps({
                'type': 'realtime_data',
                'symbol': symbol,
                'timeframe': timeframe,
                'data': data,
                'timestamp': int(time.time())
            })
            
            # 向所有订阅者发送数据
            disconnected_websockets = set()
            for websocket in self.subscription_manager[subscription_key]:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"向WebSocket发送数据失败: {e}")
                    disconnected_websockets.add(websocket)
            
            # 清理断开的连接
            for ws in disconnected_websockets:
                self.subscription_manager[subscription_key].discard(ws)
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """启动API服务器"""
        logger.info(f"启动TradingView API服务器: {host}:{port}")
        
        # 初始化组件
        await self.initialize()
        
        # 启动服务器
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()


# ==================== 启动脚本 ====================

async def main():
    """主函数"""
    config = {
        'cache_db_path': 'data/tradingview_cache.db',
        'max_memory_cache': 5000,
        'api_host': '0.0.0.0',
        'api_port': 8000
    }
    
    server = TradingViewAPIServer(config)
    await server.start_server(
        host=config['api_host'],
        port=config['api_port']
    )


if __name__ == "__main__":
    asyncio.run(main())