#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView K线数据 HTTP API 服务

提供RESTful API接口获取TradingView历史K线数据

启动服务:
    python -m tradingview.kline_api_server

    或指定端口:
    python -m tradingview.kline_api_server --port 8080

API端点:
    GET /klines?symbol=OANDA:XAUUSD&timeframe=15&count=100
    GET /health
    GET /stats

示例请求:
    curl "http://localhost:8000/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100"
    curl "http://localhost:8000/klines?symbol=BINANCE:BTCUSDT&timeframe=15m&count=50"

作者: Claude Code Assistant
创建时间: 2024-12
版本: 1.0.0
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI, Query, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("❌ 缺少依赖包，请安装: pip install fastapi uvicorn")
    sys.exit(1)

from tradingview.historical_kline_service import (
    HistoricalKlineService,
    KlineDataRequest,
    KlineQualityLevel,
    DataFetchStatus
)

from config.logging_config import get_logger
logger = get_logger(__name__)

# =============================================================================
# 全局服务实例
# =============================================================================

kline_service: Optional[HistoricalKlineService] = None

# =============================================================================
# 生命周期管理
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global kline_service

    # 启动
    logger.info("🚀 启动K线数据API服务...")
    try:
        kline_service = HistoricalKlineService(use_enhanced_client=True)
        await kline_service.initialize()
        logger.info("✅ K线数据服务初始化成功")
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise

    yield

    # 关闭
    logger.info("🛑 关闭K线数据API服务...")
    if kline_service:
        await kline_service.close()
        logger.info("✅ K线数据服务已关闭")

# =============================================================================
# FastAPI应用配置
# =============================================================================

