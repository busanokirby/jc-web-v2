"""Shared base class for all declarative models.

Provides a permissive constructor that accepts arbitrary keyword arguments
so that clients can instantiate models using column names without
static type checker complaints.  All database models should inherit from
``BaseModel`` in addition to ``db.Model``.
"""
from typing import Any

from app.extensions import db


class BaseModel(db.Model):
    __abstract__ = True
    # permit legacy or purely-typing annotations without ``Mapped``
    __allow_unmapped__ = True

    def __init__(self, **kwargs: Any) -> None:
        # SQLAlchemy's base ``__init__`` already accepts ``**kwargs``; this
        # explicit override gives Pyright/Pylance a concrete signature so that
        # calls like ``Product(name=name, sku=sku)`` no longer trigger
        # "No parameter named ..." errors.
        super().__init__(**kwargs)
