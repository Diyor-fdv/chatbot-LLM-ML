from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


_agent = None


def llm_chat(messages: list[LLMMessage], *, temperature: float = 0.2) -> str | None:
    """
    Agno-only LLM entrypoint. Returns None if LLM is disabled/unavailable.
    """
    if not settings.llm_enabled:
        return None
    if not settings.openai_api_key:
        logger.warning("LLM_ENABLED=true but OPENAI_API_KEY is missing; LLM disabled.")
        return None

    try:
        global _agent
        if _agent is None:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat

            model = OpenAIChat(id=settings.openai_model, base_url=settings.openai_base_url, temperature=temperature)
            _agent = Agent(model=model, markdown=False)

        prompt = "\n\n".join([f"{m.role.upper()}:\n{m.content}" for m in messages])
        out = _agent.run(prompt)
        return getattr(out, "content", str(out))
    except Exception as e:  # noqa: BLE001
        logger.warning("Agno LLM call failed. err=%s", e)
        return None