app = FastAPI(
    title="TradingView K线数据API",
    description="提供TradingView历史K线数据的RESTful API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS配置 - 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# API端点
# =============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "TradingView K线数据API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "klines": "/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100",
            "health": "/health",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

@app.get("/klines")
async def get_klines(
    symbol: str = Query(..., description="交易品种，例如: OANDA:XAUUSD, BINANCE:BTCUSDT"),
    timeframe: str = Query("15", description="时间框架，例如: 1, 5, 15, 30, 60, 1D (也支持15m格式)"),
    count: int = Query(100, ge=1, le=5000, description="K线数量 (1-5000)"),
    quality: str = Query("production", description="质量等级: development, production, financial"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    format: str = Query("json", description="返回格式: json, simple")
):
    """
    获取K线数据

    参数:
        - symbol: 交易品种 (必需)
            - 格式: 交易所:品种，例如: OANDA:XAUUSD, BINANCE:BTCUSDT
            - 如果没有交易所前缀，默认为BINANCE

        - timeframe: 时间框架 (默认: 15)
            - 支持格式: 1, 5, 15, 30, 60, 240, 1D, 1W, 1M
            - 也支持: 1m, 5m, 15m, 1h, 4h, 1d (会自动转换)

        - count: 获取数量 (默认: 100, 范围: 1-5000)

        - quality: 质量等级 (默认: production)
            - development: ≥90%
            - production: ≥95%
            - financial: ≥98%

        - use_cache: 是否使用缓存 (默认: true)

        - format: 返回格式
            - json: 完整JSON格式（包含元数据）
            - simple: 简化格式（仅K线数据）

    返回:
        JSON格式的K线数据

    示例:
        /klines?symbol=OANDA:XAUUSD&timeframe=15&count=100
        /klines?symbol=BINANCE:BTCUSDT&timeframe=1h&count=50&format=simple
    """
    try:
        # 标准化时间框架格式 (15m -> 15, 1h -> 60, 4h -> 240, 1d -> 1D)
        timeframe_normalized = normalize_timeframe(timeframe)

        # 标准化品种格式
        symbol_normalized = normalize_symbol(symbol)

        # 解析质量等级
        try:
            quality_level = KlineQualityLevel[quality.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的质量等级: {quality}. 可选值: development, production, financial"
            )

        # 创建请求
        request = KlineDataRequest(
            symbol=symbol_normalized,
            timeframe=timeframe_normalized,
            count=count,
            quality_level=quality_level,
            cache_enabled=use_cache
        )

        logger.info(f"📊 收到K线请求: {symbol_normalized} {timeframe_normalized} x{count}")

        # 获取K线数据
        response = await kline_service.fetch_klines(request)

        # 根据状态返回不同的HTTP状态码
        if response.status == DataFetchStatus.FAILED:
            raise HTTPException(
                status_code=500,
                detail=f"数据获取失败: {response.error_message}"
            )

        # 格式化返回结果
        if format == "simple":
            # 简化格式 - 仅返回K线数据数组
            return {
                "success": True,
                "symbol": response.symbol,
                "timeframe": response.timeframe,
                "count": len(response.klines),
                "data": [
                    {
                        "timestamp": k.timestamp,
                        "datetime": k.datetime,
                        "open": k.open,
                        "high": k.high,
                        "low": k.low,
                        "close": k.close,
                        "volume": k.volume
                    }
                    for k in response.klines
                ]
            }
        else:
            # 完整格式 - 包含所有元数据
            result = response.to_dict()
            result["success"] = True

            # 添加警告信息
            if response.status == DataFetchStatus.PARTIAL:
                result["warning"] = response.error_message

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理K线请求失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )

@app.get("/batch_klines")
async def get_batch_klines(
    symbols: str = Query(..., description="品种列表，逗号分隔，例如: BINANCE:BTCUSDT,BINANCE:ETHUSDT"),
    timeframe: str = Query("15", description="时间框架"),
    count: int = Query(100, ge=1, le=5000, description="每个品种的K线数量"),
    quality: str = Query("production", description="质量等级"),
    use_cache: bool = Query(True, description="是否使用缓存")
):
    """
    批量获取多个品种的K线数据

    参数:
        - symbols: 品种列表（逗号分隔）
            例如: BINANCE:BTCUSDT,BINANCE:ETHUSDT,OANDA:XAUUSD

        - 其他参数同 /klines 接口

    返回:
        多个品种的K线数据数组

    示例:
        /batch_klines?symbols=BINANCE:BTCUSDT,BINANCE:ETHUSDT&timeframe=15&count=50
    """
    try:
        # 解析品种列表
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]

        if not symbol_list:
            raise HTTPException(status_code=400, detail="品种列表不能为空")

        if len(symbol_list) > 50:
            raise HTTPException(status_code=400, detail="一次最多批量获取50个品种")

        # 标准化时间框架
        timeframe_normalized = normalize_timeframe(timeframe)

        # 解析质量等级
        try:
            quality_level = KlineQualityLevel[quality.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"无效的质量等级: {quality}")

        # 创建批量请求
        requests = [
            KlineDataRequest(
                symbol=normalize_symbol(symbol),
                timeframe=timeframe_normalized,
                count=count,
                quality_level=quality_level,
                cache_enabled=use_cache
            )
            for symbol in symbol_list
        ]

        logger.info(f"📊 收到批量K线请求: {len(symbol_list)}个品种")

        # 批量获取
        responses = await kline_service.batch_fetch_klines(requests)

        # 格式化结果
        results = []
        for response in responses:
            results.append({
                "symbol": response.symbol,
                "timeframe": response.timeframe,
                "status": response.status.value,
                "count": len(response.klines),
                "quality_score": response.quality_score,
                "data": [
                    {
                        "timestamp": k.timestamp,
                        "datetime": k.datetime,
                        "open": k.open,
                        "high": k.high,
                        "low": k.low,
                        "close": k.close,
                        "volume": k.volume
                    }
                    for k in response.klines
                ],
                "error": response.error_message if response.status == DataFetchStatus.FAILED else None
            })

        return {
            "success": True,
            "total": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查"""
    if kline_service and kline_service.is_initialized:
        return {
            "status": "healthy",
            "service": "kline_api",
            "timestamp": datetime.now().isoformat(),
            "initialized": True
        }
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "kline_api",
                "timestamp": datetime.now().isoformat(),
                "initialized": False
            }
        )

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    if not kline_service:
        raise HTTPException(status_code=503, detail="服务未初始化")

    stats = kline_service.get_stats()

    return {
        "success": True,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# 辅助函数
# =============================================================================

def normalize_timeframe(timeframe: str) -> str:
    """
    标准化时间框架格式

    转换规则:
        1m, 1min -> 1
        5m, 5min -> 5
        15m, 15min -> 15
        30m, 30min -> 30
        1h, 1hour -> 60
        2h -> 120
        4h -> 240
        1d, 1day -> 1D
        1w, 1week -> 1W
        1M, 1month -> 1M
    """
    timeframe = timeframe.lower().strip()

    # 分钟格式
    if timeframe.endswith('m') or timeframe.endswith('min'):
        value = timeframe.replace('m', '').replace('min', '').strip()
        return value

    # 小时格式
    if timeframe.endswith('h') or timeframe.endswith('hour'):
        value = timeframe.replace('h', '').replace('hour', '').strip()
        try:
            hours = int(value)
            return str(hours * 60)  # 转换为分钟
        except ValueError:
            pass

    # 日线格式
    if timeframe.endswith('d') or timeframe.endswith('day'):
        return "1D"

    # 周线格式
    if timeframe.endswith('w') or timeframe.endswith('week'):
        return "1W"

    # 月线格式
    if timeframe.upper().endswith('M') or timeframe.endswith('month'):
        return "1M"

    # 已经是标准格式
    return timeframe

def normalize_symbol(symbol: str) -> str:
    """
    标准化品种格式

    规则:
        - 如果已有交易所前缀，保持不变
        - 如果没有前缀，默认添加BINANCE:
    """
    symbol = symbol.upper().strip()

    if ':' not in symbol:
        # 没有交易所前缀，默认BINANCE
        return f"BINANCE:{symbol}"

    return symbol

# =============================================================================
# 命令行启动
# =============================================================================

def main():
    """命令行启动"""
    import argparse

    parser = argparse.ArgumentParser(description="TradingView K线数据HTTP API服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 TradingView K线数据HTTP API服务")
    print("=" * 80)
    print(f"\n📡 服务地址: http://{args.host}:{args.port}")
    print(f"📚 API文档: http://{args.host}:{args.port}/docs")
    print(f"📊 ReDoc文档: http://{args.host}:{args.port}/redoc")
    print(f"\n示例请求:")
    print(f"  curl \"http://{args.host}:{args.port}/klines?symbol=OANDA:XAUUSD&timeframe=15&count=100\"")
    print(f"  curl \"http://{args.host}:{args.port}/klines?symbol=BTCUSDT&timeframe=15m&count=50\"")
    print(f"  curl \"http://{args.host}:{args.port}/health\"")
    print(f"  curl \"http://{args.host}:{args.port}/stats\"")
    print("\n" + "=" * 80)
    print("按 Ctrl+C 停止服务\n")

    # 启动服务
    uvicorn.run(
        "tradingview.kline_api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info"
    )

if __name__ == "__main__":
    main()