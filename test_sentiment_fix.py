#!/usr/bin/env python3
"""
测试社交媒体分析师修复
验证情绪报告能够正常生成
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tradingagents.utils.logging_init import get_logger
logger = get_logger("test")

def test_sentiment_analyst():
    """测试社交媒体分析师功能"""
    print("=" * 80)
    print("🧪 测试社交媒体分析师修复")
    print("=" * 80)

    try:
        # 1. 导入必要的模块
        from tradingagents.agents.analysts.social_media_analyst import create_social_media_analyst
        from tradingagents.graph.toolkit import TradingToolkit
        from tradingagents.default_config import DEFAULT_CONFIG
        from langchain_openai import ChatOpenAI

        print("\n✅ 模块导入成功")

        # 2. 创建工具包
        config = DEFAULT_CONFIG.copy()
        config["online_tools"] = False  # 使用离线模式测试
        toolkit = TradingToolkit(config)

        print("✅ 工具包创建成功")

        # 3. 创建LLM实例
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        print("✅ LLM实例创建成功")

        # 4. 创建社交媒体分析师节点
        analyst_node = create_social_media_analyst(llm, toolkit)

        print("✅ 社交媒体分析师节点创建成功")

        # 5. 准备测试状态
        test_state = {
            "trade_date": "2025-10-20",
            "company_of_interest": "AAPL",
            "messages": []
        }

        print(f"\n📊 测试参数:")
        print(f"  - 股票代码: {test_state['company_of_interest']}")
        print(f"  - 分析日期: {test_state['trade_date']}")

        # 6. 执行分析
        print(f"\n🔄 开始执行社交媒体情绪分析...")

        result = analyst_node(test_state)

        # 7. 检查结果
        print(f"\n✅ 分析完成!")
        print(f"📊 结果检查:")
        print(f"  - sentiment_report存在: {('sentiment_report' in result)}")

        if 'sentiment_report' in result:
            report_length = len(result['sentiment_report'])
            print(f"  - 报告长度: {report_length} 字符")

            if report_length > 300:
                print(f"  - 状态: ✅ 报告长度正常 (>300字符)")
                print(f"\n📋 报告预览 (前500字符):")
                print("-" * 80)
                print(result['sentiment_report'][:500])
                print("-" * 80)
                return True
            elif report_length > 0:
                print(f"  - 状态: ⚠️ 报告较短 (<300字符)")
                print(f"\n📋 完整报告:")
                print("-" * 80)
                print(result['sentiment_report'])
                print("-" * 80)
                return False
            else:
                print(f"  - 状态: ❌ 报告为空")
                return False
        else:
            print(f"  - 状态: ❌ 缺少sentiment_report字段")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sentiment_analyst()

    print("\n" + "=" * 80)
    if success:
        print("🎉 测试通过！社交媒体分析师修复成功!")
    else:
        print("⚠️ 测试未完全通过，请检查日志")
    print("=" * 80)

    sys.exit(0 if success else 1)
