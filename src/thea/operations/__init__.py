"""Operation registry and base class for pipeline operations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from thea.pipeline import PipelineContext

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, "Operation"] = {}


class Operation(ABC):
    """Base class for all pipeline operations."""

    name: str = ""
    description: str = ""
    requires: list[str] = []
    provides: list[str] = []
    status: str = "implemented"  # "implemented" | "stub"

    @abstractmethod
    def execute(self, context: "PipelineContext", config: dict) -> "PipelineContext":
        """Execute this operation, updating and returning the context."""
        ...

    def to_dict(self) -> dict:
        """Serialize operation metadata for discovery."""
        return {
            "name": self.name,
            "description": self.description,
            "requires": self.requires,
            "provides": self.provides,
            "status": self.status,
        }


def register(operation: Operation) -> Operation:
    """Register an operation in the global registry."""
    _REGISTRY[operation.name] = operation
    return operation


def get_registry() -> dict[str, Operation]:
    """Get all registered operations. Triggers lazy import of operation modules."""
    if not _REGISTRY:
        _load_operations()
    return _REGISTRY


def _load_operations():
    """Import all operation modules to trigger registration."""
    from thea.operations import downscale, analyze, slice_op, colorgrade, slowdown, speedup  # noqa: F401
