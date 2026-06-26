"""Unit tests for conversation memory."""

from copilot.memory.conversation_memory import ConversationMemory
from copilot.models import ConversationTurn, IntentType, Plan


def _make_turn(query: str, response: str) -> ConversationTurn:
    return ConversationTurn(query=query, intent=IntentType.GREETING, plan=Plan(intent=IntentType.GREETING, steps=[]), results=[], response=response)


class TestConversationMemory:
    def setup_method(self):
        self.memory = ConversationMemory(window_size=5, expiration_minutes=60)

    def test_create_conversation(self):
        cid = self.memory.create_conversation()
        assert isinstance(cid, str)
        assert len(cid) == 8

    def test_add_turn(self):
        cid = self.memory.create_conversation()
        turn = _make_turn("hello", "hi")
        self.memory.add_turn(cid, turn)
        history = self.memory.get_history(cid)
        assert len(history) == 1

    def test_get_history_empty(self):
        history = self.memory.get_history("nonexistent")
        assert history == []

    def test_get_recent_context(self):
        cid = self.memory.create_conversation()
        for i in range(3):
            self.memory.add_turn(cid, _make_turn(f"q{i}", f"r{i}"))
        ctx = self.memory.get_recent_context(cid, turns=2)
        assert "q2" in ctx
        assert "q0" not in ctx

    def test_get_recent_context_empty(self):
        cid = self.memory.create_conversation()
        ctx = self.memory.get_recent_context(cid)
        assert ctx == ""

    def test_window_size_enforced(self):
        self.memory = ConversationMemory(window_size=2, expiration_minutes=60)
        cid = self.memory.create_conversation()
        for i in range(5):
            self.memory.add_turn(cid, _make_turn(f"q{i}", f"r{i}"))
        history = self.memory.get_history(cid)
        assert len(history) == 2

    def test_list_conversations(self):
        cid1 = self.memory.create_conversation()
        cid2 = self.memory.create_conversation()
        self.memory.add_turn(cid1, _make_turn("q", "r"))
        convs = self.memory.list_conversations()
        assert len(convs) == 2
        assert convs[cid1] == 1
        assert convs[cid2] == 0

    def test_clear_conversation(self):
        cid = self.memory.create_conversation()
        self.memory.add_turn(cid, _make_turn("q", "r"))
        self.memory.clear_conversation(cid)
        assert cid not in self.memory._conversations
