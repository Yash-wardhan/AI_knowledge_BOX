
import re

from guardrails.guardrail_service import (
    BLOCKED_RESPONSE,
    check_input_guardrail,
    generate_guardrailed_answer,
)
from services.llm_service import generate_answer
from services.retrieval_service import search_similar_chunks

GUARDRAIL_BLOCKED_PREFIX = "I'm sorry"

CITATION_LABEL = re.compile(r"\s*\[S\d+\]")


def prepare_history(history: list[dict] | None) -> list[dict]:
    """
    Make stored turns safe to replay to the LLM:
    - keep only user/assistant roles
    - strip old [S1]-style labels — they pointed at a *previous* retrieval and
      would be confused with the current turn's sources.
    """
    cleaned = []
    for msg in history or []:
        if msg.get("role") not in ("user", "assistant"):
            continue
        content = CITATION_LABEL.sub("", msg.get("content") or "").strip()
        if content:
            cleaned.append({"role": msg["role"], "content": content})
    return cleaned


def build_retrieval_query(question: str, history: list[dict]) -> str:
    """
    Follow-ups like "tell me more about it" embed poorly on their own.
    Prepend the previous user question so retrieval keeps the topic —
    no extra LLM call needed.
    """
    previous = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"),
        None,
    )
    return f"{previous}\n{question}" if previous else question


async def answer_question(
    db,
    question: str,
    top_k: int = 5,
    use_guardrails: bool = True,
    history: list[dict] | None = None,
):
    history = prepare_history(history)

    # 1. INPUT GUARDRAIL — check question before hitting the DB
    if use_guardrails:
        is_safe = await check_input_guardrail(question)

        if not is_safe:
            return {
                "question": question,
                "answer": BLOCKED_RESPONSE,
                "citations": [],
            }

    # 2. Retrieve relevant chunks
    results = await search_similar_chunks(
        db=db,
        question=build_retrieval_query(question, history),
        top_k=top_k,
    )

    if not results:
        return {
            "question": question,
            "answer": "I couldn't find relevant information in your saved notes.",
            "citations": [],
        }

    context_parts = []
    citation_map = {}

    for index, result in enumerate(results, start=1):
        source_label = f"S{index}"

        citation_map[source_label] = result

        context_parts.append(
            f"""
[{source_label}]
Title: {result['title']}
Content: {result['content']}
"""
        )

    context = "\n".join(context_parts)

    # 3. Generate answer (with or without guardrails)
    if use_guardrails:
        answer = await generate_guardrailed_answer(
            question=question,
            context=context,
            history=history,
        )

        # NeMo blocks the message by returning a canned refusal
        if answer.startswith(GUARDRAIL_BLOCKED_PREFIX):
            return {
                "question": question,
                "answer": answer,
                "citations": [],
            }
    else:
        answer = await generate_answer(
            question=question,
            context=context,
            history=history,
        )

    # 4. Validate citation labels
    cited_labels = set(
        re.findall(r"\[(S\d+)\]", answer)
    )

    valid_citations = [
        {
            "source_label": label,
            "chunk_id": citation_map[label]["chunk_id"],
            "item_id": citation_map[label]["item_id"],
            "title": citation_map[label]["title"],
            "source_url": citation_map[label]["source_url"],
            "content": citation_map[label]["content"],
        }
        for label in sorted(cited_labels)
        if label in citation_map
    ]

    # 5. Remove invalid citation labels
    valid_labels = set(citation_map.keys())

    answer = re.sub(
        r"\[(S\d+)\]",
        lambda match: (
            match.group(0)
            if match.group(1) in valid_labels
            else ""
        ),
        answer,
    )

    return {
        "question": question,
        "answer": answer.strip(),
        "citations": valid_citations,
    }