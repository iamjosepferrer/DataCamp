"""Researcher -> writer -> reviewer pipeline with a conditional retry edge.

Companion script for the DataCamp graph engineering tutorial.
Verified against langgraph 1.2.11 and langchain-anthropic 1.7.1.

Run it with:  python brief_graph.py
Optional:     pip install grandalf   (for the ASCII graph rendering)
"""

from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

load_dotenv()

MAX_REVISIONS = 3

# A cheap model for gathering, a stronger one for writing and reviewing.
fast_llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=2000)
main_llm = ChatAnthropic(model="claude-sonnet-5", max_tokens=2000)


class BriefState(TypedDict):
    topic: str
    notes: str
    draft: str
    verdict: str
    feedback: str
    revisions: int


def researcher(state: BriefState) -> dict:
    """Gather raw material and write it into shared state as notes."""
    prompt = (
        f"Topic: {state['topic']}\n\n"
        "List 6 to 8 concrete facts, numbers, or named examples a writer "
        "could use. Bullet points only. No introduction, no conclusion."
    )
    response = fast_llm.invoke(prompt)
    return {"notes": response.text}


def writer(state: BriefState) -> dict:
    """Turn notes into a draft, applying reviewer feedback on a retry."""
    feedback = state.get("feedback", "")
    revision_note = (
        f"\n\nThe reviewer rejected your last draft. Fix this: {feedback}"
        if feedback
        else ""
    )
    prompt = (
        f"Write a 200-word brief on: {state['topic']}\n\n"
        f"Use only these notes:\n{state['notes']}{revision_note}"
    )
    response = main_llm.invoke(prompt)
    return {
        "draft": response.text,
        "revisions": state.get("revisions", 0) + 1,
    }


def reviewer(state: BriefState) -> dict:
    """Score the draft. This node never writes, so it can be honest."""
    prompt = (
        "You are a skeptical editor. Reject the draft if it makes a claim "
        "the notes do not support, or if it runs past 250 words.\n\n"
        f"NOTES:\n{state['notes']}\n\nDRAFT:\n{state['draft']}\n\n"
        "Reply with APPROVE or REVISE on the first line. "
        "If REVISE, add one line explaining the single biggest problem."
    )
    response = main_llm.invoke(prompt)
    text = response.text.strip()
    verdict = "approve" if text.upper().startswith("APPROVE") else "revise"
    return {"verdict": verdict, "feedback": text}


def route_after_review(state: BriefState) -> Literal["writer", "__end__"]:
    """The conditional edge: ship it, or send it back to the writer.

    Keep this function silent. A print() here lands on stdout while the
    stream loop is still printing the previous chunk, so the cap notice
    shows up one step early and the trace looks out of order.
    """
    if state["verdict"] == "approve":
        return END
    if state["revisions"] >= MAX_REVISIONS:
        return END
    return "writer"


builder = StateGraph(BriefState)

builder.add_node("researcher", researcher)
builder.add_node("writer", writer)
builder.add_node("reviewer", reviewer)

builder.add_edge(START, "researcher")
builder.add_edge("researcher", "writer")
builder.add_edge("writer", "reviewer")
builder.add_conditional_edges(
    "reviewer",
    route_after_review,
    {"writer": "writer", END: END},
)

graph = builder.compile()


def print_graph_shape() -> None:
    """Render the compiled graph itself, before anything runs."""
    print("=== GRAPH SHAPE ===")
    try:
        print(graph.get_graph().draw_ascii())
    except ImportError:
        print("(ASCII rendering needs: pip install grandalf)")
    print("=== MERMAID SOURCE ===")
    print(graph.get_graph().draw_mermaid())


def run(topic: str) -> dict:
    """Run the graph once, printing what each node writes as it goes."""
    print("=== RUN TRACE ===")
    final = None
    # Ask for both streams in one pass. Streaming and then invoking
    # would run the whole graph twice and double the model calls.
    for mode, chunk in graph.stream(
        {"topic": topic, "revisions": 0},
        stream_mode=["updates", "values"],
    ):
        if mode == "updates":
            for node, update in chunk.items():
                print(f"[{node}] wrote: {list(update.keys())}")
        else:
            final = chunk
    return final


if __name__ == "__main__":
    print_graph_shape()

    topic = "Why Postgres beat MongoDB for most startups"
    final = run(topic)

    print(f"\nRevisions: {final['revisions']}")
    print(f"Verdict: {final['verdict']}")
    if final["verdict"] != "approve":
        print(f"Hit the {MAX_REVISIONS}-revision cap. Shipped as is.")
    print()
    print(final["draft"])