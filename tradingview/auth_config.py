#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView账号配置管理器
支持环境变量优先级和配置文件存储
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TradingViewAccount:
    """TradingView账号配置"""
    name: str                           # 账号名称/标识
    session_token: str                  # TV_SESSION
    signature: str                      # TV_SIGNATURE
    server: str = "data"               # 服务器选择
    description: str = ""              # 账号描述
    is_active: bool = True             # 是否激活
    created_at: Optional[str] = None   # 创建时间
    last_used: Optional[str] = None    # 最后使用时间
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingViewAccount':
        """从字典创建实例"""
        return cls(**data)
    
    def update_last_used(self):
        """更新最后使用时间"""
        self.last_used = datetime.now().isoformat()


@dataclass
class AuthConfig:
    """认证配置"""
    accounts: List[TradingViewAccount]
    default_account: Optional[str] = None   # 默认账号名称
    encryption_enabled: bool = False        # 是否启用加密
    config_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'accounts': [acc.to_dict() for acc in self.accounts],
            'default_account': self.default_account,
            'encryption_enabled': self.encryption_enabled,
            'config_version': self.config_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthConfig':
        """从字典创建实例"""
        accounts = [TradingViewAccount.from_dict(acc_data) for acc_data in data.get('accounts', [])]
        return cls(
            accounts=accounts,
            default_account=data.get('default_account'),
            encryption_enabled=data.get('encryption_enabled', False),
            config_version=data.get('config_version', '1.0')
        )


class ConfigEncryption:
    """配置文件加密管理"""
    
    def __init__(self, password: Optional[str] = None):
        self.password = password or self._get_default_password()
        self.key = self._derive_key(self.password)
        self.cipher_suite = Fernet(self.key)
    
    def _get_default_password(self) -> str:
        """获取默认密码"""
        # 从环境变量或使用机器唯一标识生成默认密码
        env_password = os.getenv('TV_CONFIG_PASSWORD')
        if env_password:
            return env_password
        
        # 使用机器信息生成唯一密码
        import platform
        machine_info = f"{platform.node()}-{platform.machine()}-{platform.system()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:32]
    
    def _derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        password_bytes = password.encode()
        salt = b'tradingview_auth_salt_2024'  # 固定盐值，生产环境应该随机生成
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_data_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise


