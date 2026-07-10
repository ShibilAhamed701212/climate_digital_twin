"""Unit tests for BaseTool abstract class."""

import pytest

from copilot.tools.base import BaseTool


class TestBaseTool:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseTool()

    def test_concrete_subclass_must_implement_all_methods(self):
        with pytest.raises(TypeError):

            class IncompleteTool(BaseTool):
                def run(self):
                    return {}

            IncompleteTool()

    def test_concrete_subclass_works(self):
        class ConcreteTool(BaseTool):
            def run(self):
                return {"result": "ok"}

            def validate(self):
                return True, ""

            def describe(self):
                return {"name": "test"}

            def health_check(self):
                return True, "healthy"

        tool = ConcreteTool()
        assert tool.run() == {"result": "ok"}
        assert tool.validate() == (True, "")
        assert tool.describe() == {"name": "test"}
        assert tool.health_check() == (True, "healthy")
