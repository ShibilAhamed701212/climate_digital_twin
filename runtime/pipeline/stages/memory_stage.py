"""MemoryStage — load memory, facts, preferences, and session summaries into context.

Runtime-native stage. Domain-agnostic.
No domain-specific concepts, prompts, or datasets.

Reads: existing blackboard keys (query context)
Writes: blackboard keys under "memory.*"
"""

from __future__ import annotations

from runtime.events.definitions import (
    MEMORY_LOADED,
)
from runtime.models.events import Event as RuntimeEvent
from runtime.models.memory import (
    ConversationMemory,
    FactStore,
    MemoryEntry,
    SessionSummary,
    ToolOutputCache,
    UserPreferenceStore,
    WorkingMemory,
)
from runtime.models.pipeline import ExecutionContext, PipelineStage


class MemoryStage(PipelineStage):
    """Load memory, facts, preferences, and session summaries into context.

    Responsibilities:
    - Load conversation history from ConversationMemory
    - Retrieve structured facts from FactStore
    - Load user preferences
    - Load session summaries
    - Expose all as typed MemoryEntry objects on the Blackboard

    This stage runs early in the pipeline so that later stages
    (Retrieval, Planning, Execution, Reasoning) can use the memory context.
    """

    name = "memory"
    description = "Load memory, facts, preferences, and session summaries"

    def __init__(
        self,
        working_memory: WorkingMemory | None = None,
        conversation_memory: ConversationMemory | None = None,
        session_summary: SessionSummary | None = None,
        tool_cache: ToolOutputCache | None = None,
        fact_store: FactStore | None = None,
        preference_store: UserPreferenceStore | None = None,
    ) -> None:
        super().__init__()
        self._working_memory = working_memory or WorkingMemory()
        self._conversation_memory = conversation_memory or ConversationMemory()
        self._session_summary = session_summary or SessionSummary()
        self._tool_cache = tool_cache or ToolOutputCache()
        self._fact_store = fact_store or FactStore()
        self._preference_store = preference_store or UserPreferenceStore()

    @property
    def stores(self) -> dict[str, object]:
        return {
            "working_memory": self._working_memory,
            "conversation": self._conversation_memory,
            "session_summary": self._session_summary,
            "tool_cache": self._tool_cache,
            "fact_store": self._fact_store,
            "preferences": self._preference_store,
        }

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        # Load all memory store contents onto the Blackboard
        memory_state: dict[str, list[MemoryEntry]] = {}

        def _load_entries(store) -> list[MemoryEntry]:
            return [
                versions[-1] for versions in store._entries.values() if not versions[-1].expired()
            ]

        # Working memory — current session state
        working_entries = _load_entries(self._working_memory)
        memory_state["working"] = working_entries

        # Conversation memory — recent turns
        conversation_entries = _load_entries(self._conversation_memory)
        memory_state["conversation"] = conversation_entries

        # Session summary
        summary_entries = _load_entries(self._session_summary)
        memory_state["session_summary"] = summary_entries

        # Tool cache
        cache_entries = _load_entries(self._tool_cache)
        memory_state["tool_cache"] = cache_entries

        # Fact store — structured facts
        fact_entries = _load_entries(self._fact_store)
        memory_state["facts"] = fact_entries

        # User preferences
        pref_entries = _load_entries(self._preference_store)
        memory_state["preferences"] = pref_entries

        ctx.blackboard.publish("memory.state", memory_state, self.name)
        ctx.blackboard.publish("memory.conversation_count", len(conversation_entries), self.name)
        ctx.blackboard.publish("memory.fact_count", len(fact_entries), self.name)

        ctx.add_metric("memory.working_entries", len(working_entries))
        ctx.add_metric("memory.conversation_turns", len(conversation_entries))
        ctx.add_metric("memory.facts", len(fact_entries))
        ctx.add_metric("memory.preferences", len(pref_entries))

        ctx.event_bus.publish(
            RuntimeEvent(
                type=MEMORY_LOADED,
                data={
                    "working": len(working_entries),
                    "conversation_turns": len(conversation_entries),
                    "facts": len(fact_entries),
                    "preferences": len(pref_entries),
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        return ctx

    def store_conversation_turn(
        self, role: str, content: str, metadata: dict | None = None
    ) -> None:
        """Store a conversation turn for future pipeline runs."""
        entry = MemoryEntry(
            key=f"turn:{role}:{hash(content) % 10000}",
            value={"role": role, "content": content},
            agent="memory_stage",
            metadata=metadata or {},
        )
        self._conversation_memory.store(entry)

    def store_fact(self, fact) -> None:
        """Store a structured fact."""
        self._fact_store.store_fact(fact)

    def get_preference(self, key: str, default=None):
        """Retrieve a user preference."""
        entry = self._preference_store.retrieve(key)
        if entry:
            return entry.value
        return default

    def set_preference(self, key: str, value) -> None:
        """Set a user preference."""
        entry = MemoryEntry(key=key, value=value, agent="memory_stage")
        self._preference_store.store(entry)
