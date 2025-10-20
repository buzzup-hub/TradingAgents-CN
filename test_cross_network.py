#!/usr/bin/env python3
"""
跨网络连接测试工具
"""

import subprocess
import socket

def test_cross_network():
    """测试跨网络连接"""

    target_ip = "192.168.124.195"
    target_port = 13000

    print(f"🔍 测试到 {target_ip}:{target_port} 的连接")
    print("=" * 50)

    # 1. 从宿主机测试
    print("1. 从宿主机测试:")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((target_ip, target_port))
        sock.close()

        if result == 0:
            print(f"   ✅ 宿主机连接成功")
        else:
            print(f"   ❌ 宿主机连接失败，错误代码: {result}")
    except Exception as e:
        print(f"   ❌ 宿主机测试异常: {e}")

    # 2. 从Docker容器内测试
    print("\n2. 从Docker容器内测试:")
    try:
        # 使用docker exec执行Python代码
        cmd = [
            "docker", "exec", "TradingAgents-web", "python", "-c",
            f"""
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
result = sock.connect_ex(('{target_ip}', {target_port}))
sock.close()

if result == 0:
    print("   ✅ 容器内连接成功")
else:
    print(f"   ❌ 容器内连接失败，错误代码: {{result}}")
    sys.exit(1)
            """
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"   {result.stdout.strip()}")
        if result.stderr:
            print(f"   错误: {result.stderr.strip()}")

    except Exception as e:
        print(f"   ❌ 容器内测试异常: {e}")

    # 3. 网络诊断建议
    print(f"\n📋 网络诊断建议:")
    print("=" * 50)
    print("如果连接失败，请检查以下事项:")
    print(f"1. 目标服务器 {target_ip} 是否正在运行")
    print(f"2. 端口 {target_port} 是否开放")
    print(f"3. 防火墙是否允许来自你机器的连接")
    print(f"4. 两个机器是否在同一网络中")
    print(f"5. 路由器是否正确配置")

if __name__ == "__main__":
    test_cross_network()