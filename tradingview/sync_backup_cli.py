#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView数据同步和备份CLI工具
提供命令行界面管理数据同步、备份和恢复操作
"""

import asyncio
import argparse
import json
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from data_sync_backup import (
    DataSyncBackupController, 
    SyncTask, 
    BackupType, 
    SyncStatus
)
from config.logging_config import get_logger

logger = get_logger(__name__)


class SyncBackupCLI:
    """数据同步备份命令行界面"""
    
    def __init__(self, config_file: str = None):
        """初始化CLI"""
        self.config_file = config_file or "tradingview/sync_backup_config.yaml"
        self.config = self._load_config()
        self.controller = DataSyncBackupController(self.config)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
            return self._get_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"已加载配置文件: {self.config_file}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'sync_config': {
                'sync_interval': 300,
                'batch_size': 100,
                'max_concurrent_tasks': 5
            },
            'backup_config': {
                'backup_dir': 'data/backups',
                'max_backup_files': 30,
                'compression_enabled': True
            },
            'schedule_enabled': False  # CLI模式下默认不启用定时任务
        }
    
    async def run_command(self, args):
        """运行CLI命令"""
        try:
            if args.command == 'status':
                await self._cmd_status(args)
            elif args.command == 'backup':
                await self._cmd_backup(args)
            elif args.command == 'restore':
                await self._cmd_restore(args)
            elif args.command == 'sync':
                await self._cmd_sync(args)
            elif args.command == 'list':
                await self._cmd_list(args)
            elif args.command == 'daemon':
                await self._cmd_daemon(args)
            elif args.command == 'test':
                await self._cmd_test(args)
            else:
                print(f"未知命令: {args.command}")
                sys.exit(1)
        
        except KeyboardInterrupt:
            print("\n操作被用户中断")
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            print(f"错误: {e}")
            sys.exit(1)
    
    async def _cmd_status(self, args):
        """查看系统状态"""
        print("🔍 获取系统状态...")
        
        # 启动系统以获取状态
        await self.controller.start()
        
        try:
            status = self.controller.get_system_status()
            
            print("\n" + "="*60)
            print(" TradingView 数据同步备份系统状态")
            print("="*60)
            
            # 同步引擎状态
            sync_status = status.get('sync_engine', {})
            print(f"\n📡 同步引擎:")
            print(f"  状态: {'🟢 运行中' if sync_status.get('is_running') else '🔴 已停止'}")
            print(f"  活跃任务: {sync_status.get('active_tasks', 0)}")
            print(f"  已完成任务: {sync_status.get('completed_tasks', 0)}")
            print(f"  失败任务: {sync_status.get('failed_tasks', 0)}")
            print(f"  队列大小: {sync_status.get('queue_size', 0)}")
            
            stats = sync_status.get('statistics', {})
            print(f"  总同步数: {stats.get('total_synced', 0)}")
            print(f"  总失败数: {stats.get('total_failed', 0)}")
            print(f"  同步速度: {stats.get('sync_speed', 0):.2f} records/sec")
            
            # 备份管理器状态
            backup_status = status.get('backup_manager', {})
            print(f"\n💾 备份管理器:")
            print(f"  总备份数: {backup_status.get('total_backups', 0)}")
            print(f"  总大小: {backup_status.get('total_size_mb', 0):.2f} MB")
            print(f"  备份目录: {backup_status.get('backup_dir', 'N/A')}")
            
            # 最近备份记录
            records = backup_status.get('backup_records', [])
            if records:
                print(f"\n📋 最近备份记录 (显示最新5个):")
                for record in records[-5:]:
                    created_time = datetime.fromtimestamp(record['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  • {record['backup_id'][:20]}... ({record['backup_type']}) - {created_time} - {record['size_bytes']/1024/1024:.1f}MB")
            
            print(f"\n⏰ 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔧 定时任务: {'启用' if status.get('schedule_enabled') else '禁用'}")
            
        finally:
            await self.controller.stop()
    
    async def _cmd_backup(self, args):
        """创建备份"""
        backup_type_map = {
            'full': BackupType.FULL,
            'incremental': BackupType.INCREMENTAL,
            'snapshot': BackupType.SNAPSHOT
        }
        
        if args.type not in backup_type_map:
            print(f"错误: 不支持的备份类型 '{args.type}'")
            print("支持的类型: full, incremental, snapshot")
            sys.exit(1)
        
        backup_type = backup_type_map[args.type]
        symbols = args.symbols.split(',') if args.symbols else None
        timeframes = args.timeframes.split(',') if args.timeframes else None
        
        print(f"🎯 开始创建 {args.type} 备份...")
        if symbols:
            print(f"   品种: {', '.join(symbols)}")
        if timeframes:
            print(f"   时间框架: {', '.join(timeframes)}")
        
        await self.controller.start()
        
        try:
            backup_id = await self.controller.create_manual_backup(
                backup_type, symbols, timeframes
            )
            
            if backup_id:
                print(f"✅ 备份创建成功!")
                print(f"   备份ID: {backup_id}")
                
                # 获取备份详情
                backup_info = self.controller.backup_manager.get_backup_info(backup_id)
                if backup_info:
                    print(f"   文件大小: {backup_info['size_bytes']/1024/1024:.2f} MB")
                    created_time = datetime.fromtimestamp(backup_info['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   创建时间: {created_time}")
                    print(f"   数据范围: {backup_info['symbols_count']} 个品种")
            else:
                print("❌ 备份创建失败")
                sys.exit(1)
        
        finally:
            await self.controller.stop()
    
    async def _cmd_restore(self, args):
        """恢复备份"""
        print(f"🔄 开始恢复备份: {args.backup_id}")
        
        await self.controller.start()
        
        try:
            # 检查备份是否存在
            backup_info = self.controller.backup_manager.get_backup_info(args.backup_id)
            if not backup_info:
                print(f"❌ 备份不存在: {args.backup_id}")
                sys.exit(1)
            
            print(f"   备份类型: {backup_info['backup_type']}")
            print(f"   备份大小: {backup_info['size_bytes']/1024/1024:.2f} MB")
            created_time = datetime.fromtimestamp(backup_info['created_at']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   创建时间: {created_time}")
            
            if not args.force:
                confirm = input("确认恢复此备份? (y/N): ")
                if confirm.lower() != 'y':
                    print("操作已取消")
                    return
            
            success = await self.controller.restore_from_backup(
                args.backup_id, args.target_db
            )
            
            if success:
                print("✅ 备份恢复成功!")
                if args.target_db:
                    print(f"   恢复到: {args.target_db}")
                else:
                    print("   恢复到: 缓存系统")
            else:
                print("❌ 备份恢复失败")
                sys.exit(1)
        
        finally:
            await self.controller.stop()
    
    async def _cmd_sync(self, args):
        """执行数据同步"""
        if args.source not in ['primary', 'cache', 'backup']:
            print("错误: source 必须是 primary, cache, 或 backup")
            sys.exit(1)
        
        if args.target not in ['cache', 'backup', 'remote']:
            print("错误: target 必须是 cache, backup, 或 remote")
            sys.exit(1)
        
        symbols = args.symbols.split(',') if args.symbols else ['BINANCE:BTCUSDT']
        timeframes = args.timeframes.split(',') if args.timeframes else ['15']
        
        print(f"🔄 开始数据同步:")
        print(f"   源: {args.source}")
        print(f"   目标: {args.target}")
        print(f"   品种: {', '.join(symbols)}")
        print(f"   时间框架: {', '.join(timeframes)}")
        
        await self.controller.start()
        
        try:
            task_id = await self.controller.sync_data(
                args.source, args.target, symbols, timeframes
            )
            
            print(f"✅ 同步任务已添加: {task_id}")
            
            # 等待任务完成
            if args.wait:
                print("⏳ 等待任务完成...")
                
                for i in range(30):  # 最多等待30秒
                    await asyncio.sleep(1)
                    status = self.controller.get_system_status()
                    
                    # 检查任务是否完成
                    sync_status = status.get('sync_engine', {})
                    if sync_status.get('active_tasks', 0) == 0:
                        print("✅ 同步任务完成!")
                        break
                    
                    print(f"   进度: {i+1}/30秒")
                else:
                    print("⚠️  任务仍在进行中，请稍后查看状态")
        
        finally:
            await self.controller.stop()
    
    async def _cmd_list(self, args):
        """列出备份或任务"""
        if args.type == 'backups':
            await self._list_backups(args)
        elif args.type == 'tasks':
            await self._list_tasks(args)
        else:
            print("错误: type 必须是 backups 或 tasks")
            sys.exit(1)
    
    async def _list_backups(self, args):
        """列出备份"""
        print("📋 备份列表:")
        
        await self.controller.start()
        
        try:
            backup_info = self.controller.backup_manager.get_backup_info()
            records = backup_info.get('backup_records', [])
            
            if not records:
                print("   没有找到备份记录")
                return
            
            # 按创建时间排序
            records.sort(key=lambda x: x['created_at'], reverse=True)
            
            print(f"\n总共 {len(records)} 个备份，总大小 {backup_info.get('total_size_mb', 0):.2f} MB\n")
            
            # 表头
            print(f"{'备份ID':<25} {'类型':<12} {'大小(MB)':<10} {'品种数':<8} {'创建时间':<20}")
            print("-" * 80)
            
            # 显示备份记录
            for record in records:
                backup_id = record['backup_id'][:22] + "..." if len(record['backup_id']) > 25 else record['backup_id']
                size_mb = record['size_bytes'] / 1024 / 1024
                created_time = datetime.fromtimestamp(record['created_at']).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"{backup_id:<25} {record['backup_type']:<12} {size_mb:<10.2f} {record['symbols_count']:<8} {created_time:<20}")
            
            if args.verbose:
                print(f"\n备份目录: {backup_info.get('backup_dir')}")
        
        finally:
            await self.controller.stop()
    
    async def _list_tasks(self, args):
        """列出同步任务"""
        print("📋 同步任务列表:")
        
        await self.controller.start()
        
        try:
            status = self.controller.get_system_status()
            sync_status = status.get('sync_engine', {})
            
            print(f"\n活跃任务: {sync_status.get('active_tasks', 0)}")
            print(f"已完成任务: {sync_status.get('completed_tasks', 0)}")
            print(f"失败任务: {sync_status.get('failed_tasks', 0)}")
            print(f"队列大小: {sync_status.get('queue_size', 0)}")
            
            stats = sync_status.get('statistics', {})
            if stats:
                print(f"\n统计信息:")
                print(f"  总同步数: {stats.get('total_synced', 0)}")
                print(f"  总失败数: {stats.get('total_failed', 0)}")
                print(f"  同步速度: {stats.get('sync_speed', 0):.2f} records/sec")
                
                if stats.get('last_error'):
                    print(f"  最后错误: {stats['last_error']}")
        
        finally:
            await self.controller.stop()
    
    async def _cmd_daemon(self, args):
        """以守护进程模式运行"""
        print("🚀 启动TradingView数据同步备份守护进程...")
        
        # 启用定时任务
        daemon_config = self.config.copy()
        daemon_config['schedule_enabled'] = True
        
        controller = DataSyncBackupController(daemon_config)
        
        try:
            await controller.start()
            print("✅ 守护进程已启动")
            print("   按 Ctrl+C 停止服务")
            
            # 持续运行
            while True:
                await asyncio.sleep(60)
                
                # 每分钟输出一次状态
                if args.verbose:
                    status = controller.get_system_status()
                    sync_stats = status.get('sync_engine', {})
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"活跃任务: {sync_stats.get('active_tasks', 0)}, "
                          f"队列: {sync_stats.get('queue_size', 0)}")
        
        except KeyboardInterrupt:
            print("\n📴 正在停止守护进程...")
        
        finally:
            await controller.stop()
            print("✅ 守护进程已停止")
    
    async def _cmd_test(self, args):
        """测试系统功能"""
        print("🧪 开始系统功能测试...")
        
        await self.controller.start()
        
        try:
            # 测试1: 系统状态
            print("\n1️⃣ 测试系统状态...")
            status = self.controller.get_system_status()
            if status:
                print("   ✅ 系统状态正常")
            else:
                print("   ❌ 系统状态异常")
            
            # 测试2: 创建测试备份
            print("\n2️⃣ 测试备份创建...")
            backup_id = await self.controller.create_manual_backup(
                BackupType.SNAPSHOT,
                symbols=['BINANCE:BTCUSDT'],
                timeframes=['15']
            )
            
            if backup_id:
                print(f"   ✅ 备份创建成功: {backup_id}")
                
                # 测试3: 备份恢复
                print("\n3️⃣ 测试备份恢复...")
                success = await self.controller.restore_from_backup(backup_id)
                if success:
                    print("   ✅ 备份恢复成功")
                else:
                    print("   ❌ 备份恢复失败")
            else:
                print("   ❌ 备份创建失败")
            
            # 测试4: 数据同步
            print("\n4️⃣ 测试数据同步...")
            task_id = await self.controller.sync_data(
                "primary", "cache", 
                ['BINANCE:BTCUSDT'], ['15']
            )
            
            if task_id:
                print(f"   ✅ 同步任务创建成功: {task_id}")
                
                # 等待任务完成
                await asyncio.sleep(3)
                
                final_status = self.controller.get_system_status()
                sync_stats = final_status.get('sync_engine', {}).get('statistics', {})
                
                if sync_stats.get('total_synced', 0) > 0:
                    print("   ✅ 数据同步成功")
                else:
                    print("   ⚠️  同步任务正在进行中")
            else:
                print("   ❌ 同步任务创建失败")
            
            print("\n🎉 系统功能测试完成!")
        
        finally:
            await self.controller.stop()


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description='TradingView数据同步备份CLI工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 查看系统状态
  python sync_backup_cli.py status
  
  # 创建全量备份
  python sync_backup_cli.py backup --type full
  
  # 创建指定品种的增量备份
  python sync_backup_cli.py backup --type incremental --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT
  
  # 恢复备份
  python sync_backup_cli.py restore backup_full_1699123456
  
  # 同步数据
  python sync_backup_cli.py sync --source primary --target cache --symbols BINANCE:BTCUSDT
  
  # 列出所有备份
  python sync_backup_cli.py list backups
  
  # 启动守护进程
  python sync_backup_cli.py daemon
  
  # 运行系统测试
  python sync_backup_cli.py test
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        help='配置文件路径',
        default='tradingview/sync_backup_config.yaml'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='查看系统状态')
    
    # backup 命令
    backup_parser = subparsers.add_parser('backup', help='创建备份')
    backup_parser.add_argument(
        '--type', 
        choices=['full', 'incremental', 'snapshot'],
        required=True,
        help='备份类型'
    )
    backup_parser.add_argument(
        '--symbols',
        help='要备份的品种 (逗号分隔)'
    )
    backup_parser.add_argument(
        '--timeframes',
        help='要备份的时间框架 (逗号分隔)'
    )
    
    # restore 命令
    restore_parser = subparsers.add_parser('restore', help='恢复备份')
    restore_parser.add_argument(
        'backup_id',
        help='备份ID'
    )
    restore_parser.add_argument(
        '--target-db',
        help='目标数据库文件路径'
    )
    restore_parser.add_argument(
        '--force',
        action='store_true',
        help='强制恢复，不提示确认'
    )
    
    # sync 命令
    sync_parser = subparsers.add_parser('sync', help='执行数据同步')
    sync_parser.add_argument(
        '--source',
        choices=['primary', 'cache', 'backup'],
        required=True,
        help='源数据类型'
    )
    sync_parser.add_argument(
        '--target',
        choices=['cache', 'backup', 'remote'],
        required=True,
        help='目标数据类型'
    )
    sync_parser.add_argument(
        '--symbols',
        help='要同步的品种 (逗号分隔)'
    )
    sync_parser.add_argument(
        '--timeframes',
        help='要同步的时间框架 (逗号分隔)'
    )
    sync_parser.add_argument(
        '--wait',
        action='store_true',
        help='等待同步任务完成'
    )
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出备份或任务')
    list_parser.add_argument(
        'type',
        choices=['backups', 'tasks'],
        help='列出类型'
    )
    list_parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细信息'
    )
    
    # daemon 命令
    daemon_parser = subparsers.add_parser('daemon', help='以守护进程模式运行')
    daemon_parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出'
    )
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='运行系统功能测试')
    
    return parser


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # 创建CLI实例并运行命令
    cli = SyncBackupCLI(args.config)
    await cli.run_command(args)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
        sys.exit(0)