class TradingViewAuthManager:
    """TradingView认证管理器"""
    
    def __init__(self, config_file: Optional[str] = None, encryption_password: Optional[str] = None):
        """
        初始化认证管理器
        
        Args:
            config_file: 配置文件路径
            encryption_password: 加密密码
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config_dir = Path(self.config_file).parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加密管理器
        self.encryption = ConfigEncryption(encryption_password)
        
        # 认证配置
        self.auth_config: Optional[AuthConfig] = None
        
        # 环境变量配置缓存
        self._env_config_cache: Optional[TradingViewAccount] = None
        
        # 加载配置
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 优先使用环境变量指定的配置文件路径
        env_config_path = os.getenv('TV_AUTH_CONFIG_PATH')
        if env_config_path:
            return env_config_path
        
        # 使用项目默认路径
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "tradingview_auth.yaml"
        return str(config_path)
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path(self.config_file)
            
            if not config_path.exists():
                logger.info(f"配置文件不存在，创建默认配置: {self.config_file}")
                self.auth_config = AuthConfig(accounts=[])
                self._save_config()
                return
            
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f) or {}
            
            # 检查是否加密
            if data.get('encrypted', False):
                encrypted_content = data.get('content', '')
                if encrypted_content:
                    decrypted_content = self.encryption.decrypt(encrypted_content)
                    data = json.loads(decrypted_content)
                else:
                    logger.warning("配置文件标记为加密但内容为空")
                    data = {}
            
            # 解析配置
            self.auth_config = AuthConfig.from_dict(data)
            logger.info(f"已加载配置文件: {self.config_file}, 账号数量: {len(self.auth_config.accounts)}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.auth_config = AuthConfig(accounts=[])
    
    def _save_config(self):
        """保存配置文件"""
        try:
            config_path = Path(self.config_file)
            config_data = self.auth_config.to_dict()
            
            # 是否启用加密
            if self.auth_config.encryption_enabled:
                # 加密配置内容
                content_json = json.dumps(config_data, ensure_ascii=False, indent=2)
                encrypted_content = self.encryption.encrypt(content_json)
                
                final_data = {
                    'encrypted': True,
                    'content': encrypted_content,
                    'version': self.auth_config.config_version,
                    'created_at': datetime.now().isoformat()
                }
            else:
                final_data = config_data
            
            # 保存文件
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    json.dump(final_data, f, ensure_ascii=False, indent=2)
                else:
                    yaml.dump(final_data, f, default_flow_style=False, allow_unicode=True)
            
            # 设置文件权限（仅所有者可读写）
            config_path.chmod(0o600)
            logger.info(f"配置文件已保存: {self.config_file}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def _get_env_config(self) -> Optional[TradingViewAccount]:
        """从环境变量获取配置"""
        if self._env_config_cache:
            return self._env_config_cache
        
        session_token = os.getenv('TV_SESSION')
        signature = os.getenv('TV_SIGNATURE')
        
        if session_token and signature:
            server = os.getenv('TV_SERVER', 'data')
            
            self._env_config_cache = TradingViewAccount(
                name="environment",
                session_token=session_token,
                signature=signature,
                server=server,
                description="从环境变量读取的配置",
                is_active=True
            )
            
            logger.info("已从环境变量读取TradingView认证配置")
            return self._env_config_cache
        
        return None
    
    def get_account(self, account_name: Optional[str] = None) -> Optional[TradingViewAccount]:
        """
        获取账号配置
        
        Args:
            account_name: 账号名称，为None时使用默认账号
        
        Returns:
            TradingViewAccount: 账号配置，优先级：环境变量 > 指定账号 > 默认账号
        """
        # 1. 优先从环境变量读取
        env_config = self._get_env_config()
        if env_config:
            env_config.update_last_used()
            return env_config
        
        # 2. 从配置文件读取
        if not self.auth_config or not self.auth_config.accounts:
            logger.warning("没有可用的TradingView账号配置")
            return None
        
        # 3. 查找指定账号
        if account_name:
            for account in self.auth_config.accounts:
                if account.name == account_name and account.is_active:
                    account.update_last_used()
                    return account
            
            logger.warning(f"未找到指定账号: {account_name}")
            return None
        
        # 4. 使用默认账号
        if self.auth_config.default_account:
            for account in self.auth_config.accounts:
                if account.name == self.auth_config.default_account and account.is_active:
                    account.update_last_used()
                    return account
        
        # 5. 使用第一个激活的账号
        for account in self.auth_config.accounts:
            if account.is_active:
                account.update_last_used()
                return account
        
        logger.warning("没有找到可用的激活账号")
        return None
    
    def add_account(self, account: TradingViewAccount, set_as_default: bool = False) -> bool:
        """
        添加账号配置
        
        Args:
            account: 账号配置
            set_as_default: 是否设为默认账号
        
        Returns:
            bool: 是否添加成功
        """
        try:
            # 检查账号名称是否已存在
            for existing_account in self.auth_config.accounts:
                if existing_account.name == account.name:
                    logger.warning(f"账号名称已存在: {account.name}")
                    return False
            
            # 添加账号
            self.auth_config.accounts.append(account)
            
            # 设为默认账号
            if set_as_default or not self.auth_config.default_account:
                self.auth_config.default_account = account.name
            
            # 保存配置
            self._save_config()
            
            logger.info(f"已添加TradingView账号: {account.name}")
            return True
            
        except Exception as e:
            logger.error(f"添加账号失败: {e}")
            return False
    
    def update_account(self, account_name: str, **updates) -> bool:
        """
        更新账号配置
        
        Args:
            account_name: 账号名称
            **updates: 更新的字段
        
        Returns:
            bool: 是否更新成功
        """
        try:
            for account in self.auth_config.accounts:
                if account.name == account_name:
                    # 更新字段
                    for key, value in updates.items():
                        if hasattr(account, key):
                            setattr(account, key, value)
                        else:
                            logger.warning(f"未知的账号字段: {key}")
                    
                    # 保存配置
                    self._save_config()
                    logger.info(f"已更新账号配置: {account_name}")
                    return True
            
            logger.warning(f"未找到指定账号: {account_name}")
            return False
            
        except Exception as e:
            logger.error(f"更新账号失败: {e}")
            return False
    
    def remove_account(self, account_name: str) -> bool:
        """
        删除账号配置
        
        Args:
            account_name: 账号名称
        
        Returns:
            bool: 是否删除成功
        """
        try:
            for i, account in enumerate(self.auth_config.accounts):
                if account.name == account_name:
                    # 删除账号
                    del self.auth_config.accounts[i]
                    
                    # 如果删除的是默认账号，重新设置默认账号
                    if self.auth_config.default_account == account_name:
                        if self.auth_config.accounts:
                            self.auth_config.default_account = self.auth_config.accounts[0].name
                        else:
                            self.auth_config.default_account = None
                    
                    # 保存配置
                    self._save_config()
                    logger.info(f"已删除账号: {account_name}")
                    return True
            
            logger.warning(f"未找到指定账号: {account_name}")
            return False
            
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            return False
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        列出所有账号配置
        
        Returns:
            List[Dict]: 账号信息列表
        """
        accounts_info = []
        
        # 环境变量配置
        env_config = self._get_env_config()
        if env_config:
            accounts_info.append({
                'name': env_config.name,
                'server': env_config.server,
                'description': env_config.description,
                'is_active': env_config.is_active,
                'source': 'environment',
                'is_default': True  # 环境变量优先级最高
            })
        
        # 配置文件账号
        if self.auth_config:
            for account in self.auth_config.accounts:
                accounts_info.append({
                    'name': account.name,
                    'server': account.server,
                    'description': account.description,
                    'is_active': account.is_active,
                    'source': 'config_file',
                    'is_default': account.name == self.auth_config.default_account,
                    'created_at': account.created_at,
                    'last_used': account.last_used
                })
        
        return accounts_info
    
    def set_default_account(self, account_name: str) -> bool:
        """
        设置默认账号
        
        Args:
            account_name: 账号名称
        
        Returns:
            bool: 是否设置成功
        """
        try:
            # 检查账号是否存在
            for account in self.auth_config.accounts:
                if account.name == account_name:
                    self.auth_config.default_account = account_name
                    self._save_config()
                    logger.info(f"已设置默认账号: {account_name}")
                    return True
            
            logger.warning(f"未找到指定账号: {account_name}")
            return False
            
        except Exception as e:
            logger.error(f"设置默认账号失败: {e}")
            return False
    
    def enable_encryption(self, password: Optional[str] = None) -> bool:
        """
        启用配置文件加密
        
        Args:
            password: 加密密码，为None时使用默认密码
        
        Returns:
            bool: 是否启用成功
        """
        try:
            if password:
                self.encryption = ConfigEncryption(password)
            
            self.auth_config.encryption_enabled = True
            self._save_config()
            
            logger.info("已启用配置文件加密")
            return True
            
        except Exception as e:
            logger.error(f"启用加密失败: {e}")
            return False
    
    def disable_encryption(self) -> bool:
        """
        禁用配置文件加密
        
        Returns:
            bool: 是否禁用成功
        """
        try:
            self.auth_config.encryption_enabled = False
            self._save_config()
            
            logger.info("已禁用配置文件加密")
            return True
            
        except Exception as e:
            logger.error(f"禁用加密失败: {e}")
            return False
    
    def validate_account(self, account: TradingViewAccount) -> bool:
        """
        验证账号配置有效性
        
        Args:
            account: 账号配置
        
        Returns:
            bool: 是否有效
        """
        try:
            # 基础字段验证
            if not account.session_token or not account.signature:
                logger.error("缺少必需的认证信息")
                return False
            
            # Token格式验证（简单检查）
            if len(account.session_token) < 10 or len(account.signature) < 10:
                logger.error("认证信息格式无效")
                return False
            
            # 服务器选择验证
            valid_servers = ['data', 'prodata', 'tradingview']
            if account.server not in valid_servers:
                logger.warning(f"不常见的服务器选择: {account.server}")
            
            return True
            
        except Exception as e:
            logger.error(f"账号验证失败: {e}")
            return False


