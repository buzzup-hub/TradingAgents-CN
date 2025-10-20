#!/usr/bin/env python3
"""
TradingView数据持久化管理器
提供多种数据保存方式：SQLite、CSV、JSON、Parquet
"""

import os
import json
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('agents')


class TradingViewDataPersistence:
    """TradingView数据持久化管理器"""

    def __init__(self, base_dir: str = "data/tradingview"):
        """
        初始化数据持久化管理器

        Args:
            base_dir: 数据存储根目录
        """
        self.base_dir = Path(base_dir)
        self.db_path = self.base_dir / "tradingview_data.db"
        self.csv_dir = self.base_dir / "csv"
        self.json_dir = self.base_dir / "json"
        self.parquet_dir = self.base_dir / "parquet"

        # 创建目录
        self._init_directories()

        # 初始化数据库
        self._init_database()

        logger.info(f"数据持久化管理器初始化: {self.base_dir}")

    def _init_directories(self):
        """初始化目录结构"""
        for directory in [self.base_dir, self.csv_dir, self.json_dir, self.parquet_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(str(self.db_path))

        # 创建历史数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL NOT NULL,
                close REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                volume INTEGER NOT NULL,
                amount REAL,
                amplitude REAL,
                change_pct REAL,
                change_amount REAL,
                turnover_rate REAL,
                source TEXT DEFAULT 'tradingview',
                fetched_at TEXT NOT NULL,
                UNIQUE(symbol, date)
            )
        """)

        # 创建原始数据表（保存TradingView原始JSON）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                data_json TEXT NOT NULL,
                quality_score REAL,
                fetched_at TEXT NOT NULL,
                count INTEGER NOT NULL
            )
        """)

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_history(symbol, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON stock_history(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON stock_history(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_symbol ON raw_data(symbol, timeframe)")

        conn.commit()
        conn.close()

        logger.info(f"SQLite数据库初始化完成: {self.db_path}")

    # ==================== SQLite 存储 ====================

    def save_to_sqlite(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        保存数据到SQLite

        Args:
            df: AKShare格式的DataFrame（12列）
            symbol: 股票代码

        Returns:
            是否保存成功
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            fetched_at = datetime.now().isoformat()

            # 准备数据
            records = []
            for _, row in df.iterrows():
                records.append((
                    symbol,
                    row['日期'],
                    float(row['开盘']),
                    float(row['收盘']),
                    float(row['最高']),
                    float(row['最低']),
                    int(row['成交量']),
                    float(row['成交额']),
                    float(row['振幅']),
                    float(row['涨跌幅']),
                    float(row['涨跌额']),
                    float(row['换手率']),
                    'tradingview',
                    fetched_at
                ))

            # 批量插入（使用INSERT OR REPLACE避免重复）
            conn.executemany("""
                INSERT OR REPLACE INTO stock_history
                (symbol, date, open, close, high, low, volume, amount,
                 amplitude, change_pct, change_amount, turnover_rate, source, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)

            conn.commit()
            conn.close()

            logger.info(f"✅ SQLite保存成功: {symbol}, {len(records)}条记录")
            return True

        except Exception as e:
            logger.error(f"❌ SQLite保存失败: {e}")
            return False

    def save_raw_to_sqlite(self, tv_data: Dict[str, Any], symbol: str, timeframe: str) -> bool:
        """
        保存TradingView原始数据到SQLite

        Args:
            tv_data: TradingView原始JSON数据
            symbol: 股票代码
            timeframe: 时间框架

        Returns:
            是否保存成功
        """
        try:
            conn = sqlite3.connect(str(self.db_path))

            data_json = json.dumps(tv_data, ensure_ascii=False)
            quality_score = tv_data.get('quality_score', 0.0)
            count = len(tv_data.get('data', []))
            fetched_at = datetime.now().isoformat()

            conn.execute("""
                INSERT INTO raw_data (symbol, timeframe, data_json, quality_score, fetched_at, count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, timeframe, data_json, quality_score, fetched_at, count))

            conn.commit()
            conn.close()

            logger.info(f"✅ 原始数据保存成功: {symbol} {timeframe}, {count}条")
            return True

        except Exception as e:
            logger.error(f"❌ 原始数据保存失败: {e}")
            return False

    # ==================== CSV 存储 ====================

    def save_to_csv(self, df: pd.DataFrame, symbol: str, append: bool = True) -> bool:
        """
        保存数据到CSV文件

        Args:
            df: AKShare格式的DataFrame
            symbol: 股票代码
            append: 是否追加模式（True追加，False覆盖）

        Returns:
            是否保存成功
        """
        try:
            csv_file = self.csv_dir / f"{symbol}.csv"

            if append and csv_file.exists():
                # 追加模式：读取现有数据，合并去重
                existing_df = pd.read_csv(csv_file)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                # 按日期去重，保留最新的
                combined_df = combined_df.drop_duplicates(subset=['日期'], keep='last')
                combined_df = combined_df.sort_values('日期')
                combined_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            else:
                # 覆盖模式
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')

            logger.info(f"✅ CSV保存成功: {csv_file}, {len(df)}条记录")
            return True

        except Exception as e:
            logger.error(f"❌ CSV保存失败: {e}")
            return False

    def save_daily_csv(self, df: pd.DataFrame, date: str = None) -> bool:
        """
        按日期保存CSV（每日一个文件）

        Args:
            df: 数据
            date: 日期（YYYY-MM-DD），不提供则使用今天

        Returns:
            是否保存成功
        """
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            daily_dir = self.csv_dir / "daily"
            daily_dir.mkdir(exist_ok=True)

            csv_file = daily_dir / f"{date}.csv"

            # 如果文件存在，追加并去重
            if csv_file.exists():
                existing_df = pd.read_csv(csv_file)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['股票代码', '日期'], keep='last')
                combined_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            else:
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')

            logger.info(f"✅ 每日CSV保存成功: {csv_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 每日CSV保存失败: {e}")
            return False

    # ==================== JSON 存储 ====================

    def save_to_json(self, tv_data: Dict[str, Any], symbol: str,
                     timeframe: str = "1D") -> bool:
        """
        保存原始TradingView数据到JSON

        Args:
            tv_data: TradingView原始数据
            symbol: 股票代码
            timeframe: 时间框架

        Returns:
            是否保存成功
        """
        try:
            # 按品种创建子目录
            symbol_dir = self.json_dir / symbol.replace(':', '_')
            symbol_dir.mkdir(exist_ok=True)

            # 文件名包含时间戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = symbol_dir / f"{timeframe}_{timestamp}.json"

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(tv_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ JSON保存成功: {json_file}")
            return True

        except Exception as e:
            logger.error(f"❌ JSON保存失败: {e}")
            return False

    # ==================== Parquet 存储 ====================

    def save_to_parquet(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        保存数据到Parquet格式（高效压缩，适合大数据）

        Args:
            df: 数据
            symbol: 股票代码

        Returns:
            是否保存成功
        """
        try:
            parquet_file = self.parquet_dir / f"{symbol}.parquet"

            # Parquet格式需要优化列类型
            df_copy = df.copy()
            df_copy['日期'] = pd.to_datetime(df_copy['日期'])

            df_copy.to_parquet(parquet_file, engine='pyarrow', compression='snappy')

            logger.info(f"✅ Parquet保存成功: {parquet_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Parquet保存失败: {e}")
            return False

    # ==================== 数据读取 ====================

    def load_from_sqlite(self, symbol: str, start_date: str = None,
                        end_date: str = None) -> Optional[pd.DataFrame]:
        """
        从SQLite读取数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame或None
        """
        try:
            conn = sqlite3.connect(str(self.db_path))

            query = "SELECT * FROM stock_history WHERE symbol = ?"
            params = [symbol]

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " ORDER BY date"

            df = pd.read_sql_query(query, conn, params=params)
            conn.close()

            if df.empty:
                logger.warning(f"未找到数据: {symbol}")
                return None

            # 转换为AKShare格式
            result = pd.DataFrame()
            result['日期'] = df['date']
            result['股票代码'] = df['symbol']
            result['开盘'] = df['open']
            result['收盘'] = df['close']
            result['最高'] = df['high']
            result['最低'] = df['low']
            result['成交量'] = df['volume']
            result['成交额'] = df['amount']
            result['振幅'] = df['amplitude']
            result['涨跌幅'] = df['change_pct']
            result['涨跌额'] = df['change_amount']
            result['换手率'] = df['turnover_rate']

            logger.info(f"✅ SQLite读取成功: {symbol}, {len(result)}条")
            return result

        except Exception as e:
            logger.error(f"❌ SQLite读取失败: {e}")
            return None

    def load_from_csv(self, symbol: str) -> Optional[pd.DataFrame]:
        """从CSV读取数据"""
        try:
            csv_file = self.csv_dir / f"{symbol}.csv"

            if not csv_file.exists():
                logger.warning(f"CSV文件不存在: {csv_file}")
                return None

            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            logger.info(f"✅ CSV读取成功: {csv_file}, {len(df)}条")
            return df

        except Exception as e:
            logger.error(f"❌ CSV读取失败: {e}")
            return None

    # ==================== 统计和管理 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            conn = sqlite3.connect(str(self.db_path))

            # 统计SQLite数据
            cursor = conn.execute("""
                SELECT
                    COUNT(DISTINCT symbol) as symbol_count,
                    COUNT(*) as total_records,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    MAX(fetched_at) as last_fetch
                FROM stock_history
            """)
            sqlite_stats = cursor.fetchone()

            # 统计原始数据
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as raw_records,
                    SUM(count) as total_klines
                FROM raw_data
            """)
            raw_stats = cursor.fetchone()

            conn.close()

            # 统计文件
            csv_count = len(list(self.csv_dir.glob("*.csv")))
            json_count = len(list(self.json_dir.rglob("*.json")))
            parquet_count = len(list(self.parquet_dir.glob("*.parquet")))

            return {
                'sqlite': {
                    'symbols': sqlite_stats[0],
                    'records': sqlite_stats[1],
                    'earliest_date': sqlite_stats[2],
                    'latest_date': sqlite_stats[3],
                    'last_fetch': sqlite_stats[4],
                    'raw_records': raw_stats[0],
                    'total_klines': raw_stats[1]
                },
                'files': {
                    'csv_files': csv_count,
                    'json_files': json_count,
                    'parquet_files': parquet_count
                },
                'storage_dir': str(self.base_dir)
            }

        except Exception as e:
            logger.error(f"❌ 获取统计失败: {e}")
            return {}

    def export_all_to_csv(self, output_file: str = None) -> bool:
        """导出所有SQLite数据到单个CSV"""
        try:
            if output_file is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = self.csv_dir / f"all_data_{timestamp}.csv"

            conn = sqlite3.connect(str(self.db_path))
            df = pd.read_sql_query("SELECT * FROM stock_history ORDER BY symbol, date", conn)
            conn.close()

            df.to_csv(output_file, index=False, encoding='utf-8-sig')

            logger.info(f"✅ 全量导出成功: {output_file}, {len(df)}条")
            return True

        except Exception as e:
            logger.error(f"❌ 全量导出失败: {e}")
            return False


# 便捷函数
def get_persistence_manager(base_dir: str = "data/tradingview") -> TradingViewDataPersistence:
    """获取持久化管理器实例"""
    return TradingViewDataPersistence(base_dir)
