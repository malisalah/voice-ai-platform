"""SQLAlchemy declarative base and common mixins."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import registry

# Initialize SQLAlchemy registry for mapping
registry = registry()

# Declarative base for all models
Base: Any = registry.generate_base()


class IDMixin:
    """Mixin providing id column."""

    __allow_unmapped__ = True
    id: Mapped[str] = mapped_column(
        primary_key=True,
        index=True,
        nullable=False,
    )


class TimestampMixin:
    """Mixin providing created_at and updated_at columns."""

    __allow_unmapped__ = True
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Mixin providing tenant_id column for multi-tenancy."""

    __allow_unmapped__ = True
    tenant_id: Mapped[str] = mapped_column(
        nullable=False,
        index=True,
    )