# 全局认证管理器实例
_auth_manager: Optional[TradingViewAuthManager] = None


def get_auth_manager(config_file: Optional[str] = None, 
                    encryption_password: Optional[str] = None) -> TradingViewAuthManager:
    """
    获取全局认证管理器实例
    
    Args:
        config_file: 配置文件路径
        encryption_password: 加密密码
    
    Returns:
        TradingViewAuthManager: 认证管理器实例
    """
    global _auth_manager
    
    if _auth_manager is None:
        _auth_manager = TradingViewAuthManager(config_file, encryption_password)
    
    return _auth_manager


def get_tradingview_auth(account_name: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    获取TradingView认证信息的便捷函数
    
    Args:
        account_name: 账号名称
    
    Returns:
        Dict[str, str]: 认证信息字典，包含token、signature、server
    """
    auth_manager = get_auth_manager()
    account = auth_manager.get_account(account_name)
    
    if account:
        return {
            'token': account.session_token,
            'signature': account.signature,
            'server': account.server
        }
    
    return None


# 便捷函数
def create_account_from_env() -> Optional[TradingViewAccount]:
    """从环境变量创建账号配置"""
    session_token = os.getenv('TV_SESSION')
    signature = os.getenv('TV_SIGNATURE')
    
    if session_token and signature:
        return TradingViewAccount(
            name=input("请输入账号名称: ").strip() or "default",
            session_token=session_token,
            signature=signature,
            server=os.getenv('TV_SERVER', 'data'),
            description=input("请输入账号描述(可选): ").strip() or "从环境变量创建"
        )
    
    return None