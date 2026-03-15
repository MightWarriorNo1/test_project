"""Topology versioning: store and retrieve graph snapshots by version."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from ntl_engine.graph.build import GridGraph


class TopologyStore(ABC):
    """Abstract store for versioned grid topologies."""

    @abstractmethod
    def put(self, version_id: str, graph: GridGraph) -> None:
        """Store graph under version_id."""
        ...

    @abstractmethod
    def get(self, version_id: str) -> Optional[GridGraph]:
        """Retrieve graph by version_id."""
        ...

    @abstractmethod
    def latest_version(self) -> Optional[str]:
        """Return latest version id if any."""
        ...


class InMemoryTopologyStore(TopologyStore):
    """In-memory topology store (e.g. for tests or single-node)."""

    def __init__(self) -> None:
        self._store: Dict[str, GridGraph] = {}
        self._order: list[str] = []

    def put(self, version_id: str, graph: GridGraph) -> None:
        self._store[version_id] = graph.copy()
        if version_id not in self._order:
            self._order.append(version_id)

    def get(self, version_id: str) -> Optional[GridGraph]:
        g = self._store.get(version_id)
        return g.copy() if g is not None else None

    def latest_version(self) -> Optional[str]:
        return self._order[-1] if self._order else None
