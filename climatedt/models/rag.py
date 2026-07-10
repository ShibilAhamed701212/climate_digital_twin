import uuid
from typing import Any


class Document:
    def __init__(
        self,
        title: str = "",
        source: str = "",
        content: str = "",
        content_type: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.document_id = uuid.uuid4().hex[:16]
        self.title = title
        self.source = source
        self.content = content
        self.content_type = content_type
        self.tags = tags or []
        self.metadata = metadata or {}
