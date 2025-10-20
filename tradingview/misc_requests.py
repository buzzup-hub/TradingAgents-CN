"""
杂项请求模块
"""
import os
import re
import json
import platform
import aiohttp
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime

from .utils import gen_auth_cookies
from .classes import PineIndicator, BuiltInIndicator

from config.logging_config import get_logger
logger = get_logger(__name__)

# 全局变量
indicators = ['Recommend.Other', 'Recommend.All', 'Recommend.MA']
built_in_indic_list = []

async def fetch_scan_data(tickers=None, columns=None):
    """
    获取扫描数据
    
    Args:
        tickers: 交易对列表
        columns: 列字段列表
        
    Returns:
        dict: 扫描结果数据
    """
    if tickers is None:
        tickers = []
    if columns is None:
        columns = []
        
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'https://scanner.tradingview.com/global/scan',
            json={
                'symbols': {'tickers': tickers},
                'columns': columns
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            return await resp.json()

async def get_ta(symbol_id):
    """
    获取技术分析数据
    
    Args:
        symbol_id: 市场ID (例如: 'COINBASE:BTCEUR')
        
    Returns:
        dict: 技术分析结果
    """
    advice = {}
    
    # 创建列字段
    cols = []
    for t in ['1', '5', '15', '60', '240', '1D', '1W', '1M']:
        for i in indicators:
            cols.append(f"{i}|{t}" if t != '1D' else i)
    
    # 获取数据
    result = await fetch_scan_data([symbol_id], cols)
    if not result.get('data') or not result['data'][0]:
        return False
    
    # 处理数据
    for i, val in enumerate(result['data'][0]['d']):
        name, period = cols[i].split('|') if '|' in cols[i] else (cols[i], '1D')
        period_name = period
        
        if period_name not in advice:
            advice[period_name] = {}
            
        advice[period_name][name.split('.')[-1]] = round(val * 1000) / 500
    
    return advice

class SearchMarketResult:
    """市场搜索结果类"""
    def __init__(self, data):
        """
        初始化市场搜索结果
        
        Args:
            data: 市场数据
        """
        self.exchange = data['exchange']
        self.fullExchange = data['fullExchange']
        self.symbol = data['symbol']
        self.id = data['id']
        self.description = data['description']
        self.type = data['type']
    
    async def get_ta(self):
        """
        获取该市场的技术分析数据
        
        Returns:
            dict: 技术分析数据
        """
        return await get_ta(self.id)

async def search_market(search, filter=''):
    """
    查找交易对 (已弃用)
    
    Args:
        search: 关键词
        filter: 分类过滤
        
    Returns:
        list: 搜索结果列表
        
    已弃用: 请使用 search_market_v3 代替
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'https://symbol-search.tradingview.com/symbol_search',
            params={
                'text': search.replace(' ', '%20'),
                'type': filter
            },
            headers={
                'origin': 'https://www.tradingview.com'
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()
            
            results = []
            for s in data:
                exchange = s['exchange'].split(' ')[0]
                symbol_id = f"{exchange}:{s['symbol']}"
                
                results.append(SearchMarketResult({
                    'id': symbol_id,
                    'exchange': exchange,
                    'fullExchange': s['exchange'],
                    'symbol': s['symbol'],
                    'description': s['description'],
                    'type': s['type']
                }))
                
            return results

async def search_market_v3(search, filter=''):
    """
    查找交易对 (V3)
    
    Args:
        search: 关键词
        filter: 分类过滤
        
    Returns:
        list: 搜索结果列表
    """
    # 处理搜索文本
    splitted_search = search.upper().replace(' ', '+').split(':')
    
    params = {
        'text': splitted_search[-1],
        'search_type': filter
    }
    
    if len(splitted_search) == 2:
        params['exchange'] = splitted_search[0]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            'https://symbol-search.tradingview.com/symbol_search/v3',
            params=params,
            headers={
                'origin': 'https://www.tradingview.com'
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()

            # print("symbol-search: ",data)
            # {'symbols_remaining': 0, 'symbols': [{'symbol': 'XAUUSD', 'description': 'Gold', 'type': 'commodity', 'exchange': 'OANDA', 'currency_code': 'USD', 'currency-logoid': 'country/US', 'logoid': 'metal/gold', 'provider_id': 'oanda', 'source2': {'id': 'OANDA', 'name': 'OANDA', 'description': 'OANDA'}, 'source_id': 'OANDA', 'typespecs': ['cfd']}]}
            results = []
            for s in data.get('symbols', []):
                exchange = s['exchange'].split(' ')[0]
                symbol_id = s.get('prefix', f"{exchange.upper()}") + ':' + s['symbol']
                
                results.append(SearchMarketResult({
                    'id': symbol_id,
                    'exchange': exchange,
                    'fullExchange': s['exchange'],
                    'symbol': s['symbol'],
                    'description': s['description'],
                    'type': s['type']
                }))
                
            return results

class SearchIndicatorResult:
    """指标搜索结果类"""
    def __init__(self, data):
        """
        初始化指标搜索结果
        
        Args:
            data: 指标数据
        """
        self.id = data['id']
        self.version = data['version']
        self.name = data['name']
        self.author = data['author']
        self.image = data['image']
        self.source = data['source']
        self.type = data['type']
        self.access = data['access']
        self._session = data.get('_session', '')
        self._signature = data.get('_signature', '')
    
    async def get(self):
        """
        获取完整指标信息
        
        Returns:
            PineIndicator: 指标对象
        """
        return await get_indicator(
            self.id, 
            self.version, 
            self._session, 
            self._signature
        )

async def search_indicator(search=''):
    """
    查找指标
    
    Args:
        search: 搜索关键词
        
    Returns:
        list: 指标搜索结果列表
    """
    global built_in_indic_list
    
    # 如果内置指标列表为空，先获取内置指标
    if not built_in_indic_list:
        for indicator_type in ['standard', 'candlestick', 'fundamental']:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        'https://pine-facade.tradingview.com/pine-facade/list',
                        params={'filter': indicator_type},
                        headers={'Accept': 'application/json'} # 显式请求JSON格式
                    ) as resp:
                        if resp.status < 500:
                            try:
                                # 首先尝试获取文本内容
                                text_content = await resp.text()
                                try:
                                    # 然后尝试将文本解析为JSON
                                    data = json.loads(text_content)
                                    if isinstance(data, list):
                                        built_in_indic_list.extend(data)
                                except json.JSONDecodeError:
                                    logger.error(f"解析内置指标列表失败: {indicator_type}")
                            except Exception as e:
                                logger.error(f"获取内置指标列表出错: {str(e)}")
            except Exception as e:
                print(f"连接指标API失败: {str(e)}")
    
    # 获取公共脚本
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://www.tradingview.com/pubscripts-suggest-json',
                params={'search': search.replace(' ', '%20')},
                headers={'Accept': 'application/json'}
            ) as resp:
                if resp.status >= 500:
                    raise ValueError(f"服务器错误: {resp.status}")
                    
                try:
                    # 首先获取文本内容
                    text_content = await resp.text()
                    # 然后解析为JSON
                    public_data = json.loads(text_content)
                except json.JSONDecodeError:
                    # 如果无法解析，使用空结果
                    print("解析公共脚本列表失败")
                    public_data = {"results": []}
    except Exception as e:
        print(f"获取公共脚本列表失败: {str(e)}")
        public_data = {"results": []}
    
    # 标准化搜索文本函数
    def norm(s=''):
        return ''.join(c for c in s.upper() if c.isalpha())
    
    # 处理内置指标
    built_in_indicators = []
    for ind in built_in_indic_list:
        if (norm(ind.get('scriptName', '')).find(norm(search)) != -1 or 
            norm(ind.get('extra', {}).get('shortDescription', '')).find(norm(search)) != -1):
            built_in_indicators.append(SearchIndicatorResult({
                'id': ind['scriptIdPart'],
                'version': ind['version'],
                'name': ind['scriptName'],
                'author': {
                    'id': ind['userId'],
                    'username': '@TRADINGVIEW@'
                },
                'image': '',
                'access': 'closed_source',
                'source': '',
                'type': ind.get('extra', {}).get('kind', 'study')
            }))
    
    # 处理公共指标
    public_indicators = []
    for ind in public_data.get('results', []):
        public_indicators.append(SearchIndicatorResult({
            'id': ind['scriptIdPart'],
            'version': ind['version'],
            'name': ind['scriptName'],
            'author': {
                'id': ind['author']['id'],
                'username': ind['author']['username']
            },
            'image': ind.get('imageUrl', ''),
            'access': ['open_source', 'closed_source', 'invite_only'][ind['access'] - 1] if ind['access'] <= 3 else 'other',
            'source': ind.get('scriptSource', ''),
            'type': ind.get('extra', {}).get('kind', 'study')
        }))
    
    # 合并结果
    return built_in_indicators + public_indicators

async def get_indicator(indicator_id, version='last', session='', signature=''):
    """
    获取指标数据
    
    Args:
        indicator_id: 指标ID
        version: 指标版本
        session: 会话ID
        signature: 签名
        
    Returns:
        PineIndicator 或 BuiltInIndicator: 指标对象
    """
    # 检查内置指标类型
    if indicator_id.startswith('STD;'):
        # 内置指标处理
        indicator_type = indicator_id.replace('STD;', '')
        
        # 内置指标映射表
        std_indicators = {
            'RSI': 'RSI@tv-basicstudies-241',
            'SMA': 'MASimple@tv-basicstudies-241',
            'EMA': 'MAExp@tv-basicstudies-241',
            'MACD': 'MACD@tv-basicstudies-241',
            'BB': 'BB@tv-basicstudies-241',  # 布林带
            'VOLUME': 'Volume@tv-basicstudies-241',
            'STOCH': 'Stochastic@tv-basicstudies-241',
            'STOCHRSI': 'StochasticRSI@tv-basicstudies-241',
            'ADX': 'ADX@tv-basicstudies-241',
            'ATR': 'ATR@tv-basicstudies-241',
            'OBV': 'OBV@tv-basicstudies-241',
        }
        
        # 获取指标类型
        if indicator_type in std_indicators:
            indicator_full_type = std_indicators[indicator_type]
            try:
                # 创建内置指标
                return BuiltInIndicator(indicator_full_type)
            except ValueError as e:
                raise ValueError(f"创建内置指标 '{indicator_type}' 失败: {str(e)}")
        else:
            raise ValueError(f"不支持的内置指标类型: '{indicator_type}'")
    
    # Pine指标处理
    if indicator_id.startswith('PUB;') or indicator_id.startswith('PRIV;'):
        # 检查版本
        version = 'last' if version == 'last' else str(version)
        
        # 构建请求URL
        url = f"https://pine-facade.tradingview.com/pine-facade/get-study-source/{indicator_id.replace(';', '%3B')}/={version}"
        
        # 添加认证信息
        headers = {
            'origin': 'https://www.tradingview.com',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        if session and signature:
            headers['cookie'] = gen_auth_cookies(session, signature)
            
        # 请求指标数据
        try:
            async with aiohttp.ClientSession() as aio_session:
                async with aio_session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        raise ValueError(f"获取指标失败: HTTP {resp.status}")
                        
                    data = await resp.json()
                    
                    if 'error' in data:
                        raise ValueError(f"获取指标失败: {data['error']}")
                        
                    # 处理特殊字符
                    inputs = {}
                    plots = {}
                    
                    # 处理输入
                    for inp in data.get('inputs', []):
                        input_id = inp.get('id', '')
                        
                        inputs[input_id] = {
                            'name': inp.get('name', ''),
                            'inline': inp.get('inline', ''),
                            'internalID': inp.get('internalID', ''),
                            'tooltip': inp.get('tooltip', ''),
                            'type': inp.get('type', 'text'),
                            'value': inp.get('defval'),
                            'isHidden': inp.get('isHidden', False),
                            'isFake': inp.get('isFake', False),
                        }
                        
                        # 处理选项
                        if 'options' in inp:
                            inputs[input_id]['options'] = inp['options']
                            
                    # 处理输出
                    for plot in data.get('plots', []):
                        if 'id' in plot and 'target' in plot:
                            plots[plot['id']] = plot['target']
                            
                    # 创建指标对象
                    return PineIndicator({
                        'pineId': data.get('pineId', ''),
                        'pineVersion': data.get('pineVersion', ''),
                        'description': data.get('description', ''),
                        'shortDescription': data.get('shortDescription', ''),
                        'inputs': inputs,
                        'plots': plots,
                        'script': data.get('source', ''),
                    })
        except Exception as e:
            raise ValueError(f"获取指标失败: {str(e)}")
            
    # 普通Pine脚本处理
    return PineIndicator({
        'pineId': '',
        'pineVersion': '',
        'description': '自定义脚本',
        'shortDescription': '自定义',
        'inputs': {},
        'plots': {},
        'script': indicator_id,
    })

class User:
    """用户类"""
    def __init__(self, data):
        """
        初始化用户对象
        
        Args:
            data: 用户数据
        """
        self.id = data.get('id')
        self.username = data.get('username')
        self.first_name = data.get('firstName')
        self.last_name = data.get('lastName')
        self.reputation = data.get('reputation')
        self.following = data.get('following')
        self.followers = data.get('followers')
        self.notifications = data.get('notifications')
        self.session = data.get('session')
        self.signature = data.get('signature')
        self.session_hash = data.get('sessionHash')
        self.private_channel = data.get('privateChannel')
        self.auth_token = data.get('authToken')
        self.join_date = data.get('joinDate')

async def login_user(username, password, remember=True, ua=None):
    """
    通过用户名/邮箱和密码登录
    
    Args:
        username: 用户名/邮箱
        password: 密码
        remember: 是否记住会话 (默认: True)
        ua: 自定义User-Agent
        
    Returns:
        User: 用户对象
    """
    if ua is None:
        ua = 'TWAPI/3.0'
        
    # 构建User Agent
    platform_info = f"{platform.version()}; {platform.platform()}; {platform.machine()}"
    user_agent = f"{ua} ({platform_info})"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'https://www.tradingview.com/accounts/signin/',
            data=f"username={username}&password={password}{'' if not remember else '&remember=on'}",
            headers={
                'referer': 'https://www.tradingview.com',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-agent': user_agent
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()
            
            if data.get('error'):
                raise ValueError(data['error'])
            
            # 获取Cookie
            cookies = resp.headers.getall('Set-Cookie', [])
            session_cookie = next((c for c in cookies if 'sessionid=' in c), '')
            session_id = re.search(r'sessionid=(.*?);', session_cookie)
            session_id = session_id.group(1) if session_id else None
            
            sign_cookie = next((c for c in cookies if 'sessionid_sign=' in c), '')
            signature = re.search(r'sessionid_sign=(.*?);', sign_cookie)
            signature = signature.group(1) if signature else None
            
            # 创建用户对象
            return User({
                'id': data['user']['id'],
                'username': data['user']['username'],
                'firstName': data['user']['first_name'],
                'lastName': data['user']['last_name'],
                'reputation': data['user']['reputation'],
                'following': data['user']['following'],
                'followers': data['user']['followers'],
                'notifications': data['user']['notification_count'],
                'session': session_id,
                'signature': signature,
                'sessionHash': data['user']['session_hash'],
                'privateChannel': data['user']['private_channel'],
                'authToken': data['user']['auth_token'],
                'joinDate': data['user']['date_joined']
            })

async def get_user(session, signature='', location='https://www.tradingview.com/'):
    """
    通过会话ID获取用户信息
    
    Args:
        session: 会话ID
        signature: 会话签名
        location: 授权页面位置
        
    Returns:
        User: 用户对象
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(
            location,
            headers={
                'cookie': gen_auth_cookies(session, signature)
            },
            allow_redirects=False
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            # 如果有重定向，则跟随重定向
            if resp.status in (301, 302, 303, 307, 308) and 'location' in resp.headers:
                if resp.headers['location'] != location:
                    return await get_user(session, signature, resp.headers['location'])
            
            data = await resp.text()
            
            # 检查是否有认证令牌
            if 'auth_token' in data:
                # 使用正则表达式提取用户信息
                user_id = re.search(r'"id":([0-9]{1,10}),', data)
                username = re.search(r'"username":"(.*?)"', data)
                first_name = re.search(r'"first_name":"(.*?)"', data)
                last_name = re.search(r'"last_name":"(.*?)"', data)
                reputation = re.search(r'"reputation":(.*?),', data)
                following = re.search(r',"following":([0-9]*?),', data)
                followers = re.search(r',"followers":([0-9]*?),', data)
                notification_following = re.search(r'"notification_count":\{"following":([0-9]*),', data)
                notification_user = re.search(r'"notification_count":\{"following":[0-9]*,"user":([0-9]*)', data)
                session_hash = re.search(r'"session_hash":"(.*?)"', data)
                private_channel = re.search(r'"private_channel":"(.*?)"', data)
                auth_token = re.search(r'"auth_token":"(.*?)"', data)
                date_joined = re.search(r'"date_joined":"(.*?)"', data)
                
                try:
                    join_date = datetime.fromisoformat(date_joined.group(1)) if date_joined else None
                except (ValueError, AttributeError):
                    join_date = None
                
                return User({
                    'id': int(user_id.group(1)) if user_id else None,
                    'username': username.group(1) if username else None,
                    'firstName': first_name.group(1) if first_name else None,
                    'lastName': last_name.group(1) if last_name else None,
                    'reputation': float(reputation.group(1)) if reputation else 0,
                    'following': int(following.group(1)) if following else 0,
                    'followers': int(followers.group(1)) if followers else 0,
                    'notifications': {
                        'following': int(notification_following.group(1)) if notification_following else 0,
                        'user': int(notification_user.group(1)) if notification_user else 0,
                    },
                    'session': session,
                    'signature': signature,
                    'sessionHash': session_hash.group(1) if session_hash else None,
                    'privateChannel': private_channel.group(1) if private_channel else None,
                    'authToken': auth_token.group(1) if auth_token else None,
                    'joinDate': join_date,
                })
            
            raise ValueError('无效或过期的会话ID/签名')

async def get_private_indicators(session, signature=''):
    """
    获取用户私有指标
    
    Args:
        session: 会话ID
        signature: 会话签名
        
    Returns:
        list: 指标搜索结果列表
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(
            'https://pine-facade.tradingview.com/pine-facade/list',
            headers={
                'cookie': gen_auth_cookies(session, signature)
            },
            params={
                'filter': 'saved'
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()
            
            results = []
            for ind in data:
                results.append(SearchIndicatorResult({
                    'id': ind['scriptIdPart'],
                    'version': ind['version'],
                    'name': ind['scriptName'],
                    'author': {
                        'id': -1,
                        'username': '@ME@'
                    },
                    'image': ind.get('imageUrl', ''),
                    'access': 'private',
                    'source': ind.get('scriptSource', ''),
                    'type': ind.get('extra', {}).get('kind', 'study'),
                    '_session': session,
                    '_signature': signature
                }))
                
            return results

async def get_chart_token(layout, credentials=None):
    """
    获取图表Token
    
    Args:
        layout: 图表布局ID
        credentials: 用户凭证 (id, session, signature)
        
    Returns:
        str: Token
    """
    if credentials is None:
        credentials = {}
        
    # 提取用户凭证
    user_id = credentials.get('id', -1)
    session = credentials.get('session')
    signature = credentials.get('signature')
    
    async with aiohttp.ClientSession() as client:
        async with client.get(
            'https://www.tradingview.com/chart-token',
            headers={
                'cookie': gen_auth_cookies(session, signature)
            },
            params={
                'image_url': layout,
                'user_id': user_id
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()
            
            if not data.get('token'):
                raise ValueError('无效的布局或凭证')
                
            return data['token']

async def get_drawings(layout, symbol='', credentials=None, chart_id='_shared'):
    """
    获取图形绘制
    
    Args:
        layout: 图表布局ID
        symbol: 市场过滤
        credentials: 用户凭证
        chart_id: 图表ID
        
    Returns:
        list: 绘制列表
    """
    # 获取图表Token
    chart_token = await get_chart_token(layout, credentials)
    
    async with aiohttp.ClientSession() as client:
        async with client.get(
            f"https://charts-storage.tradingview.com/charts-storage/get/layout/{layout}/sources",
            params={
                'chart_id': chart_id,
                'jwt': chart_token,
                'symbol': symbol
            }
        ) as resp:
            if resp.status >= 500:
                raise ValueError(f"服务器错误: {resp.status}")
                
            data = await resp.json()
            
            if not data.get('payload'):
                raise ValueError('无效的布局、用户凭证或图表ID')
                
            # 处理绘制数据
            drawings = []
            for drawing in data['payload'].get('sources', {}).values():
                # 合并状态数据
                drawing_with_state = {**drawing, **drawing.get('state', {})}
                drawings.append(drawing_with_state)
                
            return drawings