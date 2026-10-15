"""Permissions are application decisions; retrieved text cannot change them."""

import re
from dataclasses import dataclass

from sqlalchemy import select

from releaselens.models import Document

ROLE_LEVELS = {
    "reader": ("public",),
    "engineer": ("public", "internal"),
    "admin": ("public", "internal", "restricted"),
}


@dataclass(frozen=True)
class Principal:
    user: str
    role: str

    @property
    def classifications(self):
        return ROLE_LEVELS[self.role]


class NotFound(Exception):
    """Uniform missing/unauthorized response to avoid source-ID enumeration."""


class Forbidden(Exception):
    pass


def authorized_document(session, document_id, principal):
    doc = session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.classification.in_(principal.classifications),
        )
    )
    if doc is None:
        raise NotFound("Resource unavailable")
    return doc


def injection_marker(text: str) -> bool:
    # A demonstrative quarantine heuristic, NOT a general prompt-injection detector.
    return bool(
        re.search(
            r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions|"
            r"reveal\s+(the\s+)?(secret|api.key)|<\|system\|>|"
            r"[\u200b\u200c\u200d\u2060]",
            text,
            re.I,
        )
    )
