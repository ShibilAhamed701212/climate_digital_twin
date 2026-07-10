"""PipelineEngine — loads pipeline definitions, resolves execution order, executes stages.

Supports DAG execution: stages declare dependencies, engine groups them into
parallel-executable layers. Phase 2 uses sequential stages (no cross-stage deps),
but the engine already supports the DAG pattern.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from runtime.models.pipeline import CognitivePipeline, ExecutionContext, PipelineStage

logger = logging.getLogger(__name__)


class PipelineEngine:
    """Executes Cognitive Pipeline Definitions.

    Responsibilities:
    - Register and find pipelines by trigger
    - Resolve stage execution order (DAG-aware)
    - Execute stages with lifecycle hooks
    - Handle timeouts, errors, and regeneration
    """

    def __init__(self):
        self._pipelines: dict[str, list[CognitivePipeline]] = defaultdict(list)

    def register(self, pipeline: CognitivePipeline) -> None:
        for trigger in pipeline.triggers:
            self._pipelines[trigger].append(pipeline)

    def find(self, trigger: str) -> CognitivePipeline | None:
        pipelines = self._pipelines.get(trigger, [])
        if not pipelines:
            return None
        if len(pipelines) > 1:
            logger.warning(f"Multiple pipelines for trigger '{trigger}', using first")
        return pipelines[0]

    def resolve_execution_order(
        self, stages: list[PipelineStage]
    ) -> list[list[PipelineStage]]:
        """Resolve stages into dependency layers for parallel execution.

        Returns list of layers — stages in each layer can run in parallel.
        Within each layer, stages preserve their original definition order
        so that zero-dependency stages execute in the expected sequence.

        When all stage dependencies are empty (no declared deps), all stages
        land in a single layer and execute in their original definition order.
        """
        stage_map = {s.name: s for s in stages}
        resolved: set[str] = set()
        layers: list[list[PipelineStage]] = []

        # Preserve original definition order
        remaining_names = [s.name for s in stages]

        while remaining_names:
            layer: list[PipelineStage] = []
            still_remaining: list[str] = []

            for name in remaining_names:
                stage = stage_map[name]
                deps = set(stage.dependencies)
                if deps.issubset(resolved):
                    layer.append(stage)
                else:
                    still_remaining.append(name)

            if not layer:
                logger.error(
                    f"Circular dependency detected in pipeline stages: {still_remaining}"
                )
                break

            layers.append(layer)
            resolved.update(s.name for s in layer)
            remaining_names = still_remaining

        return layers

    async def execute(
        self,
        pipeline: CognitivePipeline,
        ctx: ExecutionContext,
    ) -> ExecutionContext:
        """Execute a pipeline through its stages with lifecycle management."""
        logger.info(
            f"Executing pipeline '{pipeline.id}' with {len(pipeline.stages)} stages"
        )
        ctx.execution_metadata["pipeline_id"] = pipeline.id
        ctx.execution_metadata["pipeline_start"] = ctx.runtime_context.start_time

        layers = self.resolve_execution_order(pipeline.stages)

        for layer_idx, layer in enumerate(layers):
            for stage in layer:
                stage_name = stage.name
                ctx.log_stage(stage_name, "starting")

                try:
                    # Pre-execute hook
                    await stage.before_execute(ctx)

                    # Execute with timeout
                    try:
                        ctx = await asyncio.wait_for(
                            stage.execute(ctx),
                            timeout=stage.timeout_ms / 1000.0,
                        )
                    except TimeoutError:
                        ctx = await stage.on_timeout(ctx)
                        ctx.log_stage(stage_name, "timeout")
                        continue

                    # Post-execute hook
                    await stage.after_execute(ctx)

                    ctx.log_stage(stage_name, "completed")
                    ctx.add_metric(f"stage.{stage_name}.success", True)

                except Exception as e:
                    logger.exception(f"Stage '{stage_name}' failed: {e}")
                    ctx = await stage.on_error(ctx, e)
                    ctx.log_stage(stage_name, "failed")
                    ctx.add_metric(f"stage.{stage_name}.success", False)
                    ctx.add_metric(f"stage.{stage_name}.error", str(e))

                    # Allow one regeneration cycle if Verification stage requests it
                    if stage_name == "verification" and ctx.regenerate_count < 1:
                        ctx.regenerate_count += 1
                        ctx.log_stage(
                            "pipeline", f"regeneration attempt {ctx.regenerate_count}"
                        )
                        for prev_layer in layers[:layer_idx]:
                            for prev_stage in prev_layer:
                                if (
                                    prev_stage.name in ctx.stage_outputs
                                    and prev_stage.name in ["response"]
                                ):
                                    del ctx.stage_outputs[prev_stage.name]
                                    break

        ctx.execution_metadata["pipeline_end"] = ctx.runtime_context.elapsed_ms()
        ctx.log_stage(
            "pipeline",
            "completed",
            {
                "total_stages": len(pipeline.stages),
                "layers": len(layers),
                "errors": len(ctx.errors),
            },
        )

        return ctx

    def list_triggers(self) -> list[str]:
        return list(self._pipelines.keys())
