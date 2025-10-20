#!/usr/bin/env python3
"""
TradingView数据格式适配器
将TradingView数据转换为AKShare兼容格式
确保与现有业务代码100%兼容
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


class TradingViewFormatAdapter:
    """TradingView格式适配器 - 转换为AKShare兼容格式"""

    @staticmethod
    def to_akshare_format(tv_data: Dict[str, Any], symbol: str) -> Optional[pd.DataFrame]:
        """
        将TradingView数据转换为AKShare格式

        Args:
            tv_data: TradingView API返回的JSON数据
                {
                    "success": true,
                    "symbol": "SSE:600519",
                    "data": [
                        {
                            "timestamp": 1704182400,
                            "datetime": "2025-01-02T00:00:00",
                            "open": 1524.0,
                            "high": 1524.49,
                            "low": 1480.0,
                            "close": 1488.0,
                            "volume": 50029
                        }
                    ]
                }
            symbol: 原始股票代码 (如 "600519", "00700", "AAPL")

        Returns:
            DataFrame: AKShare格式的数据 (12列)
                列: 日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        """
        try:
            if not tv_data.get('success') or not tv_data.get('data'):
                logger.warning(f"TradingView数据为空或失败: {symbol}")
                return None

            klines = tv_data['data']
            if not klines:
                logger.warning(f"TradingView数据列表为空: {symbol}")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(klines)

            # 确保数据类型正确
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)

            # 时间转换: ISO格式 → "YYYY-MM-DD" 字符串
            df['日期'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')

            # 创建结果DataFrame，按AKShare列顺序
            result = pd.DataFrame()
            result['日期'] = df['日期']
            result['股票代码'] = symbol  # 使用原始代码，不是TradingView格式
            result['开盘'] = df['open'].astype(float)
            result['收盘'] = df['close'].astype(float)
            result['最高'] = df['high'].astype(float)
            result['最低'] = df['low'].astype(float)
            result['成交量'] = df['volume'].astype(int)

            # 计算衍生字段
            result = TradingViewFormatAdapter._calculate_derived_fields(result)

            # 确保列顺序与AKShare一致
            column_order = [
                '日期', '股票代码', '开盘', '收盘', '最高', '最低',
                '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
            ]
            result = result[column_order]

            logger.info(f"✅ TradingView格式转换成功: {symbol}, {len(result)}条数据")
            return result

        except Exception as e:
            logger.error(f"❌ TradingView格式转换失败: {symbol}, 错误: {e}")
            return None

    @staticmethod
    def _calculate_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算衍生字段（AKShare有但TradingView没有的字段）

        计算公式:
        - 成交额 = 成交量 × 均价（均价 = (开盘+收盘+最高+最低)/4）
        - 涨跌额 = 今收 - 昨收
        - 涨跌幅 = (涨跌额 / 昨收) × 100
        - 振幅 = ((最高 - 最低) / 昨收) × 100
        - 换手率 = 0（需要流通股本数据，TradingView不提供）
        """

        # 成交额 = 成交量 × 均价
        # 均价估算 = (最高 + 最低 + 开盘 + 收盘) / 4
        avg_price = (df['开盘'] + df['收盘'] + df['最高'] + df['最低']) / 4
        df['成交额'] = (df['成交量'] * avg_price).astype(float)

        # 计算昨收（前一天的收盘价）
        prev_close = df['收盘'].shift(1)

        # 涨跌额 = 今收 - 昨收
        df['涨跌额'] = (df['收盘'] - prev_close).fillna(0.0)

        # 涨跌幅 = (涨跌额 / 昨收) × 100
        df['涨跌幅'] = ((df['涨跌额'] / prev_close) * 100).fillna(0.0)

        # 振幅 = ((最高 - 最低) / 昨收) × 100
        df['振幅'] = (((df['最高'] - df['最低']) / prev_close) * 100).fillna(0.0)

        # 换手率 (暂时设为0，需要流通股本数据)
        df['换手率'] = 0.0

        # 第一行的衍生字段设为0（没有昨收）
        if len(df) > 0:
            df.loc[0, ['涨跌额', '涨跌幅', '振幅']] = 0.0

        # 替换inf和nan
        df = df.replace([np.inf, -np.inf], 0.0)
        df = df.fillna(0.0)

        # 确保数据类型正确
        float_columns = ['开盘', '收盘', '最高', '最低', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
        for col in float_columns:
            df[col] = df[col].astype(float)

        return df

    @staticmethod
    def validate_format(df: pd.DataFrame) -> bool:
        """
        验证DataFrame是否符合AKShare格式

        检查:
        1. 必须包含所有12列
        2. 列名必须匹配
        3. 数据类型必须正确
        """
        if df is None or df.empty:
            logger.error("验证失败: DataFrame为空")
            return False

        # 必需的列（按顺序）
        required_columns = [
            '日期', '股票代码', '开盘', '收盘', '最高', '最低',
            '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
        ]

        # 检查列名
        if list(df.columns) != required_columns:
            missing = [col for col in required_columns if col not in df.columns]
            extra = [col for col in df.columns if col not in required_columns]
            if missing:
                logger.error(f"缺少列: {missing}")
            if extra:
                logger.error(f"多余列: {extra}")
            logger.error(f"期望列顺序: {required_columns}")
            logger.error(f"实际列顺序: {list(df.columns)}")
            return False

        # 检查数据类型
        try:
            assert df['日期'].dtype == 'object', "日期列类型错误"
            assert df['股票代码'].dtype == 'object', "股票代码列类型错误"
            assert df['成交量'].dtype in [np.int64, np.int32], "成交量列类型错误"

            float_columns = ['开盘', '收盘', '最高', '最低', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
            for col in float_columns:
                assert df[col].dtype == np.float64, f"{col}列类型错误"

            logger.info("✅ 格式验证通过")
            return True

        except AssertionError as e:
            logger.error(f"❌ 数据类型验证失败: {e}")
            logger.error(f"实际数据类型:\n{df.dtypes}")
            return False


# 便捷函数
def convert_tradingview_to_akshare(tv_data: Dict, symbol: str) -> Optional[pd.DataFrame]:
    """
    便捷转换函数

    Args:
        tv_data: TradingView API返回的JSON数据
        symbol: 股票代码

    Returns:
        AKShare格式的DataFrame
    """
    return TradingViewFormatAdapter.to_akshare_format(tv_data, symbol)


def validate_akshare_format(df: pd.DataFrame) -> bool:
    """
    便捷验证函数

    Args:
        df: 待验证的DataFrame

    Returns:
        是否符合AKShare格式
    """
    return TradingViewFormatAdapter.validate_format(df)
