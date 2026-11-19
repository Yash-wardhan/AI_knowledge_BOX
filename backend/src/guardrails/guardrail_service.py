import asyncio
import logging
from pathlib import Path

import openai
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.exceptions import LLMCallException

from backend.core.config import settings
from services.llm_service import generate_answer

CONFIG_PATH = Path(__file__).parent / "config"

# Read the static config files
_config_yml = (CONFIG_PATH / "config.yml").read_text()
_prompts_yml = (CONFIG_PATH / "prompts.yml").read_text()
_rails_co = (CONFIG_PATH / "rails.co").read_text()

# Inject real LM Studio values — NeMo does NOT resolve ${VAR} in parameters
_config_yml = (
    _config_yml
    .replace('"PLACEHOLDER"', f'"{settings.LLM_BASE_URL}"', 1)   # main base_url
    .replace('"PLACEHOLDER"', f'"{settings.LLM_API_KEY}"', 1)     # main api_key
    .replace('"PLACEHOLDER"', f'"{settings.LLM_MODEL}"', 1)       # main model_name
    .replace('"PLACEHOLDER"', f'"{settings.LLM_BASE_URL}"', 1)    # self_check base_url
    .replace('"PLACEHOLDER"', f'"{settings.LLM_API_KEY}"', 1)     # self_check api_key
    .replace('"PLACEHOLDER"', f'"{settings.LLM_MODEL}"', 1)       # self_check model_name
)

config = RailsConfig.from_content(
    yaml_content=_config_yml + "\n" + _prompts_yml,
    colang_content=_rails_co,
)

rails = LLMRails(config)

BLOCKED_RESPONSE = (
    "I'm sorry, I can't help with that. "
    "Please ask a question about your saved notes or URLs."
)

logger = logging.getLogger(__name__)

# Upstream statuses worth retrying (rate limited / temporarily overloaded)
RETRYABLE_STATUSES = {429, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.5

# NeMo is used ONLY for the rails, never for generation: NeMo's Colang 1.0
# generation drops `system` messages, so the retrieved context, citation rules
# and chat history never reached the LLM. Generation goes through
# llm_service.generate_answer instead. Per question:
#   input rail   → 1 call
#   generation   → 1 call (our own prompt: context + history + [S1] citations)
#   output rail  → 1 call
INPUT_ONLY = {"rails": ["input"]}
OUTPUT_ONLY = {"rails": ["output"]}


class LLMRateLimitedError(Exception):
    """The upstream LLM is rate limiting or overloaded, even after retries."""


async def _generate(messages: list[dict], options: dict) -> str:
    """Call NeMo with retry + exponential backoff on 429/5xx from the LLM provider."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await rails.generate_async(messages=messages, options=options)
            return _content(response)
        except LLMCallException as exc:
            if exc.status not in RETRYABLE_STATUSES:
                raise
            if attempt == MAX_ATTEMPTS:
                raise LLMRateLimitedError(str(exc)) from exc
            delay = BACKOFF_SECONDS * 2 ** (attempt - 1)
            logger.warning(
                "LLM returned %s (attempt %d/%d), retrying in %.1fs",
                exc.status, attempt, MAX_ATTEMPTS, delay,
            )
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")


def _content(response) -> str:
    """Extract the assistant text from a NeMo response (dict or GenerationResponse)."""
    if isinstance(response, dict):
        return (response.get("content") or "").strip()
    messages = getattr(response, "response", None)
    if isinstance(messages, list) and messages:
        return (messages[-1].get("content") or "").strip()
    if isinstance(messages, str):
        return messages.strip()
    return ""


async def check_input_guardrail(question: str) -> bool:
    """
    Run ONLY the input rail against the raw user question.
    Call this BEFORE retrieval to avoid unnecessary DB hits.

    Returns:
        True  — question is safe, proceed with RAG
        False — question is blocked, return early
    """
    answer = await _generate(
        messages=[
            {
                "role": "user",
                "content": question,
            },
        ],
        options=INPUT_ONLY,
    )

    # NeMo returns the canned refusal when the input rail fires
    return answer != BLOCKED_RESPONSE


async def check_output_guardrail(question: str, answer: str) -> str:
    """
    Run ONLY the output rail on an already-generated answer.

    Returns the answer as passed through the rail, or BLOCKED_RESPONSE.
    """
    content = await _generate(
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        options=OUTPUT_ONLY,
    )

    # NeMo returns the canned refusal when the output rail fires
    if not content or content == BLOCKED_RESPONSE:
        return BLOCKED_RESPONSE
    return content


async def generate_guardrailed_answer(
    question: str,
    context: str,
    history: list[dict] | None = None,
) -> str:
    """
    Generate a grounded, cited answer and pass it through the output rail.
    The input rail is NOT re-run here — call check_input_guardrail() first.

    `history` is a list of prior {"role", "content"} turns (oldest first).

    Returns BLOCKED_RESPONSE if the output rail fires.
    """
    try:
        draft = await generate_answer(
            question=question,
            context=context,
            history=history,
        )
    except openai.RateLimitError as exc:
        raise LLMRateLimitedError(str(exc)) from exc
    except openai.APIStatusError as exc:
        if exc.status_code in RETRYABLE_STATUSES:
            raise LLMRateLimitedError(str(exc)) from exc
        raise

    return await check_output_guardrail(question, draft)
