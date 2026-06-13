"""Colorgrade pipeline operation stub."""

from __future__ import annotations

from thea.operations import Operation, register


class ColorgradeOperation(Operation):
    name = "colorgrade"
    description = "Apply color grading to pipeline outputs."
    status = "stub"

    def execute(self, context, config: dict):
        raise NotImplementedError(f"{self.name} is not yet implemented")


register(ColorgradeOperation())
