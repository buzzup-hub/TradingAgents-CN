"""
协议处理模块
"""
import json
import base64
import zipfile
import io
import binascii

def parse_ws_packet(data):
    """
    解析WebSocket数据包
    
    Args:
        data: WebSocket原始数据
        
    Returns:
        list: 解析后的数据包列表
    """
    if not data:
        return []
    
    # 确保data是字符串
    if not isinstance(data, str):
        try:
            data = str(data)
        except Exception:
            return []
    
    # 移除~h~标记
    clean_data = data.replace('~h~', '')
    
    # 分割数据包
    packets = []
    parts = []
    
    # 查找所有匹配的包长度标记
    length_markers = []
    pos = 0
    
    while True:
        pos = clean_data.find('~m~', pos)
        if pos == -1:
            break
        length_markers.append(pos)
        pos += 3  # 跳过 ~m~
    
    # 如果没有长度标记，尝试直接解析整个数据
    if not length_markers:
        try:
            # 可能是一个有效的JSON字符串
            packet = json.loads(clean_data)
            return [packet]
        except json.JSONDecodeError:
            # 如果是数字，可能是ping包
            if clean_data.isdigit():
                return [int(clean_data)]
            # 不是有效的JSON或数字
            return []
    
    # 处理每个标记
    for i in range(len(length_markers)):
        start = length_markers[i]
        # 查找包长度
        length_end = clean_data.find('~m~', start + 3)
        if length_end == -1:
            continue
            
        try:
            # 获取长度值
            length = int(clean_data[start + 3:length_end])
            
            # 获取包内容
            content_start = length_end + 3
            content_end = content_start + length
            
            if content_end <= len(clean_data):
                content = clean_data[content_start:content_end]
                parts.append(content)
        except (ValueError, IndexError):
            continue
    
    # 解析每个部分
    for part in parts:
        if not part:
            continue
            
        # 处理ping包
        if part.isdigit():
            try:
                packets.append(int(part))
                continue
            except ValueError:
                # 如果无法转换为整数，跳过
                continue
            
        try:
            # 解析JSON
            packet = json.loads(part)
            packets.append(packet)
        except json.JSONDecodeError:
            # 无法解析为JSON，尝试作为普通字符串处理
            packets.append(part)
            
    return packets

def format_ws_packet(packet):
    """
    格式化WebSocket数据包
    
    Args:
        packet: 要发送的数据包
        
    Returns:
        str: 格式化后的数据，如果格式化失败则返回None
    """
    try:
        if isinstance(packet, dict):
            msg = json.dumps(packet)
        else:
            msg = str(packet)
            
        return f'~m~{len(msg)}~m~{msg}'
    except Exception:
        # 格式化失败，返回None
        return None

async def parse_compressed(data):
    """
    解析压缩数据
    
    Args:
        data: 压缩数据
        
    Returns:
        dict: 解析后的数据，如果解析失败则返回空字典
    """
    if not data:
        return {}
        
    try:
        # 解码base64
        decoded = base64.b64decode(data)
        
        # 创建内存文件对象
        zip_data = io.BytesIO(decoded)
        
        # 打开zip文件
        try:
            with zipfile.ZipFile(zip_data) as zf:
                # 获取文件列表
                file_list = zf.namelist()
                
                if not file_list:
                    # 没有文件
                    return {}
                    
                # 读取第一个文件
                try:
                    with zf.open(file_list[0]) as f:
                        content = f.read().decode('utf-8')
                        
                    # 解析JSON
                    return json.loads(content)
                except (UnicodeDecodeError, zipfile.BadZipFile):
                    # 解码或读取文件错误
                    return {}
        except zipfile.BadZipFile:
            # 不是有效的ZIP文件
            return {}
    except (ValueError, binascii.Error, TypeError):
        # base64解码错误
        return {}
    except json.JSONDecodeError:
        # JSON解析错误
        return {}
    except Exception:
        # 其他未知错误
        return {} 