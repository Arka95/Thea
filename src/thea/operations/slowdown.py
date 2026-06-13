"""Slowdown pipeline operation stub."""

from __future__ import annotations

from thea.operations import Operation, register


class SlowdownOperation(Operation):
    name = "slowdown"
    description = "Apply slowdown effects to pipeline outputs."
    status = "stub"

    def execute(self, context, config: dict):
        raise NotImplementedError(f"{self.name} is not yet implemented")


register(SlowdownOperation())
