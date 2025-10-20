"""
TradingView客户端模块
"""
import json
import asyncio
import websockets
from typing import Dict, Any, Callable, List, Optional, Union

from .protocol import parse_ws_packet, format_ws_packet
from .chart import ChartSession
from .quote import QuoteSession

from config.logging_config import get_logger
logger = get_logger(__name__)

class Client:
    """
    TradingView客户端类
    """
    def __init__(self, options=None, **kwargs):
        """
        初始化客户端
        
        Args:
            options: 客户端选项
            **kwargs: 额外的命名参数，可以包含token和signature
        """
        # 合并options和命名参数
        if options is None:
            options = {}
        
        # 将命名参数合并到options中
        for key, value in kwargs.items():
            options[key] = value
        
        # 如果没有提供认证信息，尝试从认证管理器获取
        if not options.get('token') or not options.get('signature'):
            try:
                from .auth_config import get_tradingview_auth
                auth_info = get_tradingview_auth(options.get('account_name'))
                if auth_info:
                    options.update(auth_info)
            except ImportError:
                pass  # 认证管理器不可用，继续使用传入的参数
            
        self._ws = None
        self._logged = False
        self._sessions = {}
        self._send_queue = []
        self._debug = options.get('DEBUG', False)
        
        # 回调函数
        self._callbacks = {
            'connected': [],
            'disconnected': [],
            'logged': [],
            'ping': [],
            'data': [],
            'error': [],
            'event': []
        }
        
        # 服务器和认证信息
        self._server = options.get('server', 'data')
        self._token = options.get('token', '')
        self._signature = options.get('signature', '')
        self._location = options.get('location', 'https://tradingview.com')
        
        # 心跳任务
        self._heartbeat_task = None
        self._message_loop_task = None
        self._heartbeat_interval = options.get('heartbeat_interval', 10)  # 默认10秒发送一次心跳，更频繁以避免TradingView超时
        
        # 类属性
        self.Session = type('Session', (), {
            'Chart': lambda: ChartSession(self),
            'Quote': lambda options=None: QuoteSession(self, options)
        })
        
    @property
    def is_logged(self):
        """是否已登录"""
        return self._logged
    
    @property
    def is_open(self):
        """连接是否打开"""
        if not self._ws:
            return False
        
        # 检查websockets的版本并使用正确的属性
        try:
            import pkg_resources
            websockets_version = pkg_resources.get_distribution("websockets").version
            version_parts = [int(x) for x in websockets_version.split('.')[:2]]
            
            if version_parts[0] >= 10:
                # 10.0及以上版本，ClientConnection没有open属性
                # 使用closed属性检查连接状态
                return not self._ws.closed
            else:
                # 旧版本使用open属性
                return hasattr(self._ws, 'open') and self._ws.open
        except Exception:
            # 如果无法确定版本，尝试各种方法检查连接状态
            if hasattr(self._ws, 'open'):
                return self._ws.open
            elif hasattr(self._ws, 'closed'):
                return not self._ws.closed
            else:
                # 无法确定连接状态，假设已连接
                return True
    
    @property
    def sessions(self):
        """会话列表"""
        return self._sessions
    
    async def connect(self):
        """
        连接到TradingView服务器
        """
        url = f"wss://{self._server}.tradingview.com/socket.io/websocket?type=chart"
        
        try:
            # 检查websockets库的版本并使用适当的方式设置headers
            import websockets
            import pkg_resources
            
            # 获取websockets的版本
            websockets_version = pkg_resources.get_distribution("websockets").version
            version_parts = [int(x) for x in websockets_version.split('.')[:2]]
            
            # 创建请求头
            headers = {'Origin': 'https://www.tradingview.com'}

            logger.info(f"tradingview connect: {url}, {headers}")
            
            # 连接超时参数（单位：秒）
            connection_timeout = 30  # 30秒连接超时
            handshake_timeout = 20   # 20秒握手超时
            
            # 根据版本使用不同的方式传递headers
            if version_parts[0] >= 10:
                # 10.0及以上版本使用additional_headers
                try:
                    self._ws = await asyncio.wait_for(
                        websockets.connect(
                            url, 
                            extra_headers=headers, 
                            ping_interval=8,   # 每8秒发送一次ping，比应用层心跳更频繁
                            ping_timeout=5,    # ping超时5秒  
                            close_timeout=3,   # 关闭超时3秒
                            max_size=10 * 1024 * 1024,  # 10MB的最大消息大小
                            open_timeout=handshake_timeout  # 握手超时时间
                        ),
                        timeout=connection_timeout
                    )
                except TypeError:
                    # 如果不支持上述参数，尝试使用旧版本方式
                    try:
                        self._ws = await asyncio.wait_for(
                            websockets.connect(
                                url, 
                                additional_headers=headers,
                                ping_interval=8,
                                ping_timeout=5,
                                open_timeout=handshake_timeout
                            ),
                            timeout=connection_timeout
                        )
                    except TypeError:
                        # 兼容旧版本websockets库
                        self._ws = await asyncio.wait_for(
                            websockets.connect(url, additional_headers=headers),
                            timeout=connection_timeout
                        )
            elif version_parts[0] >= 6:
                # 6.0-9.x版本
                try:
                    self._ws = await asyncio.wait_for(
                        websockets.connect(
                            url, 
                            origin="https://www.tradingview.com",
                            ping_interval=8,
                            ping_timeout=5,
                            open_timeout=handshake_timeout
                        ),
                        timeout=connection_timeout
                    )
                except TypeError:
                    # 兼容旧版本
                    self._ws = await asyncio.wait_for(
                        websockets.connect(url, origin="https://www.tradingview.com"),
                        timeout=connection_timeout
                    )
            else:
                # 较旧版本，使用原始WebSocketClientProtocol
                from websockets.client import WebSocketClientProtocol
                
                class CustomWebSocketClientProtocol(WebSocketClientProtocol):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.origin = "https://www.tradingview.com"
                
                self._ws = await asyncio.wait_for(
                    websockets.connect(url, klass=CustomWebSocketClientProtocol),
                    timeout=connection_timeout
                )
            
            # 触发连接事件
            self._handle_event('connected')
            
            # 设置认证 - 严格遵循JavaScript版本逻辑
            if self._token:
                # 获取用户信息
                try:
                    from .misc_requests import get_user
                    user = await get_user(self._token, self._signature, self._location)
                    # 使用auth_token而不是authToken
                    self._send_queue.insert(0, format_ws_packet({
                        'm': 'set_auth_token',
                        'p': [user.auth_token]
                    }))
                    self._logged = True
                    await self._send_queue_data()
                except Exception as e:
                    self._handle_error(f"认证错误: {str(e)}")
            else:
                # 使用匿名Token，与JavaScript版本一致
                self._send_queue.insert(0, format_ws_packet({
                    'm': 'set_auth_token',
                    'p': ['unauthorized_user_token']
                }))
                self._logged = True
                await self._send_queue_data()
            
            # 停止旧的任务避免冲突
            await self._stop_background_tasks()
            
            # 启动消息接收循环
            self._message_loop_task = asyncio.create_task(self._message_loop())
            
            # 启动心跳任务
            self._start_heartbeat()
            
            # 连接成功，返回True
            return True
            
        except Exception as e:
            self._handle_error(f"连接错误: {str(e)}")
            return False
    
    async def _heartbeat(self):
        """心跳任务，定期发送ping保持连接活跃"""
        retry_count = 0
        max_retries = 5
        base_wait_time = 2  # 基础等待时间（秒）
        
        try:
            while True:  # 改为无限循环，让重连逻辑控制退出
                if not self.is_open:
                    # 如果连接已断开，标记重连失败并退出心跳任务
                    # 让Enhanced客户端的自动重连机制处理重连逻辑
                    self._handle_error("检测到连接已断开，心跳任务退出")
                    break
                
                try:
                    # 使用TradingView格式的ping消息 - 发送一个整数作为ping包
                    # 这样更符合TradingView的协议
                    import time
                    ping_id = int(time.time() * 1000)  # 使用当前时间戳作为ping ID
                    ping_message = format_ws_packet(f"~h~{ping_id}")
                    
                    if ping_message:
                        await self._ws.send(ping_message)
                        if self._debug:
                            logger.debug(f"发送心跳ping: {ping_id}")
                except Exception as e:
                    self._handle_error(f"发送心跳失败: {str(e)}")
                    # 标记连接为关闭，下一次循环将尝试重连
                    if self._ws:
                        try:
                            await self._ws.close()
                        except:
                            pass
                    self._ws = None
                    self._logged = False
                    continue  # 直接进入下一次循环尝试重连
                
                # 等待下一次心跳
                await asyncio.sleep(self._heartbeat_interval)
        except asyncio.CancelledError:
            # 心跳任务被取消
            pass
        except Exception as e:
            self._handle_error(f"心跳任务异常: {str(e)}")
        finally:
            self._handle_error("心跳任务结束")
    
    async def _stop_background_tasks(self):
        """停止所有后台任务"""
        # 停止心跳任务
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        # 停止消息循环任务
        if self._message_loop_task and not self._message_loop_task.done():
            self._message_loop_task.cancel()
            try:
                await self._message_loop_task
            except asyncio.CancelledError:
                pass
            self._message_loop_task = None
    
    def _start_heartbeat(self):
        """启动心跳任务"""
        # 确保之前的心跳任务已停止 - 这里不需要再cancel，因为_stop_background_tasks已经处理了
        
        # 创建新的心跳任务
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
    
    async def _message_loop(self):
        """消息接收循环"""
        retry_count = 0
        max_retries = 5
        base_wait_time = 1  # 基础等待时间
        
        try:
            # 不同版本的websockets库可能有不同的接口
            import websockets
            import pkg_resources
            
            # 获取websockets的版本
            websockets_version = pkg_resources.get_distribution("websockets").version
            version_parts = [int(x) for x in websockets_version.split('.')[:2]]
            
            # 获取所有可能的连接关闭异常类型
            connection_exceptions = []
            if hasattr(websockets, 'exceptions'):
                # 新版本
                if hasattr(websockets.exceptions, 'ConnectionClosed'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosed)
                if hasattr(websockets.exceptions, 'ConnectionClosedError'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosedError)
                if hasattr(websockets.exceptions, 'ConnectionClosedOK'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosedOK)
            elif hasattr(websockets, 'ConnectionClosed'):
                # 旧版本
                connection_exceptions.append(websockets.ConnectionClosed)
            
            while True:  # 改为无限循环，便于处理重连
                # 检查连接状态
                if not self._ws or not self.is_open:
                    # 连接已关闭，等待心跳任务进行重连
                    await asyncio.sleep(1)
                    continue
                
                try:
                    if version_parts[0] >= 6:
                        # 6.0+版本使用异步迭代器，需要使用try-except捕获迭代器结束
                        try:
                            async for message in self._ws:
                                await self._parse_packet(message)
                                retry_count = 0  # 收到消息，重置重试计数
                        except tuple(connection_exceptions) if connection_exceptions else Exception as e:
                            self._logged = False
                            self._handle_error(f"连接已关闭: {str(e)}")
                            self._handle_event('disconnected')
                            # 等待心跳任务重连
                            await asyncio.sleep(1)
                    else:
                        # 旧版本使用recv方法
                        try:
                            message = await self._ws.recv()
                            await self._parse_packet(message)
                            retry_count = 0  # 收到消息，重置重试计数
                        except tuple(connection_exceptions) if connection_exceptions else Exception as e:
                            self._logged = False
                            self._handle_error(f"连接已关闭: {str(e)}")
                            self._handle_event('disconnected')
                            # 等待心跳任务重连
                            await asyncio.sleep(1)
                except Exception as e:
                    retry_count += 1
                    wait_time = base_wait_time * (2 ** min(retry_count - 1, 5))  # 限制最大等待时间
                    
                    self._handle_error(f"消息循环异常({retry_count}/{max_retries}): {str(e)}, {wait_time}秒后重试")
                    
                    # 标记连接为关闭，以便心跳任务重连
                    self._logged = False
                    if self._ws:
                        try:
                            await self._ws.close()
                        except:
                            pass
                    self._ws = None
                    
                    if retry_count >= max_retries:
                        self._handle_error("达到最大重试次数，消息接收循环终止")
                        return
                    
                    # 等待一段时间再重试
                    await asyncio.sleep(wait_time)
                
        except Exception as e:
            self._handle_error(f"消息循环错误: {str(e)}")
            self._logged = False
            self._handle_event('disconnected')
            
            # 停止心跳任务（消息循环结束时）
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
                self._heartbeat_task = None
    
    async def _parse_packet(self, data):
        """
        解析WebSocket数据包
        
        Args:
            data: WebSocket原始数据
        """
        if not self.is_open:
            return
            
        try:
            packets = parse_ws_packet(data)
            if not packets:
                # 如果解析结果为空，则直接返回
                return
            
            if not isinstance(packets, list):
                # 确保packets是一个列表
                packets = [packets]
            
            for packet in packets:
                if self._debug:
                    logger.debug(f"接收: {packet}")
                    
                # 处理Ping包
                if isinstance(packet, int):
                    try:
                        await self._ws.send(format_ws_packet(f"~h~{packet}"))
                        self._handle_event('ping', packet)
                    except Exception as e:
                        self._handle_error(f"处理Ping包错误: {str(e)}")
                    continue
                    
                # 处理协议错误
                if isinstance(packet, dict) and packet.get('m') == 'protocol_error':
                    self._handle_error(f"协议错误: {packet.get('p')}")
                    try:
                        await self._ws.close()
                    except Exception as e:
                        self._handle_error(f"关闭连接错误: {str(e)}")
                    continue
                    
                # 处理会话数据
                if isinstance(packet, dict) and packet.get('m') and isinstance(packet.get('p'), list):
                    try:
                        parsed = {
                            'type': packet['m'],
                            'data': packet['p']
                        }
                        
                        session_id = packet['p'][0] if packet['p'] else None
                        
                        if session_id and session_id in self._sessions:
                            if 'on_data' in self._sessions[session_id]:
                                self._sessions[session_id]['on_data'](parsed)
                            continue
                    except Exception as e:
                        self._handle_error(f"处理会话数据错误: {str(e)}")
                        continue
                
                # 处理登录数据
                if not self._logged:
                    try:
                        self._handle_event('logged', packet)
                    except Exception as e:
                        self._handle_error(f"处理登录数据错误: {str(e)}")
                    continue
                    
                # 其他数据
                try:
                    self._handle_event('data', packet)
                except Exception as e:
                    self._handle_error(f"处理数据错误: {str(e)}")
        except Exception as e:
            self._handle_error(f"解析数据包错误: {str(e)}")
    
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
    
    async def send(self, packet_type, packet_data=None):
        """
        发送数据包
        
        Args:
            packet_type: 数据包类型
            packet_data: 数据包内容
        """
        try:
            if packet_data is None:
                packet_data = []
            
            # 确保packet_data是一个列表
            if not isinstance(packet_data, list):
                packet_data = [packet_data]
            
            # 处理复杂数据结构，将某些字典和列表转换为JSON字符串
            # 但保留数组格式用于特定命令
            processed_data = []
            
            # 根据命令类型决定是否保留数组格式
            # create_series和resolve_symbol需要保留数组参数的格式
            should_preserve_arrays = packet_type in ['create_series', 'modify_series']
            
            for item in packet_data:
                try:
                    if isinstance(item, dict) and not isinstance(item, str):
                        # 字典总是转为JSON字符串
                        processed_data.append(json.dumps(item))
                    elif isinstance(item, list) and not isinstance(item, str) and not should_preserve_arrays:
                        # 数组在非保留情况下转为JSON字符串
                        processed_data.append(json.dumps(item))
                    else:
                        # 其他情况保持原样
                        processed_data.append(item)
                except Exception as e:
                    self._handle_error(f"处理数据项错误: {str(e)}")
                    # 使用原始数据
                    processed_data.append(str(item))
            
            formatted_packet = format_ws_packet({
                'm': packet_type,
                'p': processed_data
            })
            
            if formatted_packet:
                self._send_queue.append(formatted_packet)
                await self._send_queue_data()
            else:
                self._handle_error("无法格式化数据包")
        except Exception as e:
            self._handle_error(f"发送数据包错误: {str(e)}")
    
    async def _send_queue_data(self):
        """发送队列中的数据"""
        if not self.is_open:
            # 如果连接未打开，则不发送数据
            return
        
        if not self._logged and self._send_queue and 'set_auth_token' not in self._send_queue[0]:
            # 如果未登录，且队列中的第一个数据包不是认证包，则不发送数据
            return
        
        try:
            # 获取websockets的所有可能的异常类型
            import websockets
            connection_exceptions = []
            
            # 添加所有可能的连接关闭异常
            if hasattr(websockets, 'exceptions'):
                # 新版本
                if hasattr(websockets.exceptions, 'ConnectionClosed'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosed)
                if hasattr(websockets.exceptions, 'ConnectionClosedError'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosedError)
                if hasattr(websockets.exceptions, 'ConnectionClosedOK'):
                    connection_exceptions.append(websockets.exceptions.ConnectionClosedOK)
            elif hasattr(websockets, 'ConnectionClosed'):
                # 旧版本
                connection_exceptions.append(websockets.ConnectionClosed)
            
            retry_count = 0
            max_retries = 3
            base_wait_time = 0.5
            
            while self._send_queue:
                if not self.is_open:
                    # 如果连接已断开，停止发送
                    break
                    
                packet = self._send_queue[0]  # 只获取但不移除
                if self._debug:
                    logger.debug(f"发送: {packet}")
                    
                try:
                    await self._ws.send(packet)
                    # 只有成功发送后才移除
                    self._send_queue.pop(0)
                    retry_count = 0  # 成功发送后重置重试计数
                except tuple(connection_exceptions) if connection_exceptions else Exception as e:
                    # 连接已关闭，触发断开连接事件
                    self._handle_error(f"连接已关闭，无法发送数据: {str(e)}")
                    self._logged = False
                    self._handle_event('disconnected')
                    break
                except Exception as e:
                    retry_count += 1
                    wait_time = base_wait_time * (2 ** min(retry_count - 1, 3))  # 限制最大等待时间
                    
                    if retry_count > max_retries:
                        self._handle_error(f"发送数据失败，达到最大重试次数，丢弃数据包: {str(e)}")
                        self._send_queue.pop(0)  # 丢弃无法发送的数据包
                        retry_count = 0
                        continue
                    
                    self._handle_error(f"发送数据错误({retry_count}/{max_retries}): {str(e)}, {wait_time}秒后重试")
                    
                    # 等待一段时间再重试
                    await asyncio.sleep(wait_time)
                    
                    # 检查连接状态并尝试重新连接
                    if not self.is_open:
                        try:
                            await self.connect()
                        except Exception as conn_err:
                            self._handle_error(f"重新连接错误: {str(conn_err)}")
                            # 继续下一次循环，让心跳任务处理重连
                        
        except Exception as e:
            self._handle_error(f"处理发送队列错误: {str(e)}")
    
    def on_connected(self, callback):
        """
        添加连接回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['connected'].append(callback)
    
    def on_disconnected(self, callback):
        """
        添加断开连接回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['disconnected'].append(callback)
    
    def on_logged(self, callback):
        """
        添加登录回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['logged'].append(callback)
    
    def on_ping(self, callback):
        """
        添加ping回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['ping'].append(callback)
    
    def on_data(self, callback):
        """
        添加数据回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['data'].append(callback)
    
    def on_error(self, callback):
        """
        添加错误回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['error'].append(callback)
    
    def on_event(self, callback):
        """
        添加事件回调
        
        Args:
            callback: 回调函数
        """
        self._callbacks['event'].append(callback)
    
    async def end(self):
        """
        关闭连接
        """
        # 停止所有后台任务
        await self._stop_background_tasks()
            
        # 关闭WebSocket连接
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        # 重置连接状态
        self._logged = False
            
    def get_connection_status(self):
        """
        获取连接的详细状态信息
        
        Returns:
            dict: 包含连接状态的详细信息
        """
        has_heartbeat = False
        if self._heartbeat_task:
            has_heartbeat = not self._heartbeat_task.done()
            
        websocket_status = "unknown"
        if self._ws is None:
            websocket_status = "none"
        elif not self.is_open:
            websocket_status = "closed"
        else:
            websocket_status = "open"
            
        return {
            "is_open": self.is_open,
            "is_logged": self._logged,
            "websocket_status": websocket_status,
            "server": self._server,
            "has_active_heartbeat": has_heartbeat,
            "heartbeat_interval": self._heartbeat_interval,
            "active_sessions_count": len(self._sessions),
            "queued_messages": len(self._send_queue)
        }

# 为了兼容性，创建TradingViewClient别名
TradingViewClient = Client 