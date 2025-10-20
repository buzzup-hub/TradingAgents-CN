"""
图表会话模块
"""
import json
import time
import asyncio
from typing import Dict, Any, Callable, List, Optional
from ..utils import gen_session_id
from .study import ChartStudy

from config.logging_config import get_logger
logger = get_logger(__name__)

class ChartSession:
    """
    图表会话类
    """
    def __init__(self, client):
        """
        初始化图表会话
        
        Args:
            client: 客户端实例
        """
        self._session_id = gen_session_id('cs')
        self._replay_session_id = gen_session_id('rs')
        self._client = client
        self._study_listeners = {}
        
        # 回放模式属性
        self._replay_active = False
        self._replay_ok_cb = {}
        
        # 创建会话
        self._client.sessions[self._session_id] = {
            'type': 'chart',
            'on_data': self._on_session_data
        }
        
        # 回放会话
        self._client.sessions[self._replay_session_id] = {
            'type': 'replay',
            'on_data': self._on_replay_data
        }
        
        # 初始化数据
        self._periods = {}
        self._infos = {}
        self._indexes = {}
        self._timezone = 'Etc/UTC'
        self._symbol = 'BITSTAMP:BTCUSD'
        self._timeframe = '240'
        
        # 系列管理
        self._series_created = False
        self._current_series = 0
        
        # 回调函数
        self._callbacks = {
            'symbol_loaded': [],
            'update': [],
            'replay_loaded': [],
            'replay_resolution': [],
            'replay_end': [],
            'replay_point': [],
            'event': [],
            'error': []
        }
        
        # 创建图表会话
        self._create_session_task = asyncio.create_task(self._client.send('chart_create_session', [self._session_id]))
        
        # 创建研究类
        self.Study = lambda indicator: ChartStudy(self, indicator)
        
    def _on_session_data(self, packet):
        """
        处理会话数据
        
        Args:
            packet: 数据包
        """
        try:
            # 如果是研究数据
            if isinstance(packet['data'], list) and len(packet['data']) > 1 and isinstance(packet['data'][1], str) and packet['data'][1] in self._study_listeners:
                study_id = packet['data'][1]
                self._study_listeners[study_id](packet)
                return
                
            # 处理符号解析
            if packet['type'] == 'symbol_resolved':
                self._infos = {
                    'series_id': packet['data'][1],
                    **packet['data'][2]
                }
                
                self._handle_event('symbol_loaded')
                return
                
            # 处理时间刻度更新
            if packet['type'] in ['timescale_update', 'du']:
                changes = []
                
                if isinstance(packet['data'], list) and len(packet['data']) > 1:
                    for k in packet['data'][1].keys():
                        changes.append(k)
                        
                        if k == '$prices':
                            periods = packet['data'][1]['$prices']
                            if not periods or 's' not in periods:
                                continue
                                
                            # {"i":2,"v":[1754297700.0,3359.56,3359.925,3358.205,3358.605,696.0]}
                            for p in periods['s']:
                                if 'i' in p and 'v' in p:
                                    if len(p['v']) >= 6:  # 确保有足够的数据点
                                        self._indexes[p['i']] = p['v'][0]
                                        self._periods[p['v'][0]] = {
                                            'time': p['v'][0],
                                            'open': p['v'][1],
                                            'close': p['v'][4],
                                            'max': p['v'][2],
                                            'min': p['v'][3],
                                            'high': p['v'][2],  # 别名
                                            'low': p['v'][3],   # 别名
                                            'volume': round(p['v'][5] * 100) / 100 if len(p['v']) > 5 else 0,
                                        }
                            
                            continue
                            
                        if k in self._study_listeners:
                            self._study_listeners[k](packet)
                    
                    self._handle_event('update', changes)
                    return
                
            # 处理符号错误
            if packet['type'] == 'symbol_error':
                self._handle_error(f"({packet['data'][1]}) Symbol error:", packet['data'][2])
                return
                
            # 处理系列错误
            if packet['type'] == 'series_error':
                self._handle_error('Series error:', packet['data'][3])
                return
                
            # 处理关键错误
            if packet['type'] == 'critical_error':
                name, description = None, None
                if len(packet['data']) > 1:
                    name = packet['data'][1]
                if len(packet['data']) > 2:
                    description = packet['data'][2]
                self._handle_error('Critical error:', name, description)
                return
                
        except Exception as e:
            self._handle_error(f"处理会话数据错误: {str(e)}")
            
    def _on_replay_data(self, packet):
        """
        处理回放会话数据
        
        Args:
            packet: 数据包
        """
        try:
            if packet['type'] == 'replay_ok':
                # 处理回放确认
                if packet['data'][1] in self._replay_ok_cb:
                    self._replay_ok_cb[packet['data'][1]]()
                    del self._replay_ok_cb[packet['data'][1]]
                return
                
            if packet['type'] == 'replay_instance_id':
                self._handle_event('replay_loaded', packet['data'][1])
                return
                
            if packet['type'] == 'replay_point':
                self._handle_event('replay_point', packet['data'][1])
                return
                
            if packet['type'] == 'replay_resolutions':
                self._handle_event('replay_resolution', packet['data'][1], packet['data'][2])
                return
                
            if packet['type'] == 'replay_data_end':
                self._handle_event('replay_end')
                return
                
            if packet['type'] == 'critical_error':
                name, description = packet['data'][1], packet['data'][2]
                self._handle_error('Critical error:', name, description)
                return
        except Exception as e:
            self._handle_error(f"处理回放数据错误: {str(e)}")
            
    def _handle_timescale_update(self, packet):
        """
        处理时间刻度更新
        
        Args:
            packet: 数据包
        """
        try:
            # 获取数据
            if not packet['data'] or len(packet['data']) < 2:
                return
            
            data = packet['data'][1]
            changes = []
            
            # 兼容不同格式的数据
            if isinstance(data, dict):
                # 尝试直接访问数据
                if 'sds_1' in data:
                    data = data['sds_1']
                elif '$prices' in data:
                    # 处理 $prices 格式
                    if 's' in data['$prices']:
                        periods_data = data['$prices']['s']
                        for period in periods_data:
                            if 'v' in period and len(period['v']) >= 5:
                                time_value = period['v'][0]
                                self._periods[time_value] = {
                                    'time': time_value,
                                    'open': period['v'][1],
                                    'high': period['v'][2],
                                    'low': period['v'][3],
                                    'close': period['v'][4],
                                    'volume': period['v'][5] if len(period['v']) > 5 else 0
                                }
                        changes.append('periods')
                
                # 更新K线周期数据
                if 's' in data:
                    for candle in data['s']:
                        # 兼容不同格式
                        if 'i' in candle and 'v' in candle:
                            time_value = candle['i'][0] if isinstance(candle['i'], list) else candle['i']
                            
                            values = candle['v']
                            if len(values) >= 4:
                                self._periods[time_value] = {
                                    'time': time_value,
                                    'open': values[0],
                                    'high': values[1],
                                    'low': values[2],
                                    'close': values[3],
                                    'volume': values[4] if len(values) > 4 else 0
                                }
                        
                    changes.append('periods')
                    
                # 更新索引数据
                if 'indexes' in data:
                    old_index_count = len(self._indexes)
                    
                    for i in range(len(data['indexes'])):
                        self._indexes[i] = data['indexes'][i]
                        
                    if len(self._indexes) != old_index_count:
                        changes.append('indexes')
                        
                # 更新其他信息
                if 'ns' in data and 'i' in data['ns']:
                    for k, v in data['ns']['i'].items():
                        if k not in self._infos or self._infos[k] != v:
                            self._infos[k] = v
                            changes.append(f'info.{k}')
            
            # 触发更新事件
            if changes:
                self._handle_event('update', changes)
        except Exception as e:
            self._handle_error(f"处理时间刻度更新出错: {str(e)}")
            
    def _handle_symbol_resolved(self, packet):
        """
        处理符号解析结果
        
        Args:
            packet: 数据包
        """
        try:
            # 尝试兼容新旧格式
            if len(packet['data']) >= 3:
                if packet['data'][1] == 'sds_1':
                    if isinstance(packet['data'][2], dict):
                        # 新格式，直接使用字典
                        self._infos = packet['data'][2]
                    elif isinstance(packet['data'][2], str) and packet['data'][2].startswith('{'):
                        # JSON 字符串，需要解析
                        try:
                            self._infos = json.loads(packet['data'][2])
                        except json.JSONDecodeError:
                            pass
                    
                    self._handle_event('symbol_loaded')
                    return
        except Exception as e:
            self._handle_error(f"处理符号解析结果出错: {str(e)}")
            
        # 如果上面的处理失败，尝试旧方法
        try:
            if packet['data'][1] == 'sds_1':
                if isinstance(packet['data'][2], dict) and 'v' in packet['data'][2]:
                    # 符号解析成功
                    if packet['data'][2]['v']:
                        self._symbol = packet['data'][2].get('n', self._symbol)
                        self._handle_event('symbol_loaded')
                    else:
                        # 符号解析失败
                        self._handle_error('Symbol not found', self._symbol)
        except Exception as e:
            self._handle_error(f"处理符号解析结果出错: {str(e)}")
            
    def _handle_event(self, event, *data):
        """
        处理事件
        
        Args:
            event: 事件类型
            data: 事件数据
        """
        # 为了兼容示例程序中的回调函数，特殊处理 'update' 事件
        if event == 'update':
            for callback in self._callbacks[event]:
                try:
                    # 检查回调函数是否接受参数
                    import inspect
                    if inspect.signature(callback).parameters:
                        callback(*data)
                    else:
                        # 如果回调不接受参数，则直接调用
                        callback()
                except Exception as e:
                    self._handle_error(f"回调函数错误: {str(e)}")
        else:
            # 其他事件正常处理
            for callback in self._callbacks[event]:
                callback(*data)
                
        for callback in self._callbacks['event']:
            callback(event, *data)
            
    def _handle_error(self, *msgs):
        """
        处理错误
        
        Args:
            msgs: 错误信息
        """
        if not self._callbacks['error']:
            # 修复格式化错误
            # 将msgs转换为字符串并合并
            error_msg = " ".join(str(msg) for msg in msgs)
            logger.error(f"ERROR: {error_msg}")
        else:
            self._handle_event('error', *msgs)
            
    @property
    def session_id(self):
        """获取会话ID"""
        return self._session_id
    
    @property
    def periods(self):
        """获取所有K线周期，与JavaScript版本一致，但返回属性对象"""
        from types import SimpleNamespace
        
        # 先用JavaScript逻辑获取排序后的周期数据
        sorted_periods = sorted(self._periods.values(), key=lambda p: p['time'], reverse=True)
        
        # 转换为带属性访问的对象
        periods_list = []
        for period_data in sorted_periods:
            # 创建SimpleNamespace对象
            period = SimpleNamespace()
            period.time = period_data['time']
            period.open = period_data['open']
            period.high = period_data['high']  # 高点
            period.max = period_data['high']   # 最高价别名
            period.low = period_data['low']    # 低点
            period.min = period_data['low']    # 最低价别名
            period.close = period_data['close']
            period.volume = period_data['volume']
            
            # 添加其他可能存在的属性
            for key, value in period_data.items():
                if key not in ['time', 'open', 'high', 'low', 'close', 'volume']:
                    setattr(period, key, value)
            
            periods_list.append(period)
        
        return periods_list
    
    @property
    def infos(self):
        """获取会话信息，符合JavaScript逻辑但提供属性访问"""
        from types import SimpleNamespace
        
        # 创建一个SimpleNamespace对象
        info_obj = SimpleNamespace()
        
        # 复制所有属性
        for key, value in self._infos.items():
            setattr(info_obj, key, value)
            
        # 添加一些常用属性，如果没有的话
        if not hasattr(info_obj, 'description'):
            info_obj.description = getattr(info_obj, 'name', self._symbol)
            
        if not hasattr(info_obj, 'exchange'):
            if ':' in self._symbol:
                info_obj.exchange = self._symbol.split(':')[0]
            else:
                info_obj.exchange = ""
                
        if not hasattr(info_obj, 'currency_id'):
            info_obj.currency_id = "USD"
        
        return info_obj
    
    @property
    def indexes(self):
        """获取索引"""
        return self._indexes
    
    def set_market(self, symbol, options=None):
        """
        设置市场（与JS版本兼容的方法）
        
        Args:
            symbol: 交易对代码
            options: 加载选项
        """
        if options is None:
            options = {}
            
        # 重置数据
        self._periods = {}
        
        # 回放模式处理
        if self._replay_active:
            self._replay_active = False
            asyncio.create_task(self._client.send('replay_delete_session', [self._replay_session_id]))
        
        # 创建异步任务
        async def load_market():
            # 先确保会话已创建
            if hasattr(self, '_create_session_task'):
                try:
                    await self._create_session_task
                except Exception as e:
                    self._handle_error(f"创建会话出错: {str(e)}")
            
            # 设置基本信息和符号初始化
            symbol_init = {
                'symbol': symbol or 'BTCEUR',
                'adjustment': options.get('adjustment', 'splits'),
            }
            
            # 添加可选参数
            if options.get('backadjustment'):
                symbol_init['backadjustment'] = 'default'
                
            if options.get('session'):
                symbol_init['session'] = options.get('session')
                
            if options.get('currency'):
                symbol_init['currency-id'] = options.get('currency')
                
            # 处理回放模式
            if options.get('replay'):
                if not self._replay_active:
                    self._replay_active = True
                    await self._client.send('replay_create_session', [self._replay_session_id])
                
                await self._client.send('replay_add_series', [
                    self._replay_session_id,
                    'req_replay_addseries',
                    f"={json.dumps(symbol_init)}",
                    options.get('timeframe', '240'),
                ])
                
                await self._client.send('replay_reset', [
                    self._replay_session_id,
                    'req_replay_reset',
                    options['replay'],
                ])
            
            # 处理复杂图表类型
            complex_chart = options.get('type') or options.get('replay')
            chart_init = {} if complex_chart else symbol_init
            
            if complex_chart:
                if options.get('replay'):
                    chart_init['replay'] = self._replay_session_id
                    
                chart_init['symbol'] = symbol_init
                
                if options.get('type'):
                    # 此处需要增加ChartTypes映射
                    chart_init['type'] = options.get('type')
                    chart_init['inputs'] = options.get('inputs', {})
            
            # 增加系列计数
            self._current_series += 1
            
            # 解析符号
            await self._client.send('resolve_symbol', [
                self._session_id,
                f"ser_{self._current_series}",
                f"={json.dumps(chart_init)}",
            ])
            
            # 设置系列
            self.set_series(
                options.get('timeframe', '240'),
                options.get('range', 100),
                options.get('to')
            )
        
        # 执行任务
        asyncio.create_task(load_market())
        
    def set_series(self, timeframe='240', range_val=100, reference=None):
        """
        设置系列（与JS版本兼容的方法）
        
        Args:
            timeframe: 时间周期
            range_val: 数据范围
            reference: 参考时间（时间戳）
        """
        # 检查是否已设置市场
        if self._current_series == 0:
            self._handle_error('请先设置市场再设置系列')
            return
            
        # 严格按照JavaScript版本的实现处理calc_range
        # JavaScript中是: const calcRange = !reference ? range : ['bar_count', reference, range];
        calc_range = range_val if reference is None else ['bar_count', reference, range_val]
            
        # 清空数据
        self._periods = {}
        
        # 创建异步任务
        async def setup_series():
            try:
                # 确定命令类型
                command = 'modify_series' if self._series_created else 'create_series'
                
                # 直接使用数值而不是数组形式的calc_range，更符合API期望
                params = [
                    self._session_id,
                    '$prices',
                    's1',
                    f"ser_{self._current_series}",
                    timeframe
                ]
                
                # 只在创建系列时添加范围参数
                if not self._series_created:
                    # 简化参数传递，避免嵌套数组
                    if isinstance(calc_range, list):
                        params.append(calc_range)
                    else:
                        params.append(calc_range)
                else:
                    params.append('')
                    
                await self._client.send(command, params)
                
                # 设置系列已创建标志
                self._series_created = True
            except Exception as e:
                self._handle_error(f"设置系列出错: {str(e)}")
        
        # 执行任务
        asyncio.create_task(setup_series())
        
    async def set_timezone(self, timezone):
        """
        设置时区
        
        Args:
            timezone: 时区
        """
        self._timezone = timezone
        await self._client.send('set_timezone', [
            self._session_id,
            timezone,
        ])
        
    async def fetch_more(self, number=1):
        """
        获取更多数据
        
        Args:
            number: 获取数量
        """
        await self._client.send('request_more_data', [self._session_id, 'sds_1', number])
        
    async def replay_step(self, number=1):
        """
        回放步进
        
        Args:
            number: 步进数量
        Returns:
            Promise: 数据获取完成后的Promise
        """
        if not self._replay_active:
            self._handle_error('No replay session')
            return
            
        # 创建Promise
        fut = asyncio.Future()
        
        req_id = gen_session_id('rsq_step')
        await self._client.send('replay_step', [self._replay_session_id, req_id, number])
        
        # 设置回调
        self._replay_ok_cb[req_id] = lambda: fut.set_result(None)
        
        return fut
        
    async def replay_start(self, interval=1000):
        """
        开始回放
        
        Args:
            interval: 时间间隔(毫秒)
        Returns:
            Promise: 回放开始后的Promise
        """
        if not self._replay_active:
            self._handle_error('No replay session')
            return
            
        # 创建Promise
        fut = asyncio.Future()
        
        req_id = gen_session_id('rsq_start')
        await self._client.send('replay_start', [self._replay_session_id, req_id, interval])
        
        # 设置回调
        self._replay_ok_cb[req_id] = lambda: fut.set_result(None)
        
        return fut
        
    async def replay_stop(self,):
        """
        停止回放
        
        Returns:
            Promise: 回放停止后的Promise
        """
        if not self._replay_active:
            self._handle_error('No replay session')
            return
            
        # 创建Promise
        fut = asyncio.Future()
        
        req_id = gen_session_id('rsq_stop')
        await self._client.send('replay_stop', [self._replay_session_id, req_id])
        
        # 设置回调
        self._replay_ok_cb[req_id] = lambda: fut.set_result(None)
        
        return fut
        
    def on_symbol_loaded(self, callback):
        """
        添加符号加载回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['symbol_loaded'].append(callback)
        
    def on_update(self, callback):
        """
        添加更新回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['update'].append(callback)
        
    def on_replay_loaded(self, callback):
        """
        添加回放加载回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['replay_loaded'].append(callback)
        
    def on_replay_resolution(self, callback):
        """
        添加回放分辨率回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['replay_resolution'].append(callback)
        
    def on_replay_end(self, callback):
        """
        添加回放结束回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['replay_end'].append(callback)
        
    def on_replay_point(self, callback):
        """
        添加回放点回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['replay_point'].append(callback)
        
    def on_error(self, callback):
        """
        添加错误回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['error'].append(callback)
        
    def delete(self):
        """删除会话（旧方法，保留向后兼容性）"""
        asyncio.create_task(self.remove())
        
    async def remove(self):
        """异步删除会话"""
        await self._client.send('chart_delete_session', [self._session_id])
        if self._session_id in self._client.sessions:
            del self._client.sessions[self._session_id]

    def load_symbol(self, symbol, options=None):
        """
        加载交易对（兼容方法，内部调用set_market）
        
        Args:
            symbol: 交易对代码
            options: 加载选项
        """
        self.set_market(symbol, options)
    
    async def get_historical_data(self, symbol: str, timeframe: str, count: int = 500) -> List[Dict]:
        """
        获取历史K线数据的便捷方法（采用成功示例的回调机制）
        
        Args:
            symbol: 交易对代码 (例如: "BINANCE:BTCUSDT")
            timeframe: 时间框架 (例如: "15m", "1h", "1D")
            count: 数据数量，默认500
            
        Returns:
            List[Dict]: K线数据列表
        """
        try:
            # 清理现有数据和回调
            self._periods = {}
            data_loaded = False
            result_data = []
            
            # 创建Future用于等待数据加载完成
            data_future = asyncio.Future()
            
            def on_symbol_loaded():
                """符号加载完成回调"""
                logger.debug(f"✅ 符号加载完成: {symbol}")
            
            def on_update():
                """数据更新回调 - 关键！"""
                nonlocal data_loaded, result_data
                
                if data_loaded or not self._periods:
                    return
                    
                logger.debug(f"📊 数据更新回调触发，periods数量: {len(self._periods)}")
                
                # 转换数据格式为转换器期望的格式
                klines = []
                for period in sorted(self._periods.values(), key=lambda p: p['time']):
                    klines.append({
                        'time': period['time'],  # 转换器期望的字段名
                        'open': period['open'],
                        'high': period['high'],
                        'low': period['low'],
                        'close': period['close'],
                        'volume': period.get('volume', 0)
                    })
                
                result_data = klines
                data_loaded = True
                
                # 完成Future
                if not data_future.done():
                    data_future.set_result(klines)
                    logger.info(f"✅ 获取到 {len(klines)} 条K线数据: {symbol} {timeframe}")
            
            def on_error(*msgs):
                """错误处理回调"""
                error_msg = " ".join(str(msg) for msg in msgs)
                logger.error(f"❌ ChartSession错误: {error_msg}")
                if not data_future.done():
                    data_future.set_exception(Exception(error_msg))
            
            # 注册回调（采用成功示例的方式）
            self.on_symbol_loaded(on_symbol_loaded)
            self.on_update(on_update)
            self.on_error(on_error)
            
            # 转换timeframe格式
            if timeframe.endswith('m'):
                tf_value = timeframe[:-1]
            elif timeframe.endswith('h'):
                tf_value = str(int(timeframe[:-1]) * 60)
            else:
                tf_value = timeframe
            
            logger.debug(f"🎯 设置市场: {symbol}, timeframe: {tf_value}, count: {count}")
            
            # 采用成功示例的方式：在set_market时设置所有参数
            self.set_market(symbol, {
                'timeframe': tf_value,
                'range': count
            })
            
            # 等待数据加载完成，设置合理的超时时间
            try:
                result = await asyncio.wait_for(data_future, timeout=15.0)
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ 获取数据超时: {symbol} {timeframe}")
                # 超时后仍尝试返回已有数据
                if self._periods:
                    logger.warning(f"⚠️ 超时但返回部分数据: {len(self._periods)} 条")
                    klines = []
                    for period in sorted(self._periods.values(), key=lambda p: p['time']):
                        klines.append({
                            'time': period['time'],  # 转换器期望的字段名
                            'open': period['open'],
                            'high': period['high'],
                            'low': period['low'],
                            'close': period['close'],
                            'volume': period.get('volume', 0)
                        })
                    return klines
                else:
                    raise Exception(f"获取数据超时且无数据: {symbol}")
            
        except Exception as e:
            logger.error(f"❌ 获取历史数据失败: {e}")
            raise e 