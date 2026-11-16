"""TaskFlow API — API REST de gestion de tâches."""

import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status

from .database import get_db, init_db
from .schemas import Priority, Stats, Status, Task, TaskCreate, TaskUpdate


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TaskFlow API",
    description="Une API REST simple pour gérer des tâches.",
    version="1.0.0",
    lifespan=lifespan,
)

Db = Annotated[sqlite3.Connection, Depends(get_db)]

# Colonnes qu'un client a le droit de modifier.
UPDATABLE = ("title", "description", "status", "priority", "due_date")
# Champs obligatoires en base : on refuse de les mettre à null.
NOT_NULL = ("title", "status", "priority")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_task(db: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable")
    return row


@app.get("/health", tags=["Système"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, tags=["Tâches"])
def create_task(payload: TaskCreate, db: Db):
    timestamp = now()
    cursor = db.execute(
        "INSERT INTO tasks (title, description, priority, due_date, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            payload.title.strip(),
            payload.description,
            payload.priority,
            payload.due_date.isoformat() if payload.due_date else None,
            timestamp,
            timestamp,
        ),
    )
    db.commit()
    return dict(fetch_task(db, cursor.lastrowid))


@app.get("/tasks", response_model=list[Task], tags=["Tâches"])
def list_tasks(
    db: Db,
    status_filter: Annotated[Status | None, Query(alias="status")] = None,
    priority: Priority | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Recherche dans le titre")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    clauses: list[str] = []
    params: list[object] = []
    if status_filter:
        clauses.append("status = ?")
        params.append(status_filter)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if q:
        clauses.append("title LIKE ? ESCAPE '\\'")
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(f"%{escaped}%")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        f"SELECT * FROM tasks {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=Task, tags=["Tâches"])
def get_task(task_id: int, db: Db):
    return dict(fetch_task(db, task_id))


@app.patch("/tasks/{task_id}", response_model=Task, tags=["Tâches"])
def update_task(task_id: int, payload: TaskUpdate, db: Db):
    fetch_task(db, task_id)
    changes = payload.model_dump(exclude_unset=True)

    for field in NOT_NULL:
        if field in changes and changes[field] is None:
            raise HTTPException(
                422, f"Le champ « {field} » ne peut pas être vide"
            )

    if changes:
        if changes.get("title"):
            changes["title"] = changes["title"].strip()
        if changes.get("due_date"):
            changes["due_date"] = changes["due_date"].isoformat()

        columns = [name for name in UPDATABLE if name in changes]
        assignments = ", ".join(f"{name} = ?" for name in columns)
        db.execute(
            f"UPDATE tasks SET {assignments}, updated_at = ? WHERE id = ?",
            (*(changes[name] for name in columns), now(), task_id),
        )
        db.commit()

    return dict(fetch_task(db, task_id))


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tâches"])
def delete_task(task_id: int, db: Db) -> Response:
    fetch_task(db, task_id)
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/stats", response_model=Stats, tags=["Statistiques"])
def stats(db: Db):
    by_status = dict(db.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    by_priority = dict(db.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority").fetchall())
    overdue = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE due_date < ? AND status != 'terminee'",
        (date.today().isoformat(),),
    ).fetchone()[0]
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
    }
