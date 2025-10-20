# TradingView数据同步和备份系统使用指南

## 📋 目录

1. [系统概述](#-系统概述)
2. [快速开始](#-快速开始)
3. [数据同步](#-数据同步)
4. [数据备份](#-数据备份)
5. [配置管理](#-配置管理)
6. [CLI工具使用](#-cli工具使用)
7. [监控和运维](#-监控和运维)
8. [最佳实践](#-最佳实践)
9. [故障排除](#-故障排除)

---

## 🎯 系统概述

TradingView数据同步和备份系统提供了完整的数据生命周期管理解决方案，包括：

### 核心功能

- **📊 多源数据同步**: 支持主数据源、缓存、备份之间的灵活同步
- **💾 多类型备份**: 全量备份、增量备份、快照备份、差异备份
- **⏰ 定时任务调度**: 基于Cron表达式的灵活任务调度
- **🔍 实时监控**: 完整的性能指标和健康检查
- **🛠️ CLI管理工具**: 命令行界面方便运维管理
- **⚡ 高性能设计**: 异步处理、并发控制、智能缓存

### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                   数据同步备份系统架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 数据源层                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ TradingView │  │  缓存系统   │  │   备份存储   │            │
│  │  (Primary)  │  │  (Cache)    │  │  (Backup)    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│  🔄 同步引擎层             │                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           DataSyncEngine (异步任务调度)                     │ │
│  │                                                             │ │
│  │ • 任务队列管理  • 并发控制  • 重试机制  • 性能监控         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                           │                                    │
│  💾 备份管理层             │                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          DataBackupManager (备份生命周期管理)               │ │
│  │                                                             │ │
│  │ • 多类型备份  • 版本管理  • 校验恢复  • 清理策略           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境准备

```bash
# 1. 安装依赖
pip install asyncio pyyaml schedule prometheus_client

# 2. 创建必要目录
mkdir -p data/backups
mkdir -p logs

# 3. 检查配置文件
ls tradingview/sync_backup_config.yaml
```

### 30秒快速体验

```bash
# 1. 运行系统测试
python tradingview/sync_backup_cli.py test

# 2. 查看系统状态
python tradingview/sync_backup_cli.py status

# 3. 创建快照备份
python tradingview/sync_backup_cli.py backup --type snapshot

# 4. 列出所有备份
python tradingview/sync_backup_cli.py list backups
```

### Python API 快速使用

```python
import asyncio
from tradingview.data_sync_backup import DataSyncBackupController, BackupType

async def quick_demo():
    # 初始化控制器
    controller = DataSyncBackupController()
    
    try:
        # 启动系统
        await controller.start()
        
        # 创建备份
        backup_id = await controller.create_manual_backup(
            BackupType.FULL,
            symbols=['BINANCE:BTCUSDT'],
            timeframes=['15']
        )
        
        print(f"备份创建成功: {backup_id}")
        
        # 执行同步
        task_id = await controller.sync_data(
            source_type="primary",
            target_type="cache",
            symbols=['BINANCE:BTCUSDT'],
            timeframes=['15']
        )
        
        print(f"同步任务启动: {task_id}")
        
        # 等待任务完成
        await asyncio.sleep(5)
        
        # 查看状态
        status = controller.get_system_status()
        print(f"系统状态: {status}")
        
    finally:
        await controller.stop()

# 运行演示
asyncio.run(quick_demo())
```

---

## 🔄 数据同步

### 同步类型和方向

| 源类型 | 目标类型 | 描述 | 使用场景 |
|--------|----------|------|----------|
| primary | cache | 主数据源到缓存 | 实时数据更新 |
| cache | backup | 缓存到备份 | 定期数据备份 |
| backup | cache | 备份到缓存 | 灾难恢复 |
| cache | remote | 缓存到远程 | 数据分发 |

### 同步策略配置

```yaml
# sync_backup_config.yaml
sync_config:
  sync_interval: 300                    # 同步间隔(秒)
  batch_size: 100                       # 批处理大小
  max_concurrent_tasks: 5               # 最大并发任务
  
  # 优先级品种和时间框架
  priority_symbols:
    - "BINANCE:BTCUSDT"
    - "BINANCE:ETHUSDT"
  
  priority_timeframes:
    - "1"      # 1分钟
    - "15"     # 15分钟
```

### 编程式同步

```python
from tradingview.data_sync_backup import DataSyncEngine, SyncTask

async def custom_sync_example():
    # 创建同步引擎
    sync_engine = DataSyncEngine({
        'sync_interval': 60,
        'max_concurrent_tasks': 10
    })
    
    await sync_engine.start_sync_engine()
    
    # 创建自定义同步任务
    task = SyncTask(
        task_id="",
        source_type="primary",
        target_type="cache",
        symbols=['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'],
        timeframes=['5', '15', '60'],
        priority=1
    )
    
    # 添加任务
    task_id = await sync_engine.add_sync_task(task)
    print(f"同步任务已添加: {task_id}")
    
    # 监控任务状态
    while True:
        status = sync_engine.get_sync_status()
        print(f"活跃任务: {status['active_tasks']}")
        
        if status['active_tasks'] == 0:
            break
            
        await asyncio.sleep(1)
    
    await sync_engine.stop_sync_engine()
```

### CLI同步操作

```bash
# 基础同步
python tradingview/sync_backup_cli.py sync \
  --source primary \
  --target cache \
  --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT \
  --timeframes 15,60

# 带等待的同步
python tradingview/sync_backup_cli.py sync \
  --source cache \
  --target backup \
  --symbols BINANCE:BTCUSDT \
  --wait

# 查看同步任务状态
python tradingview/sync_backup_cli.py list tasks
```

---

## 💾 数据备份

### 备份类型详解

#### 1. 全量备份 (Full Backup)
```bash
# 完整的数据备份，包含所有历史数据
python tradingview/sync_backup_cli.py backup --type full

# 指定品种的全量备份
python tradingview/sync_backup_cli.py backup \
  --type full \
  --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT \
  --timeframes 15,60
```

**特点**:
- 包含完整的历史数据
- 备份时间较长，文件较大
- 可独立恢复，不依赖其他备份
- 建议每日或每周执行

#### 2. 增量备份 (Incremental Backup)
```bash
# 只备份自上次备份以来的新数据
python tradingview/sync_backup_cli.py backup --type incremental
```

**特点**:
- 只备份变化的数据
- 备份速度快，文件小
- 恢复时需要完整备份链
- 建议每小时或更频繁执行

#### 3. 快照备份 (Snapshot Backup)
```bash
# 备份当前时刻的数据状态
python tradingview/sync_backup_cli.py backup --type snapshot
```

**特点**:
- 捕获特定时间点的数据状态
- 备份快速，适合频繁执行
- 主要用于测试和验证
- 建议在重要操作前执行

### 备份管理

```python
from tradingview.data_sync_backup import DataBackupManager, BackupType

async def backup_management_example():
    # 创建备份管理器
    backup_manager = DataBackupManager({
        'backup_dir': 'data/backups',
        'max_backup_files': 50,
        'compression_enabled': True
    })
    
    # 创建全量备份
    backup_id = await backup_manager.create_backup(
        BackupType.FULL,
        symbols=['BINANCE:BTCUSDT'],
        timeframes=['15', '60']
    )
    
    print(f"备份创建成功: {backup_id}")
    
    # 获取备份信息
    backup_info = backup_manager.get_backup_info(backup_id)
    print(f"备份大小: {backup_info['size_bytes']/1024/1024:.2f} MB")
    
    # 恢复备份
    success = await backup_manager.restore_backup(backup_id)
    print(f"备份恢复: {'成功' if success else '失败'}")
    
    # 列出所有备份
    all_backups = backup_manager.get_backup_info()
    for record in all_backups['backup_records']:
        print(f"备份: {record['backup_id']} - {record['backup_type']}")
```

### 备份策略配置

```yaml
# 备份保留策略
backup_config:
  retention_policy:
    daily_backups: 7                    # 保留7天日备份
    weekly_backups: 4                   # 保留4周周备份
    monthly_backups: 12                 # 保留12个月月备份
    yearly_backups: 3                   # 保留3年年备份
  
  # 备份验证
  verification:
    enable_checksum: true               # 启用校验和
    verify_after_backup: true          # 备份后立即验证
    
  # 存储后端
  storage_backends:
    local:
      enabled: true
      path: "data/backups/local"
    
    remote:
      enabled: false
      type: "s3"
      bucket: "tradingview-backups"
```

---

## ⚙️ 配置管理

### 主配置文件结构

```yaml
# sync_backup_config.yaml

# 数据同步配置
sync_config:
  sync_interval: 300
  batch_size: 100
  max_concurrent_tasks: 5

# 数据备份配置  
backup_config:
  backup_dir: "data/backups"
  max_backup_files: 30
  compression_enabled: true

# 定时任务配置
schedule_config:
  enabled: true
  backup_schedules:
    full_backup:
      cron: "0 2 * * *"                # 每天凌晨2点
    incremental_backup:
      cron: "*/30 * * * *"             # 每30分钟

# 监控配置
monitoring_config:
  enabled: true
  metrics_port: 9090
  alerts:
    enabled: true
```

### 动态配置更新

```python
import yaml
from tradingview.data_sync_backup import DataSyncBackupController

async def update_config_example():
    # 加载当前配置
    with open('tradingview/sync_backup_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 修改配置
    config['sync_config']['sync_interval'] = 180  # 改为3分钟
    config['backup_config']['max_backup_files'] = 50  # 增加备份文件数
    
    # 保存配置
    with open('tradingview/sync_backup_config.yaml', 'w') as f:
        yaml.dump(config, f, indent=2)
    
    # 重新初始化控制器
    controller = DataSyncBackupController(config)
    await controller.start()
    
    print("配置已更新并应用")
```

### 环境特定配置

```bash
# 开发环境
export SYNC_BACKUP_ENV=development
export SYNC_BACKUP_CONFIG=config/dev_sync_backup.yaml

# 生产环境
export SYNC_BACKUP_ENV=production  
export SYNC_BACKUP_CONFIG=config/prod_sync_backup.yaml

# 使用环境变量覆盖配置
export SYNC_INTERVAL=120
export BACKUP_DIR=/data/backups
export MAX_CONCURRENT_TASKS=8
```

---

## 🛠️ CLI工具使用

### 基础命令

```bash
# 查看帮助
python tradingview/sync_backup_cli.py --help

# 查看系统状态
python tradingview/sync_backup_cli.py status

# 详细状态输出
python tradingview/sync_backup_cli.py status --verbose
```

### 备份管理命令

```bash
# 创建全量备份
python tradingview/sync_backup_cli.py backup --type full

# 创建指定品种的增量备份
python tradingview/sync_backup_cli.py backup \
  --type incremental \
  --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT \
  --timeframes 15,60

# 列出所有备份
python tradingview/sync_backup_cli.py list backups

# 详细备份信息
python tradingview/sync_backup_cli.py list backups --verbose

# 恢复备份
python tradingview/sync_backup_cli.py restore backup_full_1699123456

# 强制恢复备份(不提示确认)
python tradingview/sync_backup_cli.py restore backup_full_1699123456 --force

# 恢复到指定数据库文件
python tradingview/sync_backup_cli.py restore backup_full_1699123456 \
  --target-db /path/to/target.db
```

### 同步管理命令

```bash
# 执行主数据源到缓存同步
python tradingview/sync_backup_cli.py sync \
  --source primary \
  --target cache \
  --symbols BINANCE:BTCUSDT

# 执行缓存到备份同步并等待完成
python tradingview/sync_backup_cli.py sync \
  --source cache \
  --target backup \
  --wait

# 查看同步任务状态
python tradingview/sync_backup_cli.py list tasks

# 详细任务信息
python tradingview/sync_backup_cli.py list tasks --verbose
```

### 守护进程模式

```bash
# 启动守护进程
python tradingview/sync_backup_cli.py daemon

# 详细输出的守护进程
python tradingview/sync_backup_cli.py daemon --verbose

# 后台运行守护进程
nohup python tradingview/sync_backup_cli.py daemon > sync_backup.log 2>&1 &

# 使用systemd管理守护进程
sudo systemctl start tradingview-sync-backup
sudo systemctl enable tradingview-sync-backup
```

### 测试和调试

```bash
# 运行系统功能测试
python tradingview/sync_backup_cli.py test

# 使用指定配置文件
python tradingview/sync_backup_cli.py --config /path/to/config.yaml status

# 详细调试输出
python tradingview/sync_backup_cli.py --verbose status
```

---

## 📊 监控和运维

### Prometheus指标集成

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 启动指标服务器
start_http_server(9090)

# 关键指标
sync_requests_total = Counter('sync_requests_total', 'Total sync requests', ['source', 'target'])
sync_duration_seconds = Histogram('sync_duration_seconds', 'Sync duration')
backup_size_bytes = Gauge('backup_size_bytes', 'Backup file size', ['backup_id'])
system_health_score = Gauge('system_health_score', 'System health score')

# 在应用中记录指标
sync_requests_total.labels(source='primary', target='cache').inc()
sync_duration_seconds.observe(processing_time)
backup_size_bytes.labels(backup_id='backup_123').set(file_size)
```

### 健康检查端点

```python
from fastapi import FastAPI
from tradingview.data_sync_backup import DataSyncBackupController

app = FastAPI()
controller = DataSyncBackupController()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    status = controller.get_system_status()
    
    # 计算健康分数
    health_score = 1.0
    sync_engine = status.get('sync_engine', {})
    
    # 检查活跃任务数
    if sync_engine.get('active_tasks', 0) > 10:
        health_score -= 0.2
    
    # 检查失败任务数
    if sync_engine.get('failed_tasks', 0) > 5:
        health_score -= 0.3
    
    # 检查最近错误
    if sync_engine.get('statistics', {}).get('last_error'):
        health_score -= 0.1
    
    return {
        "status": "healthy" if health_score > 0.7 else "unhealthy",
        "health_score": health_score,
        "details": status,
        "timestamp": int(time.time())
    }

@app.get("/metrics")
async def get_metrics():
    """Prometheus格式指标"""
    status = controller.get_system_status()
    
    metrics = []
    
    # 同步引擎指标
    sync_stats = status.get('sync_engine', {})
    metrics.append(f"sync_active_tasks {sync_stats.get('active_tasks', 0)}")
    metrics.append(f"sync_completed_tasks {sync_stats.get('completed_tasks', 0)}")
    metrics.append(f"sync_failed_tasks {sync_stats.get('failed_tasks', 0)}")
    
    # 备份管理器指标
    backup_stats = status.get('backup_manager', {})
    metrics.append(f"backup_total_count {backup_stats.get('total_backups', 0)}")
    metrics.append(f"backup_total_size_mb {backup_stats.get('total_size_mb', 0)}")
    
    return "\n".join(metrics)
```

### 日志分析

```python
import logging
from datetime import datetime, timedelta

class SyncBackupLogger:
    """同步备份专用日志器"""
    
    def __init__(self):
        self.logger = logging.getLogger('sync_backup')
        self.handler = logging.FileHandler('logs/sync_backup.log')
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
    
    def log_sync_start(self, task_id: str, source: str, target: str):
        """记录同步开始"""
        self.logger.info(f"SYNC_START - Task: {task_id}, {source} -> {target}")
    
    def log_sync_complete(self, task_id: str, duration: float, records: int):
        """记录同步完成"""
        self.logger.info(f"SYNC_COMPLETE - Task: {task_id}, Duration: {duration:.2f}s, Records: {records}")
    
    def log_backup_create(self, backup_id: str, backup_type: str, size_mb: float):
        """记录备份创建"""
        self.logger.info(f"BACKUP_CREATE - ID: {backup_id}, Type: {backup_type}, Size: {size_mb:.2f}MB")
    
    def log_error(self, operation: str, error: str):
        """记录错误"""
        self.logger.error(f"ERROR - Operation: {operation}, Error: {error}")
    
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """分析日志"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        stats = {
            'sync_count': 0,
            'backup_count': 0,
            'error_count': 0,
            'avg_sync_duration': 0.0
        }
        
        try:
            with open('logs/sync_backup.log', 'r') as f:
                for line in f:
                    if 'SYNC_COMPLETE' in line:
                        stats['sync_count'] += 1
                    elif 'BACKUP_CREATE' in line:
                        stats['backup_count'] += 1
                    elif 'ERROR' in line:
                        stats['error_count'] += 1
        
        except FileNotFoundError:
            pass
        
        return stats

# 使用示例
logger = SyncBackupLogger()
logger.log_sync_start("task_123", "primary", "cache")
logger.log_sync_complete("task_123", 5.2, 1000)

# 分析最近24小时的日志
stats = logger.analyze_logs(24)
print(f"同步次数: {stats['sync_count']}")
print(f"备份次数: {stats['backup_count']}")
print(f"错误次数: {stats['error_count']}")
```

### 告警配置

```yaml
# 告警规则配置
monitoring_config:
  alerts:
    enabled: true
    
    # 告警渠道
    channels:
      email:
        enabled: true
        smtp_server: "smtp.example.com"
        recipients: ["admin@example.com"]
      
      webhook:
        enabled: true
        url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      
      log:
        enabled: true
        level: "ERROR"
    
    # 告警规则
    rules:
      sync_failure_rate:
        condition: "sync_failure_rate > 0.1"
        threshold: 0.1
        severity: "critical"
        message: "同步失败率超过10%"
      
      backup_failure:
        condition: "backup_failure_count > 0"
        threshold: 0
        severity: "error"
        message: "备份任务失败"
      
      disk_usage:
        condition: "disk_usage > 0.85"
        threshold: 0.85
        severity: "warning"
        message: "磁盘使用率超过85%"
```

---

## ✅ 最佳实践

### 1. 备份策略最佳实践

```yaml
# 推荐的备份策略
backup_schedule:
  # 全量备份 - 每周日凌晨2点
  full_backup:
    cron: "0 2 * * 0"
    retention_days: 30
  
  # 增量备份 - 每4小时
  incremental_backup:
    cron: "0 */4 * * *"
    retention_days: 7
  
  # 快照备份 - 每小时
  snapshot_backup:
    cron: "0 * * * *"
    retention_days: 1
```

**原因**:
- 全量备份频率低但完整性好
- 增量备份平衡了存储空间和恢复时间
- 快照备份用于快速故障恢复

### 2. 同步优先级管理

```python
# 按重要性和活跃度设置同步优先级
sync_priority_config = {
    # 高优先级 - 热门品种，频繁交易
    'high_priority': {
        'symbols': ['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'],
        'timeframes': ['1', '5', '15'],
        'sync_interval': 60  # 1分钟同步
    },
    
    # 中优先级 - 重要品种，中等活跃度
    'medium_priority': {
        'symbols': ['BINANCE:ADAUSDT', 'FX:EURUSD'],
        'timeframes': ['15', '60'],
        'sync_interval': 300  # 5分钟同步
    },
    
    # 低优先级 - 其他品种，低活跃度
    'low_priority': {
        'symbols': ['*'],  # 其他所有品种
        'timeframes': ['60', '240'],
        'sync_interval': 1800  # 30分钟同步
    }
}
```

### 3. 性能优化配置

```yaml
# 性能优化配置
sync_config:
  # 根据系统资源调整
  max_concurrent_tasks: 8              # CPU核心数
  batch_size: 200                      # 根据内存大小调整
  connection_pool_size: 16             # 2倍并发任务数
  
  # 网络优化
  enable_compression: true
  keep_alive_timeout: 60
  connection_timeout: 30
  
  # 重试策略
  max_retries: 3
  retry_delay_base: 2                  # 指数退避

backup_config:
  # 存储优化
  compression_enabled: true
  compression_level: 6                 # 平衡压缩率和速度
  
  # 并发优化
  max_backup_workers: 2                # 避免I/O竞争
  enable_async_io: true
```

### 4. 资源管理

```python
import psutil
import asyncio
from typing import Dict, Any

class ResourceManager:
    """资源使用监控和管理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_memory_percent = self.config.get('max_memory_percent', 80)
        self.max_cpu_percent = self.config.get('max_cpu_percent', 70)
        self.max_disk_percent = self.config.get('max_disk_percent', 85)
    
    def check_resources(self) -> Dict[str, Any]:
        """检查系统资源使用情况"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        return {
            'memory_percent': memory.percent,
            'cpu_percent': cpu,
            'disk_percent': disk.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_free_gb': disk.free / (1024**3)
        }
    
    def is_resource_available(self) -> bool:
        """检查是否有足够资源执行任务"""
        resources = self.check_resources()
        
        return (
            resources['memory_percent'] < self.max_memory_percent and
            resources['cpu_percent'] < self.max_cpu_percent and
            resources['disk_percent'] < self.max_disk_percent
        )
    
    async def wait_for_resources(self, timeout: int = 300):
        """等待资源可用"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_resource_available():
                return True
            
            await asyncio.sleep(10)
        
        return False

# 在同步任务中使用资源管理
async def resource_aware_sync(controller, task):
    resource_manager = ResourceManager()
    
    # 等待资源可用
    if await resource_manager.wait_for_resources():
        # 执行同步任务
        return await controller.sync_data(task)
    else:
        raise Exception("系统资源不足，跳过同步任务")
```

### 5. 错误处理和恢复

```python
from enum import Enum
import logging

class ErrorRecoveryStrategy(Enum):
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ALERT = "alert"

class ErrorHandler:
    """错误处理和恢复策略"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_strategies = {
            ConnectionError: ErrorRecoveryStrategy.RETRY,
            TimeoutError: ErrorRecoveryStrategy.RETRY,
            ValueError: ErrorRecoveryStrategy.SKIP,
            MemoryError: ErrorRecoveryStrategy.ALERT,
            OSError: ErrorRecoveryStrategy.FALLBACK
        }
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> ErrorRecoveryStrategy:
        """处理错误并返回恢复策略"""
        error_type = type(error)
        strategy = self.error_strategies.get(error_type, ErrorRecoveryStrategy.ALERT)
        
        self.logger.error(f"错误处理: {error_type.__name__}: {error}, 策略: {strategy.value}")
        
        if strategy == ErrorRecoveryStrategy.RETRY:
            return await self._handle_retry(error, context)
        elif strategy == ErrorRecoveryStrategy.FALLBACK:
            return await self._handle_fallback(error, context)
        elif strategy == ErrorRecoveryStrategy.ALERT:
            return await self._handle_alert(error, context)
        
        return strategy
    
    async def _handle_retry(self, error: Exception, context: Dict[str, Any]) -> ErrorRecoveryStrategy:
        """处理重试策略"""
        retry_count = context.get('retry_count', 0)
        max_retries = context.get('max_retries', 3)
        
        if retry_count < max_retries:
            delay = 2 ** retry_count  # 指数退避
            await asyncio.sleep(delay)
            return ErrorRecoveryStrategy.RETRY
        else:
            return ErrorRecoveryStrategy.ALERT
    
    async def _handle_fallback(self, error: Exception, context: Dict[str, Any]) -> ErrorRecoveryStrategy:
        """处理后备策略"""
        # 实现后备数据源或降级服务
        self.logger.info("启用后备策略")
        return ErrorRecoveryStrategy.FALLBACK
    
    async def _handle_alert(self, error: Exception, context: Dict[str, Any]) -> ErrorRecoveryStrategy:
        """处理告警策略"""
        # 发送告警通知
        self.logger.critical(f"严重错误需要人工干预: {error}")
        return ErrorRecoveryStrategy.ALERT

# 在同步过程中使用错误处理
async def resilient_sync_task(task):
    error_handler = ErrorHandler()
    
    for attempt in range(3):
        try:
            return await execute_sync_task(task)
        
        except Exception as e:
            strategy = await error_handler.handle_error(e, {
                'retry_count': attempt,
                'max_retries': 3,
                'task_id': task.task_id
            })
            
            if strategy != ErrorRecoveryStrategy.RETRY:
                break
    
    raise Exception(f"同步任务最终失败: {task.task_id}")
```

---

## 🔧 故障排除

### 常见问题及解决方案

#### 1. 同步任务堆积

**症状**: 同步队列大小持续增长，活跃任务数始终为最大值

```bash
# 检查症状
python tradingview/sync_backup_cli.py status
# 输出: queue_size: 50, active_tasks: 5 (持续不下降)
```

**原因分析**:
- 单个任务执行时间过长
- 数据源响应慢或不稳定
- 系统资源不足

**解决方案**:
```yaml
# 1. 增加并发任务数
sync_config:
  max_concurrent_tasks: 10            # 从5增加到10

# 2. 减少批处理大小
sync_config:
  batch_size: 50                      # 从100减少到50

# 3. 增加超时时间
sync_config:
  timeout_seconds: 60                 # 从30增加到60
```

```python
# 4. 清理队列的紧急处理
async def clear_sync_queue():
    controller = DataSyncBackupController()
    await controller.start()
    
    # 获取同步引擎
    sync_engine = controller.sync_engine
    
    # 清空队列 (紧急情况下使用)
    while not sync_engine.task_queue.empty():
        try:
            task = sync_engine.task_queue.get_nowait()
            print(f"清理任务: {task.task_id}")
        except:
            break
    
    await controller.stop()
```

#### 2. 备份文件损坏

**症状**: 备份恢复时提示校验和不匹配

```bash
# 症状
python tradingview/sync_backup_cli.py restore backup_full_1699123456
# 输出: 错误: 备份文件校验失败
```

**诊断步骤**:
```python
import hashlib
from pathlib import Path

async def diagnose_backup_corruption(backup_id: str):
    """诊断备份文件损坏"""
    backup_manager = DataBackupManager()
    
    # 获取备份记录
    record = backup_manager.backup_records.get(backup_id)
    if not record:
        print(f"备份记录不存在: {backup_id}")
        return
    
    backup_file = Path(record.file_path)
    if not backup_file.exists():
        print(f"备份文件不存在: {backup_file}")
        return
    
    # 重新计算校验和
    current_checksum = await backup_manager._calculate_checksum(backup_file)
    original_checksum = record.checksum
    
    print(f"原始校验和: {original_checksum}")
    print(f"当前校验和: {current_checksum}")
    print(f"文件完整性: {'✅ 完好' if current_checksum == original_checksum else '❌ 损坏'}")
    
    # 检查文件权限
    print(f"文件权限: {oct(backup_file.stat().st_mode)}")
    print(f"文件大小: {backup_file.stat().st_size} bytes")
```

**解决方案**:
```bash
# 1. 使用最近的备份恢复
python tradingview/sync_backup_cli.py list backups
python tradingview/sync_backup_cli.py restore <previous_backup_id>

# 2. 创建新的备份
python tradingview/sync_backup_cli.py backup --type full
```

#### 3. 磁盘空间不足

**症状**: 备份任务失败，提示磁盘空间不足

```bash
# 检查磁盘使用情况
df -h
du -sh data/backups/*
```

**解决方案**:
```python
import shutil
from pathlib import Path

async def cleanup_old_backups():
    """清理旧备份文件"""
    backup_manager = DataBackupManager()
    
    # 获取所有备份记录，按时间排序
    records = sorted(
        backup_manager.backup_records.values(),
        key=lambda x: x.created_at
    )
    
    # 计算总大小
    total_size = sum(record.size_bytes for record in records)
    print(f"当前备份总大小: {total_size / 1024 / 1024 / 1024:.2f} GB")
    
    # 删除最旧的备份直到空间充足
    target_size = total_size * 0.7  # 保留70%
    current_size = total_size
    
    for record in records:
        if current_size <= target_size:
            break
        
        backup_file = Path(record.file_path)
        if backup_file.exists():
            backup_file.unlink()
            current_size -= record.size_bytes
            print(f"删除备份: {record.backup_id}")
    
    print(f"清理后大小: {current_size / 1024 / 1024 / 1024:.2f} GB")
```

```yaml
# 配置自动清理策略
backup_config:
  max_backup_files: 20                # 减少最大备份文件数
  max_total_size_gb: 50               # 设置总大小限制
  
  auto_cleanup:
    enabled: true
    size_threshold_gb: 40             # 超过40GB时自动清理
    retention_policy:
      keep_latest: 5                  # 始终保留最新5个备份
      keep_daily: 7                   # 保留7天内的每日备份
```

#### 4. 内存使用过高

**症状**: 系统内存使用率持续升高，可能导致OOM

```python
import psutil
import gc

async def diagnose_memory_usage():
    """诊断内存使用情况"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"进程内存使用:")
    print(f"  RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"  VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    
    # 系统内存
    system_memory = psutil.virtual_memory()
    print(f"系统内存:")
    print(f"  总内存: {system_memory.total / 1024 / 1024 / 1024:.2f} GB")
    print(f"  已使用: {system_memory.used / 1024 / 1024 / 1024:.2f} GB")
    print(f"  使用率: {system_memory.percent:.1f}%")
    
    # 垃圾回收统计
    gc_stats = gc.get_stats()
    print(f"垃圾回收统计: {gc_stats}")
    
    # 强制垃圾回收
    collected = gc.collect()
    print(f"垃圾回收释放对象数: {collected}")
```

**解决方案**:
```yaml
# 1. 减少缓存大小
sync_config:
  batch_size: 50                      # 减少批处理大小
  max_concurrent_tasks: 3             # 减少并发任务

# 2. 启用内存监控
monitoring_config:
  memory_monitoring:
    enabled: true
    max_memory_percent: 70            # 超过70%时告警
    force_gc_threshold: 80            # 超过80%时强制垃圾回收
```

```python
# 3. 实现内存监控和自动清理
class MemoryMonitor:
    def __init__(self, max_memory_percent: float = 80):
        self.max_memory_percent = max_memory_percent
    
    def check_memory_usage(self) -> float:
        """检查内存使用率"""
        memory = psutil.virtual_memory()
        return memory.percent
    
    async def memory_cleanup_if_needed(self):
        """如果需要则进行内存清理"""
        usage = self.check_memory_usage()
        
        if usage > self.max_memory_percent:
            print(f"内存使用率过高: {usage:.1f}%，开始清理...")
            
            # 强制垃圾回收
            collected = gc.collect()
            print(f"垃圾回收释放对象: {collected}")
            
            # 再次检查
            new_usage = self.check_memory_usage()
            print(f"清理后内存使用率: {new_usage:.1f}%")
            
            return new_usage < self.max_memory_percent
        
        return True

# 在同步任务中使用内存监控
async def memory_aware_sync_task(task):
    memory_monitor = MemoryMonitor(max_memory_percent=75)
    
    # 任务执行前检查内存
    if not await memory_monitor.memory_cleanup_if_needed():
        raise Exception("内存不足，跳过同步任务")
    
    # 执行任务
    result = await execute_sync_task(task)
    
    # 任务完成后清理内存
    await memory_monitor.memory_cleanup_if_needed()
    
    return result
```

### 调试工具和技巧

#### 1. 调试模式启用

```yaml
# 在配置文件中启用调试模式
debug_config:
  debug_mode: true
  verbose_logging: true
  profile_performance: true
  dry_run: false                      # 设为true只模拟不实际执行
```

#### 2. 日志分析脚本

```python
import re
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_sync_logs(log_file: str = "logs/sync_backup.log", hours: int = 24):
    """分析同步日志"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    stats = {
        'sync_started': 0,
        'sync_completed': 0,
        'sync_failed': 0,
        'backup_created': 0,
        'errors': defaultdict(int),
        'avg_sync_duration': 0,
        'task_distribution': defaultdict(int)
    }
    
    total_duration = 0
    duration_count = 0
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # 解析时间戳
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if not timestamp_match:
                    continue
                
                log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                if log_time < cutoff_time:
                    continue
                
                # 分析日志内容
                if 'SYNC_START' in line:
                    stats['sync_started'] += 1
                    
                    # 提取任务类型
                    task_match = re.search(r'(\w+) -> (\w+)', line)
                    if task_match:
                        task_type = f"{task_match.group(1)}_to_{task_match.group(2)}"
                        stats['task_distribution'][task_type] += 1
                
                elif 'SYNC_COMPLETE' in line:
                    stats['sync_completed'] += 1
                    
                    # 提取持续时间
                    duration_match = re.search(r'Duration: ([\d.]+)s', line)
                    if duration_match:
                        duration = float(duration_match.group(1))
                        total_duration += duration
                        duration_count += 1
                
                elif 'BACKUP_CREATE' in line:
                    stats['backup_created'] += 1
                
                elif 'ERROR' in line:
                    stats['sync_failed'] += 1
                    
                    # 分类错误类型
                    if 'ConnectionError' in line:
                        stats['errors']['connection_error'] += 1
                    elif 'TimeoutError' in line:
                        stats['errors']['timeout_error'] += 1
                    elif 'ValueError' in line:
                        stats['errors']['value_error'] += 1
                    else:
                        stats['errors']['other_error'] += 1
    
    except FileNotFoundError:
        print(f"日志文件不存在: {log_file}")
        return stats
    
    # 计算平均持续时间
    if duration_count > 0:
        stats['avg_sync_duration'] = total_duration / duration_count
    
    return stats

# 使用示例
def print_sync_analysis():
    """打印同步分析报告"""
    stats = analyze_sync_logs(hours=24)
    
    print("=== 过去24小时同步分析报告 ===")
    print(f"同步任务启动: {stats['sync_started']}")
    print(f"同步任务完成: {stats['sync_completed']}")
    print(f"同步任务失败: {stats['sync_failed']}")
    print(f"备份任务创建: {stats['backup_created']}")
    print(f"平均同步时间: {stats['avg_sync_duration']:.2f}秒")
    
    if stats['sync_started'] > 0:
        success_rate = stats['sync_completed'] / stats['sync_started'] * 100
        print(f"成功率: {success_rate:.1f}%")
    
    print("\n任务类型分布:")
    for task_type, count in stats['task_distribution'].items():
        print(f"  {task_type}: {count}")
    
    if stats['errors']:
        print("\n错误类型分布:")
        for error_type, count in stats['errors'].items():
            print(f"  {error_type}: {count}")

# 运行分析
print_sync_analysis()
```

---

## 📞 技术支持

### 常见问题FAQ

**Q: 如何优化同步性能？**
A: 1) 增加并发任务数 2) 启用压缩 3) 调整批处理大小 4) 使用SSD存储

**Q: 备份文件太大怎么办？**
A: 1) 启用压缩 2) 使用增量备份 3) 定期清理旧备份 4) 分片存储

**Q: 如何监控系统健康状态？**
A: 1) 使用CLI status命令 2) 集成Prometheus 3) 配置告警规则 4) 查看日志分析

**Q: 恢复速度太慢？**
A: 1) 检查磁盘I/O性能 2) 增加恢复并发数 3) 使用本地存储 4) 优化网络连接

### 获取帮助

- **CLI帮助**: `python tradingview/sync_backup_cli.py --help`
- **配置文档**: 查看 `sync_backup_config.yaml` 注释
- **日志文件**: 检查 `logs/sync_backup.log`
- **健康检查**: 运行 `python tradingview/sync_backup_cli.py test`

---

*本指南涵盖了TradingView数据同步和备份系统的完整使用方法。如有问题，请参考故障排除章节或查看系统日志。*