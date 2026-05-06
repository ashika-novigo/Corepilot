from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterable, Literal, TypedDict


Role = Literal["user", "assistant", "system"]


class ChatTurn(TypedDict):
    role: Role
    content: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_history(turns: Iterable[dict[str, Any]] | None) -> list[ChatTurn]:
    """Keep only prompt-safe chat turns in the standard role/content format."""
    normalized: list[ChatTurn] = []

    for turn in turns or []:
        role = turn.get("role")
        content = turn.get("content")

        if role not in ("user", "assistant", "system"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue

        normalized.append({"role": role, "content": content.strip()})

    return normalized


@dataclass
class AgentSessionState:
    user_id: str
    history: list[ChatTurn] = field(default_factory=list)
    active_agent: str | None = None
    last_agent: str | None = None
    pending: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    max_history: int = 40

    def touch(self) -> None:
        self.updated_at = _now()

    def append_turn(self, role: Role, content: str) -> None:
        if not content or not content.strip():
            return

        self.history.append({"role": role, "content": content.strip()})
        self.trim_history()
        self.touch()

    def record_exchange(self, user_message: str, assistant_reply: str) -> None:
        self.append_turn("user", user_message)
        self.append_turn("assistant", assistant_reply)

    def prompt_history(self, current_message: str | None = None, limit: int = 10) -> list[ChatTurn]:
        turns = normalize_history(self.history)

        if current_message and current_message.strip():
            turns.append({"role": "user", "content": current_message.strip()})

        return turns[-limit:]

    def history_text(self, current_message: str | None = None, limit: int = 10) -> str:
        turns = self.prompt_history(current_message=current_message, limit=limit)

        if not turns:
            return "(no prior turns)"

        return "\n".join(
            f"{turn['role'].capitalize()}: {turn['content']}"
            for turn in turns
        )

    def set_agent(self, agent: str | None) -> None:
        self.active_agent = agent
        if agent:
            self.last_agent = agent
        self.touch()

    def set_pending(self, key: str, value: dict[str, Any]) -> None:
        self.pending[key] = value
        self.touch()

    def get_pending(self, key: str) -> dict[str, Any] | None:
        return self.pending.get(key)

    def clear_pending(self, key: str) -> None:
        self.pending.pop(key, None)
        self.touch()

    def trim_history(self) -> None:
        if len(self.history) > self.max_history:
            self.history[:] = self.history[-self.max_history:]


class InMemoryAgentStateStore:
    """Per-user agent state store. Swap this class for Redis/DB persistence later."""

    def __init__(self, max_history: int = 40):
        self.max_history = max_history
        self._states: dict[str, AgentSessionState] = {}
        self._lock = RLock()

    def get(self, user_id: str) -> AgentSessionState:
        with self._lock:
            state = self._states.get(user_id)
            if state is None:
                state = AgentSessionState(user_id=user_id, max_history=self.max_history)
                self._states[user_id] = state
            return state

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._states.pop(user_id, None)


agent_state_store = InMemoryAgentStateStore()
