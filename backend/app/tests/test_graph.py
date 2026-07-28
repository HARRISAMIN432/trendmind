from __future__ import annotations
import logging
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
from app.graph.pipeline_graph import _has_articles, build_pipeline_graph, run_pipeline
from app.graph.state import PipelineState

STAGE_TO_NODE_NAME = {
    "collect": "collector_node",
    "clean": "cleaner_node",
    "classify": "classification_node",
    "summarize": "summarization_node",
    "embed": "embedding_node",
    "dedup": "duplicate_node",
}


def _make_node(stage: str, articles_out: list, call_log: list):
    def _node(state: dict) -> dict:
        call_log.append({"stage": stage, "input_count": len(state.get("articles", []))})
        state["articles"] = articles_out
        return state

    return _node


@contextmanager
def patched_nodes(call_log: list, **per_stage_articles):
    defaults = {
        "collect": ["article-1"],
        "clean": ["article-1"],
        "classify": ["article-1"],
        "summarize": ["article-1"],
        "embed": ["article-1"],
        "dedup": ["article-1"],
    }
    defaults.update(per_stage_articles)

    with ExitStack() as stack:
        for stage, articles in defaults.items():
            stack.enter_context(
                patch(
                    f"app.graph.pipeline_graph.{STAGE_TO_NODE_NAME[stage]}",
                    side_effect=_make_node(stage, articles, call_log),
                )
            )
        yield


@contextmanager
def patched_singleton_graph(call_log: list, **per_stage_articles):
    with patched_nodes(call_log, **per_stage_articles):
        fresh_graph = build_pipeline_graph()
        with patch("app.graph.pipeline_graph.pipeline_graph", fresh_graph):
            yield

class TestHasArticles:
    def test_continue_when_articles_present(self):
        state: PipelineState = {"articles": ["a"]}
        assert _has_articles(state) == "continue"

    def test_stop_when_articles_empty_list(self):
        state: PipelineState = {"articles": []}
        assert _has_articles(state) == "stop"

    def test_stop_when_articles_key_missing(self):
        state: PipelineState = {}
        assert _has_articles(state) == "stop"

class TestFullPipelineHappyPath:
    def test_all_six_stages_run_in_order(self):
        call_log: list = []
        with patched_nodes(call_log):
            graph = build_pipeline_graph()
            graph.invoke({})

        assert [c["stage"] for c in call_log] == [
            "collect",
            "clean",
            "classify",
            "summarize",
            "embed",
            "dedup",
        ]

    def test_final_articles_come_from_last_stage(self):
        call_log: list = []
        with patched_nodes(call_log, dedup=["final-article"]):
            graph = build_pipeline_graph()
            final_state = graph.invoke({})

        assert final_state["articles"] == ["final-article"]

    def test_articles_flow_from_one_stage_into_the_next(self):
        call_log: list = []
        with patched_nodes(call_log, collect=["a", "b", "c"]):
            graph = build_pipeline_graph()
            graph.invoke({})

        by_stage = {c["stage"]: c["input_count"] for c in call_log}
        assert by_stage["collect"] == 0  # nothing in state yet when collect runs
        assert by_stage["clean"] == 3  # saw collect's 3 articles

class TestShortCircuiting:
    def test_stops_after_collect_if_no_articles_collected(self):
        call_log: list = []
        with patched_nodes(call_log, collect=[]):
            graph = build_pipeline_graph()
            final_state = graph.invoke({})

        assert [c["stage"] for c in call_log] == ["collect"]
        assert final_state["articles"] == []

    def test_stops_after_clean_if_all_articles_dropped(self):
        call_log: list = []
        with patched_nodes(call_log, clean=[]):
            graph = build_pipeline_graph()
            graph.invoke({})

        assert [c["stage"] for c in call_log] == ["collect", "clean"]

    def test_stops_after_classify_if_all_articles_dropped(self):
        call_log: list = []
        with patched_nodes(call_log, classify=[]):
            graph = build_pipeline_graph()
            graph.invoke({})

        assert [c["stage"] for c in call_log] == ["collect", "clean", "classify"]

    def test_stops_after_summarize_if_all_articles_dropped(self):
        call_log: list = []
        with patched_nodes(call_log, summarize=[]):
            graph = build_pipeline_graph()
            graph.invoke({})

        assert [c["stage"] for c in call_log] == [
            "collect",
            "clean",
            "classify",
            "summarize",
        ]

    def test_stops_after_embed_if_all_articles_dropped(self):
        call_log: list = []
        with patched_nodes(call_log, embed=[]):
            graph = build_pipeline_graph()
            graph.invoke({})

        stages = [c["stage"] for c in call_log]
        assert stages == ["collect", "clean", "classify", "summarize", "embed"]
        # dedup must never be called once embed's batch is empty.
        assert "dedup" not in stages

    def test_dedup_runs_unconditionally_once_embed_has_output(self):
        call_log: list = []
        with patched_nodes(call_log, dedup=[]):
            graph = build_pipeline_graph()
            final_state = graph.invoke({})

        assert call_log[-1]["stage"] == "dedup"
        assert final_state["articles"] == []

