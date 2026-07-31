from __future__ import annotations
import logging
from langgraph.graph import END, START, StateGraph
from app.agents.classification_agent import classification_node
from app.agents.cleaner_agent import cleaner_node
from app.agents.collector_agent import collector_node
from app.agents.duplicate_agent import duplicate_node
from app.agents.embedding_agent import embedding_node
from app.agents.summarization_agent import summarization_node
from app.graph.state import PipelineState

logger = logging.getLogger(__name__)


def _has_articles(state: PipelineState) -> str:
    return "continue" if state.get("articles") else "stop"


def build_pipeline_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("collect", collector_node)
    graph.add_node("clean", cleaner_node)
    graph.add_node("classify", classification_node)
    graph.add_node("summarize", summarization_node)
    graph.add_node("embed", embedding_node)
    graph.add_node("dedup", duplicate_node)

    graph.add_edge(START, "collect")

    graph.add_conditional_edges(
        "collect", _has_articles, {"continue": "clean", "stop": END}
    )
    graph.add_conditional_edges(
        "clean", _has_articles, {"continue": "classify", "stop": END}
    )
    graph.add_conditional_edges(
        "classify", _has_articles, {"continue": "summarize", "stop": END}
    )
    graph.add_conditional_edges(
        "summarize", _has_articles, {"continue": "embed", "stop": END}
    )
    graph.add_conditional_edges(
        "embed", _has_articles, {"continue": "dedup", "stop": END}
    )
    graph.add_edge("dedup", END)

    return graph.compile()

pipeline_graph = build_pipeline_graph()


def run_pipeline(
    existing_urls: set[str] | None = None,
    existing_embedded_articles: list | None = None,
) -> PipelineState:
    initial_state: PipelineState = {}
    if existing_urls is not None:
        initial_state["existing_urls"] = existing_urls
    if existing_embedded_articles is not None:
        initial_state["existing_embedded_articles"] = existing_embedded_articles

    final_state: PipelineState = pipeline_graph.invoke(initial_state)

    logger.info(
        "Pipeline run complete: %d articles out, errors: collector=%d cleaner=%d "
        "classification=%d summarization=%d embedding=%d, duplicates=%d",
        len(final_state.get("articles", [])),
        len(final_state.get("collector_errors", [])),
        len(final_state.get("cleaner_errors", [])),
        len(final_state.get("classification_errors", [])),
        len(final_state.get("summarization_errors", [])),
        len(final_state.get("embedding_errors", [])),
        final_state.get("duplicate_count", 0),
    )
    return final_state