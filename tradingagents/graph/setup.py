# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from .conditional_logic import ConditionalLogic

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        config: Dict[str, Any] = None,
        react_llm = None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.config = config or {}
        self.react_llm = react_llm

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            # 现在所有LLM都使用标准市场分析师（包括阿里百炼的OpenAI兼容适配器）
            llm_provider = self.config.get("llm_provider", "").lower()

            # 检查是否使用OpenAI兼容的阿里百炼适配器
            using_dashscope_openai = (
                "dashscope" in llm_provider and
                hasattr(self.quick_thinking_llm, '__class__') and
                'OpenAI' in self.quick_thinking_llm.__class__.__name__
            )

            if using_dashscope_openai:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼OpenAI兼容模式）")
            elif "dashscope" in llm_provider or "阿里百炼" in self.config.get("llm_provider", ""):
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼原生模式）")
            elif "deepseek" in llm_provider:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（DeepSeek）")
            else:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师")

            # 所有LLM都使用标准分析师
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            # 现在所有LLM都使用标准基本面分析师（包括阿里百炼的OpenAI兼容适配器）
            llm_provider = self.config.get("llm_provider", "").lower()

            # 检查是否使用OpenAI兼容的阿里百炼适配器
            using_dashscope_openai = (
                "dashscope" in llm_provider and
                hasattr(self.quick_thinking_llm, '__class__') and
                'OpenAI' in self.quick_thinking_llm.__class__.__name__
            )

            if using_dashscope_openai:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（阿里百炼OpenAI兼容模式）")
            elif "dashscope" in llm_provider or "阿里百炼" in self.config.get("llm_provider", ""):
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（阿里百炼原生模式）")
            elif "deepseek" in llm_provider:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（DeepSeek）")
            else:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师")

            # 所有LLM都使用标准分析师（包含强制工具调用机制）
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        risky_analyst = create_risky_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Define edges
        # 🚀 并发优化：所有分析师从START同时启动
        logger.info(f"🚀 [并发优化] 启用并发执行模式，{len(selected_analysts)}个分析师将并行执行")

        # 1. START节点并发连接到所有分析师
        for analyst_type in selected_analysts:
            analyst_name = f"{analyst_type.capitalize()} Analyst"
            workflow.add_edge(START, analyst_name)
            logger.debug(f"🔗 [并发优化] START -> {analyst_name}")

        # 2. 为每个分析师配置工具调用和消息清理
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)
            logger.debug(f"🔧 [并发优化] {current_analyst} 工具链配置完成")

        # 3. 创建同步节点，等待所有分析师完成
        def sync_analysts(state):
            """同步节点：等待所有分析师完成后继续"""
            logger.info(f"✅ [并发优化] 所有分析师已完成，准备进入研究员辩论阶段")
            logger.debug(f"📊 [并发优化] 已收集报告: market={len(state.get('market_report', ''))}, "
                        f"sentiment={len(state.get('sentiment_report', ''))}, "
                        f"news={len(state.get('news_report', ''))}, "
                        f"fundamentals={len(state.get('fundamentals_report', ''))}")
            return state

        workflow.add_node("Sync_Analysts", sync_analysts)

        # 4. 所有分析师的清理节点连接到同步点
        for analyst_type in selected_analysts:
            current_clear = f"Msg Clear {analyst_type.capitalize()}"
            workflow.add_edge(current_clear, "Sync_Analysts")
            logger.debug(f"🔗 [并发优化] {current_clear} -> Sync_Analysts")

        # 5. 同步点连接到Bull Researcher
        workflow.add_edge("Sync_Analysts", "Bull Researcher")
        logger.info(f"✅ [并发优化] 分析师并发配置完成")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
