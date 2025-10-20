"""
图表指标研究模块
"""
import json
import asyncio
from typing import Dict, Any, Callable, List, Optional
from ..utils import gen_session_id
from ..protocol import parse_compressed
from .graphic_parser import graphic_parse

from config.logging_config import get_logger
logger = get_logger(__name__)

class ChartStudy:
    """
    图表指标研究类
    """
    def __init__(self, chart_session, indicator):
        """
        初始化图表指标研究
        
        Args:
            chart_session: 图表会话
            indicator: 指标对象
        """
        from ..classes import PineIndicator, BuiltInIndicator
        
        if not isinstance(indicator, (PineIndicator, BuiltInIndicator)):
            raise TypeError("指标参数必须是PineIndicator或BuiltInIndicator的实例。"
                           "请使用'TradingView.get_indicator()'函数。")
            
        self.instance = indicator
        self._study_id = gen_session_id('st')
        self._study_listeners = chart_session._study_listeners
        self._chart_session = chart_session
        
        # 初始化数据
        self._periods = {}
        self._indexes = []
        self._graphic = {}
        self._strategy_report = {
            'trades': [],
            'history': {},
            'performance': {},
        }
        
        # 回调函数
        self._callbacks = {
            'study_completed': [],
            'update': [],
            'event': [],
            'error': []
        }
        
        # 设置监听器
        self._study_listeners[self._study_id] = self._handle_study_data
        
        # 创建指标 - 异步创建任务
        self._create_study_task = asyncio.create_task(
            chart_session._client.send('create_study', [
                chart_session._session_id,
                self._study_id,
                'st1',
                '$prices',
                self.instance.type,
                self._get_inputs(self.instance),
            ])
        )
    
    def _get_inputs(self, options):
        """
        获取指标输入参数
        
        Args:
            options: 指标对象
            
        Returns:
            dict: 输入参数
        """
        from ..classes import PineIndicator
        
        if isinstance(options, PineIndicator):
            pine_inputs = {'text': options.script}
            
            if options.pine_id:
                pine_inputs['pineId'] = options.pine_id
                
            if options.pine_version:
                pine_inputs['pineVersion'] = options.pine_version
                
            for n, (input_id, input_obj) in enumerate(options.inputs.items()):
                pine_inputs[input_id] = {
                    'v': input_obj['value'] if input_obj['type'] != 'color' else n,
                    'f': input_obj.get('isFake', False),
                    't': input_obj['type']
                }
                
            return pine_inputs
        
        return options.options
    
    async def _handle_study_data(self, packet):
        """
        处理指标数据
        
        Args:
            packet: 数据包
        """
        # 指标完成
        if packet['type'] == 'study_completed':
            self._handle_event('study_completed')
            return
            
        # 时间刻度更新
        if packet['type'] in ['timescale_update', 'du']:
            changes = []
            data = packet['data'][1].get(self._study_id, {})
            
            # 处理指标数据
            if data and data.get('st') and data['st'][0]:
                for p in data['st']:
                    period = {}
                    
                    for i, plot in enumerate(p['v']):
                        if not hasattr(self.instance, 'plots') or not self.instance.plots:
                            period['$time' if i == 0 else f'plot_{i-1}'] = plot
                        else:
                            plot_name = '$time' if i == 0 else self.instance.plots.get(f'plot_{i-1}')
                            if plot_name and plot_name not in period:
                                period[plot_name] = plot
                            else:
                                period[f'plot_{i-1}'] = plot
                                
                    self._periods[p['v'][0]] = period
                    
                changes.append('plots')
            
            # 处理图形数据
            if data.get('ns') and data['ns'].get('d'):
                try:
                    parsed = json.loads(data['ns'].get('d', '{}'))
                    
                    if parsed.get('graphicsCmds'):
                        # 处理图形命令
                        if parsed['graphicsCmds'].get('erase'):
                            for instruction in parsed['graphicsCmds']['erase']:
                                if instruction['action'] == 'all':
                                    if not instruction.get('type'):
                                        self._graphic = {}
                                    else:
                                        if instruction['type'] in self._graphic:
                                            del self._graphic[instruction['type']]
                                elif instruction['action'] == 'one':
                                    if instruction['type'] in self._graphic and instruction['id'] in self._graphic[instruction['type']]:
                                        del self._graphic[instruction['type']][instruction['id']]
                        
                        # 处理创建命令
                        if parsed['graphicsCmds'].get('create'):
                            for draw_type, groups in parsed['graphicsCmds']['create'].items():
                                if draw_type not in self._graphic:
                                    self._graphic[draw_type] = {}
                                    
                                for group in groups:
                                    if isinstance(group, dict) and 'data' in group:
                                        for item in group['data']:
                                            self._graphic[draw_type][item['id']] = item
                        
                        changes.append('graphic')
                    
                    # 更新策略报告
                    if parsed.get('dataCompressed'):
                        try:
                            decompressed = await parse_compressed(parsed['dataCompressed'])
                            if decompressed and decompressed.get('report'):
                                await self._update_strategy_report(decompressed['report'], changes)
                        except Exception as e:
                            self._handle_error(f"解析压缩数据出错: {str(e)}")
                    
                    if parsed.get('data') and parsed['data'].get('report'):
                        await self._update_strategy_report(parsed['data']['report'], changes)
                    
                except json.JSONDecodeError:
                    self._handle_error("解析JSON数据出错")
            
            # 更新索引
            if data.get('ns') and data['ns'].get('indexes') and isinstance(data['ns']['indexes'], list):
                self._indexes = data['ns']['indexes']
            
            # 触发更新事件
            if changes:
                self._handle_event('update', changes)
            
        # 指标错误
        elif packet['type'] == 'study_error':
            error_msg = f"指标错误: {packet['data'][3]}" if len(packet['data']) > 3 else "未知指标错误"
            self._handle_error(error_msg)
    
    async def _update_strategy_report(self, report, changes):
        """
        更新策略报告数据
        
        Args:
            report: 报告数据
            changes: 变更列表
        """
        if report.get('currency'):
            self._strategy_report['currency'] = report['currency']
            changes.append('report.currency')
            
        if report.get('settings'):
            self._strategy_report['settings'] = report['settings']
            changes.append('report.settings')
            
        if report.get('performance'):
            self._strategy_report['performance'] = report['performance']
            changes.append('report.perf')
            
        if report.get('trades'):
            self._strategy_report['trades'] = self._parse_trades(report['trades'])
            changes.append('report.trades')
            
        if report.get('equity'):
            self._strategy_report['history'] = {
                'buyHold': report.get('buyHold'),
                'buyHoldPercent': report.get('buyHoldPercent'),
                'drawDown': report.get('drawDown'),
                'drawDownPercent': report.get('drawDownPercent'),
                'equity': report.get('equity'),
                'equityPercent': report.get('equityPercent'),
            }
            changes.append('report.history')
    
    def _parse_trades(self, trades):
        """
        解析交易数据
        
        Args:
            trades: 交易数据
            
        Returns:
            list: 解析后的交易列表
        """
        return [
            {
                'entry': {
                    'name': t['e']['c'],
                    'type': 'short' if t['e']['tp'][0] == 's' else 'long',
                    'value': t['e']['p'],
                    'time': t['e']['tm'],
                },
                'exit': {
                    'name': t['x']['c'],
                    'value': t['x']['p'],
                    'time': t['x']['tm'],
                },
                'quantity': t['q'],
                'profit': t['tp'],
                'cumulative': t['cp'],
                'runup': t['rn'],
                'drawdown': t['dd'],
            }
            for t in reversed(trades)
        ]
    
    def _handle_event(self, event, *data):
        """
        处理事件
        
        Args:
            event: 事件类型
            data: 事件数据
        """
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
    def periods(self):
        """获取周期数据"""
        from types import SimpleNamespace
        
        # 创建一个有属性访问的对象列表
        periods_list = []
        for period_data in sorted(self._periods.values(), key=lambda p: p.get('$time', 0), reverse=True):
            # 创建SimpleNamespace对象，将字典键值对转为属性
            period = SimpleNamespace()
            
            # 设置基本属性
            period.time = period_data.get('$time', 0)
            
            # 为所有plot_N属性设置默认值为None
            for i in range(10):  # 假设最多有10个plot属性
                setattr(period, f'plot_{i}', None)
            
            # 添加所有其他属性
            for key, value in period_data.items():
                if key != '$time':
                    # 转换属性名
                    attr_name = key
                    if key.startswith('plot_'):
                        attr_name = key  # 保持plot_N格式
                        
                    setattr(period, attr_name, value)
            
            periods_list.append(period)
        
        return periods_list
    
    @property
    def graphic(self):
        """获取图形数据"""
        # 创建翻译表
        translator = {}
        
        chart_indexes = getattr(self._chart_session, 'indexes', {})
        sorted_indexes = sorted(chart_indexes.keys(), key=lambda k: chart_indexes[k], reverse=True)
        
        for n, r in enumerate(sorted_indexes):
            translator[r] = n
            
        indexes = [translator.get(i, 0) for i in self._indexes]
        return graphic_parse(self._graphic, indexes)
    
    @property
    def strategy_report(self):
        """获取策略报告"""
        return self._strategy_report
    
    async def set_indicator(self, indicator):
        """
        设置指标
        
        Args:
            indicator: 新的指标对象
        """
        from ..classes import PineIndicator, BuiltInIndicator
        
        if not isinstance(indicator, (PineIndicator, BuiltInIndicator)):
            raise TypeError("指标参数必须是PineIndicator或BuiltInIndicator的实例。"
                           "请使用'TradingView.get_indicator()'函数。")
        
        self.instance = indicator
        
        await self._chart_session._client.send('modify_study', [
            self._chart_session._session_id,
            self._study_id,
            'st1',
            self._get_inputs(self.instance),
        ])
    
    def on_ready(self, callback):
        """
        添加就绪回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['study_completed'].append(callback)
    
    def on_update(self, callback):
        """
        添加更新回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['update'].append(callback)
    
    def on_error(self, callback):
        """
        添加错误回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['error'].append(callback)
    
    async def remove(self):
        """移除指标研究"""
        await self._chart_session._client.send('remove_study', [
            self._chart_session._session_id,
            self._study_id,
        ])
        if self._study_id in self._study_listeners:
            del self._study_listeners[self._study_id] 