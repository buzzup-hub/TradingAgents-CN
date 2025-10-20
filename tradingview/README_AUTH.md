# TradingView 账号配置管理系统

## 📋 功能概述

TradingView账号配置管理系统提供了完整的认证信息管理方案，支持：

- **环境变量优先级读取** - 优先从环境变量获取认证信息
- **多账号配置管理** - 支持配置多个TradingView账号
- **安全加密存储** - 支持配置文件加密保护敏感信息  
- **命令行管理工具** - 提供完整的CLI工具管理账号配置
- **自动集成** - 自动集成到现有TradingView客户端

## 🚀 快速入门

### 1. 环境变量方式 (推荐)

```bash
# 设置环境变量
export TV_SESSION="your_session_token_here"
export TV_SIGNATURE="your_signature_here"
export TV_SERVER="data"  # 可选，默认为data

# 直接使用，无需额外配置
python your_script.py
```

### 2. 配置文件方式

```bash
# 使用CLI工具添加账号
cd /Users/zerone/code/trading/chan.py/tradingview
python auth_cli.py add --from-env --set-default

# 或手动添加账号
python auth_cli.py add
```

### 3. 代码中使用

```python
# 自动从配置获取认证信息
from tradingview import Client
client = Client()  # 自动使用配置的认证信息
await client.connect()

# 指定特定账号
client = Client({'account_name': 'my_account'})
await client.connect()

# 增强客户端同样支持
from tradingview.enhanced_client import EnhancedTradingViewClient
client = EnhancedTradingViewClient()
await client.connect()
```

## 📁 文件结构

```
tradingview/
├── auth_config.py          # 认证配置管理核心模块
├── auth_cli.py             # 命令行管理工具
├── README_AUTH.md          # 本说明文档
└── client.py               # 已集成认证管理器

config/
└── tradingview_auth.yaml   # 默认配置文件模板
```

## 🔧 CLI工具使用

### 基础命令

```bash
# 查看所有账号配置
python auth_cli.py list

# 从环境变量添加账号并设为默认
python auth_cli.py add --from-env --set-default

# 手动添加账号
python auth_cli.py add

# 测试账号连接
python auth_cli.py test [账号名称]

# 设置默认账号
python auth_cli.py default my_account

# 删除账号
python auth_cli.py remove my_account --force
```

### 高级功能

```bash
# 启用配置文件加密
python auth_cli.py encrypt --password

# 禁用配置文件加密  
python auth_cli.py decrypt --force

# 导出配置
python auth_cli.py export --output my_accounts.json

# 导入配置
python auth_cli.py import my_accounts.json

# 更新账号信息
python auth_cli.py update my_account --server prodata --description "专业账号"
```

## ⚙️ 配置文件格式

### YAML格式 (推荐)

```yaml
# config/tradingview_auth.yaml
config_version: "1.0"
encryption_enabled: false
default_account: "main_account"

accounts:
  - name: "main_account"
    session_token: "your_session_token"
    signature: "your_signature"
    server: "data" 
    description: "主要交易账号"
    is_active: true
    created_at: "2024-01-01T00:00:00"
    last_used: null
```

### 加密存储

启用加密后，配置文件格式：

```yaml
encrypted: true
content: "gAAAAABh5x..."  # 加密后的配置内容
version: "1.0"
created_at: "2024-01-01T00:00:00"
```

## 🔐 认证信息获取

### 1. 登录TradingView

访问 [TradingView官网](https://tradingview.com) 并登录账号

### 2. 获取Session和Signature

1. 打开浏览器开发者工具 (F12)
2. 切换到 **Network** 标签页
3. 过滤显示 **WS** (WebSocket) 请求
4. 刷新页面或打开图表
5. 找到WebSocket连接请求
6. 在请求详情中查找：
   - `session`: 复制为 `TV_SESSION`
   - `signature`: 复制为 `TV_SIGNATURE`

### 3. 验证配置

```bash
# 测试配置是否正确
python auth_cli.py test
```

## 🎯 使用优先级

认证信息获取优先级（从高到低）：

1. **环境变量** - `TV_SESSION`, `TV_SIGNATURE`, `TV_SERVER`
2. **指定账号** - 通过 `account_name` 参数指定
3. **默认账号** - 配置文件中的 `default_account`
4. **第一个激活账号** - 配置文件中第一个 `is_active: true` 的账号

## 🛡️ 安全建议

### 生产环境

```bash
# 1. 启用配置文件加密
python auth_cli.py encrypt --password

# 2. 设置文件权限
chmod 600 config/tradingview_auth.yaml

# 3. 使用环境变量（更安全）
export TV_SESSION="..."
export TV_SIGNATURE="..."
```

### 开发环境

```bash
# 使用配置文件，方便管理多个账号
python auth_cli.py add --from-env --set-default
```

## 📊 配置示例

### 多账号配置示例

```yaml
accounts:
  # 主要账号
  - name: "main_trading"
    session_token: "main_session_token"
    signature: "main_signature"
    server: "data"
    description: "主要交易账号"
    is_active: true
  
  # 备用账号
  - name: "backup_account"
    session_token: "backup_session_token"
    signature: "backup_signature"  
    server: "data"
    description: "备用账号"
    is_active: true
    
  # 专业数据账号
  - name: "pro_data"
    session_token: "pro_session_token"
    signature: "pro_signature"
    server: "prodata"
    description: "专业版数据账号"
    is_active: false  # 需要时激活
```

### 代码中切换账号

```python
# 使用默认账号
client = Client()

# 使用指定账号
client = Client({'account_name': 'backup_account'})

# 使用专业数据账号
client = Client({'account_name': 'pro_data'})
```

## 🔍 故障排除

### 常见问题

1. **认证失败**
   ```bash
   python auth_cli.py test  # 测试连接
   ```

2. **配置文件权限问题**
   ```bash
   chmod 600 config/tradingview_auth.yaml
   ```

3. **加密配置无法读取**
   ```bash
   python auth_cli.py decrypt --force  # 禁用加密
   ```

4. **环境变量未生效**
   ```bash
   echo $TV_SESSION  # 检查环境变量
   source ~/.bashrc  # 重新加载环境变量
   ```

### 调试模式

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

from tradingview.auth_config import get_auth_manager
auth_manager = get_auth_manager()
account = auth_manager.get_account()
print(f"使用账号: {account.name if account else 'None'}")
```

## 🔄 迁移指南

### 从环境变量迁移到配置文件

```bash
# 1. 从当前环境变量创建配置
python auth_cli.py add --from-env --set-default

# 2. 验证配置
python auth_cli.py list

# 3. 测试连接
python auth_cli.py test
```

### 配置文件格式升级

配置管理器自动处理版本兼容性，无需手动升级。

## 📚 API参考

### 主要类和函数

```python
from tradingview.auth_config import (
    TradingViewAuthManager,     # 认证管理器
    TradingViewAccount,         # 账号配置类
    get_auth_manager,          # 获取全局管理器实例
    get_tradingview_auth       # 便捷认证信息获取函数
)

# 获取认证信息
auth_info = get_tradingview_auth('my_account')
# 返回: {'token': '...', 'signature': '...', 'server': 'data'}

# 使用管理器
auth_manager = get_auth_manager()
account = auth_manager.get_account('my_account')
```

---

**注意**: 请妥善保管您的TradingView认证信息，不要分享给他人或提交到公共代码仓库。