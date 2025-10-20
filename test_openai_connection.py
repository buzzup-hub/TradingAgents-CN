#!/usr/bin/env python3
"""
测试OpenAI连接工具
"""

import os
import sys
import socket
import requests
import json
from pathlib import Path

def test_openai_connection():
    """测试OpenAI连接配置"""

    print("🔧 OpenAI连接测试工具")
    print("=" * 50)

    # 读取配置
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    print(f"📋 配置信息:")
    print(f"   API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"   Base URL: {base_url}")
    print(f"   完整URL: {base_url}/models")
    print()

    # 测试网络连接
    parsed_url = base_url.replace("http://", "").replace("https://", "").split("/")[0]
    host, port = parsed_url.split(":") if ":" in parsed_url else (parsed_url, 80)
    port = int(port)

    print(f"🌐 网络连接测试:")
    print(f"   主机: {host}")
    print(f"   端口: {port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"   ✅ TCP连接成功")
        else:
            print(f"   ❌ TCP连接失败，错误代码: {result}")
            error_codes = {
                11: 'Resource temporarily unavailable (EAGAIN)',
                111: 'Connection refused (ECONNREFUSED)',
                113: 'No route to host (ENETUNREACH)',
                110: 'Connection timed out (ETIMEDOUT)'
            }
            print(f"      {error_codes.get(result, '未知错误')}")
            return False
    except Exception as e:
        print(f"   ❌ 网络测试异常: {e}")
        return False

    print()

    # 测试API调用
    print(f"🔗 API调用测试:")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        # 测试模型列表
        response = requests.get(f"{base_url}/models", headers=headers, timeout=10)

        if response.status_code == 200:
            print(f"   ✅ API调用成功 (状态码: {response.status_code})")

            try:
                models = response.json()
                if "data" in models and models["data"]:
                    print(f"   📊 可用模型数量: {len(models['data'])}")
                    print(f"   📝 部分模型:")
                    for i, model in enumerate(models["data"][:5]):  # 只显示前5个
                        model_id = model.get("id", "unknown")
                        print(f"      {i+1}. {model_id}")
                    if len(models["data"]) > 5:
                        print(f"      ... 还有 {len(models['data']) - 5} 个模型")
            except:
                print(f"   📝 响应格式检查失败")
        else:
            print(f"   ❌ API调用失败 (状态码: {response.status_code})")
            print(f"   📝 错误响应: {response.text[:200]}...")
            return False

    except requests.exceptions.Timeout:
        print(f"   ❌ API调用超时")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ API连接错误: {e}")
        return False
    except Exception as e:
        print(f"   ❌ API调用异常: {e}")
        return False

    print()
    print(f"🎉 测试完成！OpenAI服务正常工作")
    return True

def test_specific_url(url, api_key):
    """测试特定URL"""
    print(f"🔧 测试特定URL: {url}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{url}/models", headers=headers, timeout=10)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"   ✅ 连接成功！可用模型: {len(models.get('data', []))}")
            return True
        else:
            print(f"   ❌ 连接失败: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return False

if __name__ == "__main__":
    # 加载环境变量
    project_root = Path(__file__).parent
    env_file = project_root / ".env"

    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✅ 已加载环境变量: {env_file}")
    else:
        print(f"⚠️  未找到.env文件: {env_file}")

    # 测试主配置
    success = test_openai_connection()

    if not success:
        print()
        print(f"🔄 尝试其他可能的URL:")

        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            # 测试一些常见的替代URL
            alternative_urls = [
                "http://192.168.124.195:13000/v1",
                "http://192.168.124.195:13000",
                "http://localhost:13000/v1",
                "http://127.0.0.1:13000/v1",
                "http://host.docker.internal:13000/v1"
            ]

            for url in alternative_urls:
                print(f"\n🔗 测试: {url}")
                test_specific_url(url, api_key)

    print(f"\n" + "=" * 50)
    print(f"测试完成！")