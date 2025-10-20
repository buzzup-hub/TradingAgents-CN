#!/usr/bin/env python3
"""
临时修复OpenAI配置
"""

import os
from pathlib import Path

def fix_openai_config():
    """临时修复OpenAI配置以使用可用的服务"""

    # 这里可以设置一个你知道工作的OpenAI兼容服务
    working_configs = [
        {
            "name": "自定义本地服务",
            "url": "http://127.0.0.1:8000/v1",
            "description": "如果你有本地运行的OpenAI兼容服务"
        },
        {
            "name": "OpenRouter（免费）",
            "url": "https://openrouter.ai/api/v1",
            "description": "使用OpenRouter，提供免费模型"
        },
        {
            "name": "DeepSeek（推荐）",
            "url": "https://api.deepseek.com",
            "description": "使用DeepSeek API，性价比高"
        }
    ]

    print("🔧 可用的OpenAI兼容服务:")
    print("=" * 50)

    for i, config in enumerate(working_configs, 1):
        print(f"{i}. {config['name']}")
        print(f"   URL: {config['url']}")
        print(f"   说明: {config['description']}")
        print()

    print("请选择一个服务，然后运行以下命令更新配置:")
    print(f"export OPENAI_BASE_URL=<选择的URL>")
    print("或者直接修改 .env 文件")

if __name__ == "__main__":
    fix_openai_config()