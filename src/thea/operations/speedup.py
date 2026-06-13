"""Speedup pipeline operation stub."""

from __future__ import annotations

from thea.operations import Operation, register


class SpeedupOperation(Operation):
    name = "speedup"
    description = "Apply speedup effects to pipeline outputs."
    status = "stub"

    def execute(self, context, config: dict):
        raise NotImplementedError(f"{self.name} is not yet implemented")


register(SpeedupOperation())