class TestRunPipeline:
    def test_passes_existing_urls_into_initial_state(self):
        seen_state = {}

        def _capture_collect(state: dict) -> dict:
            seen_state.update(state)
            state["articles"] = []  # short-circuit immediately, keep test simple
            return state

        with patch("app.graph.pipeline_graph.collector_node", side_effect=_capture_collect):
            fresh_graph = build_pipeline_graph()
            with patch("app.graph.pipeline_graph.pipeline_graph", fresh_graph):
                run_pipeline(existing_urls={"http://example.com/a"})

        assert seen_state.get("existing_urls") == {"http://example.com/a"}

    def test_passes_existing_embedded_articles_into_initial_state(self):
        seen_state = {}

        def _capture_collect(state: dict) -> dict:
            seen_state.update(state)
            state["articles"] = []
            return state

        fake_existing = ["fake-embedded-article"]
        with patch("app.graph.pipeline_graph.collector_node", side_effect=_capture_collect):
            fresh_graph = build_pipeline_graph()
            with patch("app.graph.pipeline_graph.pipeline_graph", fresh_graph):
                run_pipeline(existing_embedded_articles=fake_existing)

        assert seen_state.get("existing_embedded_articles") == fake_existing

    def test_omitted_optional_args_are_not_placed_in_initial_state(self):
        seen_state = {}

        def _capture_collect(state: dict) -> dict:
            seen_state.update(state)
            state["articles"] = []
            return state

        with patch("app.graph.pipeline_graph.collector_node", side_effect=_capture_collect):
            fresh_graph = build_pipeline_graph()
            with patch("app.graph.pipeline_graph.pipeline_graph", fresh_graph):
                run_pipeline()

        assert "existing_urls" not in seen_state
        assert "existing_embedded_articles" not in seen_state

    def test_returns_the_final_state_from_the_graph(self):
        call_log: list = []
        with patched_singleton_graph(call_log, dedup=["result-article"]):
            final_state = run_pipeline()

        assert final_state["articles"] == ["result-article"]

    def test_logs_a_summary_line(self, caplog):
        call_log: list = []
        with patched_singleton_graph(call_log, dedup=["result-article"]):
            with caplog.at_level(logging.INFO, logger="app.graph.pipeline_graph"):
                run_pipeline()

        assert any("Pipeline run complete" in record.message for record in caplog.records)

class TestErrorListsSurviveInFinalState:
    def test_collector_errors_present_in_final_state(self):
        call_log: list = []

        def _collect_with_errors(state: dict) -> dict:
            call_log.append({"stage": "collect"})
            state["articles"] = ["a"]
            state["collector_errors"] = [{"source_name": "Feed X", "error": "timeout"}]
            return state

        with patch("app.graph.pipeline_graph.collector_node", side_effect=_collect_with_errors), \
             patch(
                 "app.graph.pipeline_graph.cleaner_node",
                 side_effect=_make_node("clean", ["a"], call_log),
             ), \
             patch(
                 "app.graph.pipeline_graph.classification_node",
                 side_effect=_make_node("classify", ["a"], call_log),
             ), \
             patch(
                 "app.graph.pipeline_graph.summarization_node",
                 side_effect=_make_node("summarize", ["a"], call_log),
             ), \
             patch(
                 "app.graph.pipeline_graph.embedding_node",
                 side_effect=_make_node("embed", ["a"], call_log),
             ), \
             patch(
                 "app.graph.pipeline_graph.duplicate_node",
                 side_effect=_make_node("dedup", ["a"], call_log),
             ):
            graph = build_pipeline_graph()
            final_state = graph.invoke({})

        assert final_state["collector_errors"] == [
            {"source_name": "Feed X", "error": "timeout"}
        ]
        assert [c["stage"] for c in call_log] == [
            "collect",
            "clean",
            "classify",
            "summarize",
            "embed",
            "dedup",
        ]

    def test_duplicate_count_present_in_final_state(self):
        call_log: list = []

        def _dedup_with_count(state: dict) -> dict:
            call_log.append({"stage": "dedup"})
            state["articles"] = ["a", "b"]
            state["duplicate_count"] = 1
            return state

        with patched_nodes(call_log, dedup=["a", "b"]), \
             patch("app.graph.pipeline_graph.duplicate_node", side_effect=_dedup_with_count):
            graph = build_pipeline_graph()
            final_state = graph.invoke({})

        assert final_state["duplicate_count"] == 1

class TestPipelineStateShape:
    def test_pipeline_state_is_a_plain_dict_at_runtime(self):
        state: PipelineState = {"articles": [], "duplicate_count": 0}
        assert isinstance(state, dict)
        assert state["duplicate_count"] == 0

    def test_pipeline_state_allows_missing_optional_keys(self):
        state: PipelineState = {}
        assert state.get("articles") is None