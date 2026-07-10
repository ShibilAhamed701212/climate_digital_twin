"""Pipeline engine for executing Cognitive Pipeline Definitions.

The Runtime loads pipeline definitions, resolves stage dependencies,
executes stages, and collects results — without knowing what the stages do.
"""

from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage  # noqa: F401
from runtime.pipeline.engine import PipelineEngine  # noqa: F401
