from __future__ import annotations

import uuid

from copilot.models import ConversationTurn


class ConversationMemory:
    def __init__(self, window_size: int = 10, expiration_minutes: int = 60) -> None:
        self._window_size = window_size
        self._expiration_seconds = expiration_minutes * 60
        self._conversations: dict[str, list[ConversationTurn]] = {}

    def create_conversation(self) -> str:
        conv_id = str(uuid.uuid4())[:8]
        self._conversations[conv_id] = []
        return conv_id

    def add_turn(self, conversation_id: str, turn: ConversationTurn) -> None:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append(turn)
        self._trim(conversation_id)

    def get_history(self, conversation_id: str) -> list[ConversationTurn]:
        return self._conversations.get(conversation_id, [])

    def get_recent_context(self, conversation_id: str, turns: int = 5) -> str:
        history = self.get_history(conversation_id)
        recent = history[-turns:] if len(history) > turns else history
        if not recent:
            return ""
        lines = ["Previous conversation context:"]
        for turn in recent:
            lines.append(f"  User: {turn.query}")
            lines.append(f"  Copilot: {turn.response[:200]}")
        return "\n".join(lines)

    def list_conversations(self) -> dict[str, int]:
        return {cid: len(turns) for cid, turns in self._conversations.items()}

    def clear_conversation(self, conversation_id: str) -> None:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]

    def _trim(self, conversation_id: str) -> None:
        history = self._conversations.get(conversation_id, [])
        if len(history) > self._window_size:
            self._conversations[conversation_id] = history[-self._window_size :]
