#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TradingView账号配置管理CLI工具
提供命令行界面管理TradingView认证配置
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Optional
import getpass
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tradingview.auth_config import (
    TradingViewAuthManager, 
    TradingViewAccount, 
    get_auth_manager,
    create_account_from_env
)
from config.logging_config import get_logger

logger = get_logger(__name__)


class AuthCLI:
    """认证配置CLI管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.auth_manager = get_auth_manager(config_file)
    
    def cmd_list(self, args):
        """列出所有账号配置"""
        print("📋 TradingView账号配置列表")
        print("=" * 60)
        
        accounts = self.auth_manager.list_accounts()
        
        if not accounts:
            print("❌ 没有找到任何账号配置")
            print("\n💡 提示:")
            print("   1. 设置环境变量: export TV_SESSION=xxx TV_SIGNATURE=xxx")
            print("   2. 或使用命令添加配置: python auth_cli.py add")
            return
        
        # 显示账号信息
        for i, account in enumerate(accounts, 1):
            status_icon = "🟢" if account['is_active'] else "🔴"
            default_icon = "⭐" if account['is_default'] else "  "
            source_icon = "🌍" if account['source'] == 'environment' else "📁"
            
            print(f"{i:2d}. {default_icon} {status_icon} {source_icon} {account['name']}")
            print(f"     服务器: {account['server']}")
            print(f"     来源: {'环境变量' if account['source'] == 'environment' else '配置文件'}")
            
            if account['description']:
                print(f"     描述: {account['description']}")
            
            if account.get('created_at'):
                created_time = datetime.fromisoformat(account['created_at']).strftime('%Y-%m-%d %H:%M')
                print(f"     创建: {created_time}")
            
            if account.get('last_used'):
                used_time = datetime.fromisoformat(account['last_used']).strftime('%Y-%m-%d %H:%M')
                print(f"     最后使用: {used_time}")
            
            print()
        
        print("图例: ⭐=默认 🟢=激活 🔴=禁用 🌍=环境变量 📁=配置文件")
    
    def cmd_add(self, args):
        """添加账号配置"""
        print("✨ 添加TradingView账号配置")
        print("=" * 40)
        
        # 检查是否从环境变量创建
        if args.from_env:
            account = create_account_from_env()
            if not account:
                print("❌ 环境变量中未找到TV_SESSION和TV_SIGNATURE")
                print("请先设置环境变量:")
                print("   export TV_SESSION='your_session_token'")
                print("   export TV_SIGNATURE='your_signature'")
                return
        else:
            # 手动输入账号信息
            print("请输入账号信息:")
            
            name = input("账号名称: ").strip()
            if not name:
                print("❌ 账号名称不能为空")
                return
            
            session_token = getpass.getpass("Session Token (TV_SESSION): ").strip()
            if not session_token:
                print("❌ Session Token不能为空")
                return
            
            signature = getpass.getpass("Signature (TV_SIGNATURE): ").strip()
            if not signature:
                print("❌ Signature不能为空")
                return
            
            server = input("服务器 [data]: ").strip() or "data"
            description = input("描述 (可选): ").strip()
            
            account = TradingViewAccount(
                name=name,
                session_token=session_token,
                signature=signature,
                server=server,
                description=description
            )
        
        # 验证账号配置
        if not self.auth_manager.validate_account(account):
            print("❌ 账号配置验证失败")
            return
        
        # 添加账号
        set_as_default = args.set_default or input("设为默认账号? [y/N]: ").lower() == 'y'
        
        if self.auth_manager.add_account(account, set_as_default):
            print(f"✅ 成功添加账号: {account.name}")
            if set_as_default:
                print("⭐ 已设为默认账号")
        else:
            print("❌ 添加账号失败")
    
    def cmd_remove(self, args):
        """删除账号配置"""
        account_name = args.name
        
        # 确认删除
        if not args.force:
            confirm = input(f"确认删除账号 '{account_name}'? [y/N]: ").lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        if self.auth_manager.remove_account(account_name):
            print(f"✅ 成功删除账号: {account_name}")
        else:
            print(f"❌ 删除账号失败: {account_name}")
    
    def cmd_update(self, args):
        """更新账号配置"""
        account_name = args.name
        updates = {}
        
        # 收集更新字段
        if args.server:
            updates['server'] = args.server
        
        if args.description is not None:
            updates['description'] = args.description
        
        if args.active is not None:
            updates['is_active'] = args.active
        
        if not updates:
            print("❌ 没有指定要更新的字段")
            return
        
        if self.auth_manager.update_account(account_name, **updates):
            print(f"✅ 成功更新账号: {account_name}")
            for key, value in updates.items():
                print(f"   {key}: {value}")
        else:
            print(f"❌ 更新账号失败: {account_name}")
    
    def cmd_default(self, args):
        """设置默认账号"""
        account_name = args.name
        
        if self.auth_manager.set_default_account(account_name):
            print(f"✅ 已设置默认账号: {account_name}")
        else:
            print(f"❌ 设置默认账号失败: {account_name}")
    
    def cmd_test(self, args):
        """测试账号配置"""
        account_name = args.name if hasattr(args, 'name') else None
        
        print(f"🧪 测试账号配置: {account_name or '默认账号'}")
        print("=" * 40)
        
        # 获取账号配置
        account = self.auth_manager.get_account(account_name)
        
        if not account:
            print("❌ 未找到指定账号配置")
            return
        
        print(f"📋 账号信息:")
        print(f"   名称: {account.name}")
        print(f"   服务器: {account.server}")
        print(f"   描述: {account.description}")
        print(f"   Token: {(account.session_token)} ")
        print(f"   Signature: {(account.signature)} ")
        print(f"   Token长度: {len(account.session_token)} 字符")
        print(f"   Signature长度: {len(account.signature)} 字符")
        
        # 基础验证
        if self.auth_manager.validate_account(account):
            print("✅ 账号配置格式验证通过")
        else:
            print("❌ 账号配置格式验证失败")
            return
        
        # 连接测试（需要导入TradingView客户端）
        try:
            import asyncio
            from tradingview.client import Client
            
            async def test_connection():
                client = Client({
                    'token': account.session_token,
                    'signature': account.signature,
                    'server': account.server
                })
                
                try:
                    print("🔄 测试连接...")
                    await client.connect()
                    
                    if client.is_logged and client.is_open:
                        print("✅ 连接测试成功")
                        return True
                    else:
                        print("❌ 连接测试失败: 未能完成登录")
                        return False
                        
                except Exception as e:
                    print(f"❌ 连接测试失败: {e}")
                    return False
                finally:
                    if client:
                        await client.end()
            
            # 运行连接测试
            success = asyncio.run(test_connection())
            
            if success:
                # 更新最后使用时间
                account.update_last_used()
                print("📝 已更新最后使用时间")
            
        except ImportError:
            print("⚠️  无法导入TradingView客户端，跳过连接测试")
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
    
    def cmd_export(self, args):
        """导出账号配置"""
        accounts = self.auth_manager.list_accounts()
        
        # 过滤掉环境变量配置
        config_accounts = [acc for acc in accounts if acc['source'] == 'config_file']
        
        if not config_accounts:
            print("❌ 没有可导出的配置文件账号")
            return
        
        export_data = {
            'accounts': config_accounts,
            'exported_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        output_file = args.output or 'tradingview_accounts_export.json'
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 配置已导出到: {output_file}")
            print(f"📊 导出账号数量: {len(config_accounts)}")
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
    
    def cmd_import(self, args):
        """导入账号配置"""
        import_file = args.file
        
        if not os.path.exists(import_file):
            print(f"❌ 导入文件不存在: {import_file}")
            return
        
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            accounts_data = import_data.get('accounts', [])
            if not accounts_data:
                print("❌ 导入文件中没有找到账号配置")
                return
            
            print(f"📋 准备导入 {len(accounts_data)} 个账号配置")
            
            imported_count = 0
            for acc_data in accounts_data:
                try:
                    # 移除source等运行时字段
                    clean_data = {
                        'name': acc_data['name'],
                        'server': acc_data['server'],
                        'description': acc_data['description'],
                        'is_active': acc_data['is_active']
                    }
                    
                    # 需要用户输入敏感信息
                    print(f"\n导入账号: {acc_data['name']}")
                    session_token = getpass.getpass("Session Token: ").strip()
                    signature = getpass.getpass("Signature: ").strip()
                    
                    if not session_token or not signature:
                        print("跳过该账号（缺少认证信息）")
                        continue
                    
                    account = TradingViewAccount(
                        session_token=session_token,
                        signature=signature,  
                        **clean_data
                    )
                    
                    if self.auth_manager.add_account(account):
                        imported_count += 1
                        print(f"✅ 导入成功: {account.name}")
                    else:
                        print(f"❌ 导入失败: {account.name}")
                        
                except Exception as e:
                    print(f"❌ 导入账号失败: {e}")
            
            print(f"\n📊 导入完成，成功导入 {imported_count} 个账号")
            
        except Exception as e:
            print(f"❌ 导入失败: {e}")
    
    def cmd_encrypt(self, args):
        """启用配置加密"""
        password = None
        
        if args.password:
            password = getpass.getpass("请输入加密密码: ")
            if not password:
                print("❌ 密码不能为空")
                return
        
        if self.auth_manager.enable_encryption(password):
            print("✅ 已启用配置文件加密")
            if not password:
                print("💡 使用默认加密密码（基于机器标识）")
        else:
            print("❌ 启用加密失败")
    
    def cmd_decrypt(self, args):
        """禁用配置加密"""
        if not args.force:
            confirm = input("确认禁用配置文件加密? [y/N]: ").lower()
            if confirm != 'y':
                print("操作已取消")
                return
        
        if self.auth_manager.disable_encryption():
            print("✅ 已禁用配置文件加密")
        else:
            print("❌ 禁用加密失败")


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description='TradingView账号配置管理CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 列出所有账号配置
  python auth_cli.py list
  
  # 从环境变量添加账号
  python auth_cli.py add --from-env --set-default
  
  # 手动添加账号
  python auth_cli.py add
  
  # 设置默认账号
  python auth_cli.py default my_account
  
  # 测试账号连接
  python auth_cli.py test my_account
  
  # 更新账号信息
  python auth_cli.py update my_account --server prodata --description "生产账号"
  
  # 删除账号
  python auth_cli.py remove my_account --force
  
  # 启用配置加密
  python auth_cli.py encrypt --password
  
  # 导出配置
  python auth_cli.py export --output my_accounts.json
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        help='配置文件路径',
        default=None
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有账号配置')
    
    # add 命令
    add_parser = subparsers.add_parser('add', help='添加账号配置')
    add_parser.add_argument('--from-env', action='store_true', help='从环境变量创建账号')
    add_parser.add_argument('--set-default', action='store_true', help='设为默认账号')
    
    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除账号配置')
    remove_parser.add_argument('name', help='账号名称')
    remove_parser.add_argument('--force', action='store_true', help='强制删除，不确认')
    
    # update 命令
    update_parser = subparsers.add_parser('update', help='更新账号配置')
    update_parser.add_argument('name', help='账号名称')
    update_parser.add_argument('--server', help='服务器')
    update_parser.add_argument('--description', help='描述')
    update_parser.add_argument('--active', type=bool, help='是否激活')
    
    # default 命令
    default_parser = subparsers.add_parser('default', help='设置默认账号')
    default_parser.add_argument('name', help='账号名称')
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='测试账号配置')
    test_parser.add_argument('name', nargs='?', help='账号名称（可选，默认测试默认账号）')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出账号配置')
    export_parser.add_argument('--output', help='输出文件路径')
    
    # import 命令
    import_parser = subparsers.add_parser('import', help='导入账号配置')
    import_parser.add_argument('file', help='导入文件路径')
    
    # encrypt 命令
    encrypt_parser = subparsers.add_parser('encrypt', help='启用配置加密')
    encrypt_parser.add_argument('--password', action='store_true', help='使用自定义密码')
    
    # decrypt 命令
    decrypt_parser = subparsers.add_parser('decrypt', help='禁用配置加密')
    decrypt_parser.add_argument('--force', action='store_true', help='强制禁用，不确认')
    
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        cli = AuthCLI(args.config)
        
        # 执行命令
        command_method = getattr(cli, f'cmd_{args.command}', None)
        if command_method:
            command_method(args)
        else:
            print(f"未知命令: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"CLI执行失败: {e}")
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()