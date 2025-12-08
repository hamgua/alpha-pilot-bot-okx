"""
数据验证模块
提供数据验证和JSON处理功能
"""

import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_price_data(data: Dict[str, Any]) -> bool:
        """验证价格数据"""
        try:
            required_fields = ['price', 'timestamp']
            return all(field in data for field in required_fields)
        except Exception as e:
            logger.error(f"价格数据验证失败: {e}")
            return False
    
    @staticmethod
    def validate_signal_data(data: Dict[str, Any]) -> bool:
        """验证信号数据"""
        try:
            required_fields = ['signal', 'confidence', 'reason']
            return all(field in data for field in required_fields)
        except Exception as e:
            logger.error(f"信号数据验证失败: {e}")
            return False
    
    @staticmethod
    def validate_position_data(data: Dict[str, Any]) -> bool:
        """验证持仓数据"""
        try:
            required_fields = ['side', 'size', 'entry_price']
            return all(field in data for field in required_fields)
        except Exception as e:
            logger.error(f"持仓数据验证失败: {e}")
            return False
    
    @staticmethod
    def validate_market_data(data: Dict[str, Any]) -> bool:
        """验证市场数据"""
        try:
            if not isinstance(data, dict):
                return False
            
            # 检查基本结构
            if 'price' not in data or 'timestamp' not in data:
                return False
            
            # 验证价格
            price = data.get('price')
            if not isinstance(price, (int, float)) or price <= 0:
                return False
            
            # 验证时间戳
            timestamp = data.get('timestamp')
            if not isinstance(timestamp, (int, float, str)):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"市场数据验证失败: {e}")
            return False
    
    @staticmethod
    def validate_trading_config(config: Dict[str, Any]) -> bool:
        """验证交易配置"""
        try:
            required_top_level = ['exchange', 'trading', 'risk_management']
            return all(key in config for key in required_top_level)
        except Exception as e:
            logger.error(f"交易配置验证失败: {e}")
            return False
    
    @staticmethod
    def sanitize_data(data: Any) -> Any:
        """清理数据，移除潜在的危险字符"""
        try:
            if isinstance(data, dict):
                return {k: DataValidator.sanitize_data(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [DataValidator.sanitize_data(item) for item in data]
            elif isinstance(data, str):
                # 移除潜在的危险字符
                return data.replace('\x00', '').strip()
            else:
                return data
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            return data

class JSONHelper:
    """JSON工具类"""
    
    @staticmethod
    def safe_parse(json_str: str) -> Optional[Dict[str, Any]]:
        """安全解析JSON"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON解析失败: {e}")
            return None
    
    @staticmethod
    def safe_stringify(obj: Any) -> str:
        """安全序列化JSON"""
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON序列化失败: {e}")
            return str(obj)
    
    @staticmethod
    def safe_json_serialize(obj: Any, indent: int = 2) -> str:
        """安全序列化JSON（带格式化）"""
        try:
            return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
        except Exception as e:
            logger.error(f"JSON格式化序列化失败: {e}")
            return str(obj)
    
    @staticmethod
    def validate_json_structure(data: str, required_fields: List[str]) -> bool:
        """验证JSON结构"""
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                return False
            
            return all(field in parsed for field in required_fields)
        except Exception as e:
            logger.error(f"JSON结构验证失败: {e}")
            return False
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取JSON"""
        try:
            # 查找JSON对象
            start_idx = text.find('{')
            end_idx = text.rfind('}')

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = text[start_idx:end_idx + 1]
                return JSONHelper.safe_parse(json_str)

            return None

        except Exception as e:
            logger.error(f"提取JSON失败: {e}")
            return None

    @staticmethod
    def merge_json_objects(*json_objects: Dict[str, Any]) -> Dict[str, Any]:
        """合并多个JSON对象"""
        result = {}
        for obj in json_objects:
            if isinstance(obj, dict):
                result.update(obj)
        return result

    @staticmethod
    def get_json_diff(old_json: Dict[str, Any], new_json: Dict[str, Any]) -> Dict[str, Any]:
        """获取两个JSON对象的差异"""
        diff = {
            'added': {},
            'modified': {},
            'deleted': {}
        }

        # 检查新增和修改的字段
        for key, new_value in new_json.items():
            if key not in old_json:
                diff['added'][key] = new_value
            elif old_json[key] != new_value:
                diff['modified'][key] = {
                    'old': old_json[key],
                    'new': new_value
                }

        # 检查删除的字段
        for key, old_value in old_json.items():
            if key not in new_json:
                diff['deleted'][key] = old_value

        return diff

    @staticmethod
    def flatten_json(nested_json: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
        """扁平化嵌套的JSON对象"""
        def _flatten(obj, parent_key=''):
            items = []
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                if isinstance(value, dict):
                    items.extend(_flatten(value, new_key).items())
                else:
                    items.append((new_key, value))
            return dict(items)

        return _flatten(nested_json)

    @staticmethod
    def unflatten_json(flat_json: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
        """将扁平化的JSON恢复为嵌套结构"""
        result = {}
        for key, value in flat_json.items():
            keys = key.split(separator)
            current = result
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = value
        return result

    @staticmethod
    def filter_json_by_keys(json_obj: Dict[str, Any], keys_to_keep: List[str]) -> Dict[str, Any]:
        """根据键列表过滤JSON对象"""
        return {key: json_obj[key] for key in keys_to_keep if key in json_obj}

    @staticmethod
    def remove_json_keys(json_obj: Dict[str, Any], keys_to_remove: List[str]) -> Dict[str, Any]:
        """从JSON对象中删除指定的键"""
        return {key: value for key, value in json_obj.items() if key not in keys_to_remove}

    @staticmethod
    def convert_to_json_serializable(obj: Any) -> Any:
        """将对象转换为JSON可序列化的格式"""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, dict):
            return {str(k): JSONHelper.convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [JSONHelper.convert_to_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return JSONHelper.convert_to_json_serializable(obj.__dict__)
        else:
            return str(obj)

# 全局实例
data_validator = DataValidator()
json_helper = JSONHelper()

# 向后兼容的函数
def validate_price_data(data: Dict[str, Any]) -> bool:
    """验证价格数据（向后兼容）"""
    return DataValidator.validate_price_data(data)

def validate_signal_data(data: Dict[str, Any]) -> bool:
    """验证信号数据（向后兼容）"""
    return DataValidator.validate_signal_data(data)

def validate_position_data(data: Dict[str, Any]) -> bool:
    """验证持仓数据（向后兼容）"""
    return DataValidator.validate_position_data(data)

def safe_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
    """安全解析JSON（向后兼容）"""
    return JSONHelper.safe_parse(json_str)

def safe_stringify_json(obj: Any) -> str:
    """安全序列化JSON（向后兼容）"""
    return JSONHelper.safe_stringify(obj)

# 导出主要功能
__all__ = [
    'DataValidator',
    'JSONHelper',
    'data_validator',
    'json_helper',
    'validate_price_data',
    'validate_signal_data',
    'validate_position_data',
    'safe_parse_json',
    'safe_stringify_json'
]