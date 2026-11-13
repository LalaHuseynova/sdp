"""Explicit research integration over original flat/withhold SAFE-Mem retrieval."""

from .adapter import GovernedRetrieval, RetrievalContext, RetrievalOutcome
from .metadata import AccessSnapshot, ArtifactGrant, BindingCatalog, RecordBinding, SourceBinding

__all__ = [
    "AccessSnapshot",
    "ArtifactGrant",
    "BindingCatalog",
    "GovernedRetrieval",
    "RecordBinding",
    "RetrievalContext",
    "RetrievalOutcome",
    "SourceBinding",
]
