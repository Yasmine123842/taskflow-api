"""Modèles de données validés par Pydantic."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["a_faire", "en_cours", "terminee"]
Priority = Literal["basse", "moyenne", "haute"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120, examples=["Préparer la démo"])
    description: str | None = Field(default=None, max_length=1000)
    priority: Priority = "moyenne"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Tous les champs sont optionnels : seuls ceux envoyés sont modifiés."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    status: Status | None = None
    priority: Priority | None = None
    due_date: date | None = None


class Task(BaseModel):
    id: int
    title: str
    description: str | None
    status: Status
    priority: Priority
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class Stats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    overdue: int
