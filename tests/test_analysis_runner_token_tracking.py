
import os
import sys
import types
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class DummyLogger:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class DummyLoggerManager:
    def log_analysis_start(self, *args, **kwargs):
        pass

    def log_analysis_complete(self, *args, **kwargs):
        pass

    def log_module_error(self, *args, **kwargs):
        pass


class FailingTracker:
    def track_usage(self, **kwargs):
        raise RuntimeError("boom")

    def get_session_cost(self, session_id):
        return 0.0

    def estimate_cost(self, provider, model_name, estimated_input_tokens, estimated_output_tokens):
        return 0.0

class AnalysisRunnerTokenTrackingTest(unittest.TestCase):
    def test_run_stock_analysis_handles_token_tracking_failure(self):
        fake_preparation = SimpleNamespace(
            is_valid=True,
            error_message=None,
            suggestion=None,
            stock_name="Dummy Corp",
            market_type="港股",
            cache_status="hit",
        )

        validator_module = ModuleType("tradingagents.utils.stock_validator")
        validator_module.prepare_stock_data = lambda **kwargs: fake_preparation

        class DummyGraph:
            def __init__(self, analysts, config, debug=False):
                self.analysts = analysts
                self.config = config
                self.debug = debug

            def propagate(self, symbol, date):
                return ({"investment_plan": "plan"}, {"action": "HOLD"})

        graph_module = ModuleType("tradingagents.graph.trading_graph")
        graph_module.TradingAgentsGraph = DummyGraph

        default_config_module = ModuleType("tradingagents.default_config")
        default_config_module.DEFAULT_CONFIG = {
            "data_dir": "./tmp_data",
            "results_dir": "./tmp_results",
            "data_cache_dir": "./tmp_cache",
            "online_tools": False,
            "memory_enabled": False,
        }

        report_module = ModuleType("web.utils.report_exporter")

        def fake_save_analysis_report(**kwargs):
            return True

        def fake_save_modular_reports_to_results_dir(*args, **kwargs):
            return {}

        report_module.save_analysis_report = fake_save_analysis_report
        report_module.save_modular_reports_to_results_dir = fake_save_modular_reports_to_results_dir

        dotenv_module = ModuleType("dotenv")
        dotenv_module.load_dotenv = lambda *args, **kwargs: None

        streamlit_module = ModuleType("streamlit")
        streamlit_module.session_state = {}
        toml_module = ModuleType("toml")
        toml_module.load = lambda *args, **kwargs: {}

        logging_manager_module = ModuleType("tradingagents.utils.logging_manager")
        dummy_logger = DummyLogger()
        logging_manager_module.get_logger = lambda name=None: dummy_logger
        logging_manager_module.get_logger_manager = lambda: DummyLoggerManager()

        logging_init_module = ModuleType("tradingagents.utils.logging_init")
        logging_init_module.setup_web_logging = lambda: dummy_logger

        config_manager_module = ModuleType("tradingagents.config.config_manager")
        config_manager_module.token_tracker = FailingTracker()

        module_overrides = {
            "tradingagents.utils.stock_validator": validator_module,
            "tradingagents.graph.trading_graph": graph_module,
            "tradingagents.default_config": default_config_module,
            "web.utils.report_exporter": report_module,
            "dotenv": dotenv_module,
            "streamlit": streamlit_module,
            "toml": toml_module,
            "tradingagents.utils.logging_manager": logging_manager_module,
            "tradingagents.utils.logging_init": logging_init_module,
            "tradingagents.config.config_manager": config_manager_module,
        }

        env_overrides = {
            "DASHSCOPE_API_KEY": "dummy",
            "FINNHUB_API_KEY": "dummy",
        }

        messages = []

        def progress_cb(message, step=None, total_steps=None):
            messages.append(message)

        with patch.dict(sys.modules, module_overrides, clear=False):
            sys.modules.pop('web.utils.analysis_runner', None)
            from web.utils import analysis_runner  # noqa: WPS433

            with patch('web.utils.analysis_runner.get_logger_manager', return_value=DummyLoggerManager()):
                with patch('web.utils.analysis_runner.st', SimpleNamespace(session_state={})):  # type: ignore[arg-type]
                    with patch('web.utils.analysis_runner.token_tracker', FailingTracker()):
                        with patch('web.utils.analysis_runner.TOKEN_TRACKING_ENABLED', True):
                            with patch.dict(os.environ, env_overrides, clear=False):
                                result = analysis_runner.run_stock_analysis(
                                    stock_symbol="0700.HK",
                                    analysis_date="2025-10-14",
                                    analysts=["Analyst"],
                                    research_depth=3,
                                    llm_provider="dashscope",
                                    llm_model="qwen-plus",
                                    market_type="港股",
                                    progress_callback=progress_cb,
                                )

        self.assertTrue(result["success"])
        self.assertTrue(any("Token成本记录失败" in msg for msg in messages))


if __name__ == '__main__':
    unittest.main()
