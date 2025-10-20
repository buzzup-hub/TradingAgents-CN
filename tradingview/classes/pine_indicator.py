"""
Pine指标类
"""
from typing import Dict, Any, Optional

class PineIndicator:
    """
    Pine指标类
    """
    def __init__(self, options: Dict[str, Any]):
        """
        初始化Pine指标
        
        Args:
            options: 指标选项
        """
        self._options = options
        self._type = 'Script@tv-scripting-101!'
        
    @property
    def pine_id(self) -> str:
        """获取指标ID"""
        return self._options.get('pineId', '')
        
    @property
    def pine_version(self) -> str:
        """获取指标版本"""
        return self._options.get('pineVersion', '')
        
    @property
    def description(self) -> str:
        """获取指标描述"""
        return self._options.get('description', '')
        
    @property
    def short_description(self) -> str:
        """获取指标简短描述"""
        return self._options.get('shortDescription', '')
        
    @property
    def inputs(self) -> Dict[str, Any]:
        """获取指标输入参数"""
        return self._options.get('inputs', {})
        
    @property
    def plots(self) -> Dict[str, str]:
        """获取指标绘图"""
        return self._options.get('plots', {})
        
    @property
    def type(self) -> str:
        """获取指标类型"""
        return self._type
        
    def set_type(self, type: str = 'Script@tv-scripting-101!') -> None:
        """
        设置指标类型
        
        Args:
            type: 指标类型
        """
        self._type = type
        
    @property
    def script(self) -> str:
        """获取指标脚本"""
        return self._options.get('script', '')
        
    def set_option(self, key: str, value: Any) -> None:
        """
        设置指标选项
        
        Args:
            key: 选项键
            value: 选项值
        """
        prop_id = ''
        
        # 查找输入参数
        if f'in_{key}' in self._options['inputs']:
            prop_id = f'in_{key}'
        elif key in self._options['inputs']:
            prop_id = key
        else:
            # 通过inline或internalID查找
            for input_id, input_data in self._options['inputs'].items():
                if input_data.get('inline') == key or input_data.get('internalID') == key:
                    prop_id = input_id
                    break
                    
        if prop_id and prop_id in self._options['inputs']:
            input_data = self._options['inputs'][prop_id]
            
            # 类型检查
            types = {
                'bool': bool,
                'integer': int,
                'float': float,
                'text': str
            }
            
            if input_data['type'] in types:
                if not isinstance(value, types[input_data['type']]):
                    raise TypeError(f"Input '{input_data['name']}' ({prop_id}) must be a {types[input_data['type']].__name__}!")
                    
            # 选项值检查
            if 'options' in input_data and value not in input_data['options']:
                raise ValueError(f"Input '{input_data['name']}' ({prop_id}) must be one of these values: {input_data['options']}")
                
            input_data['value'] = value
        else:
            raise KeyError(f"Input '{key}' not found ({prop_id}).") 