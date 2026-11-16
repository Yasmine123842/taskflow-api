from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Un client de test avec une base neuve pour chaque test."""
    monkeypatch.setenv("TASKFLOW_DB", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


def create(client, **fields):
    response = client.post("/tasks", json={"title": "Tâche de test", **fields})
    assert response.status_code == 201
    return response.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_task_sets_defaults(client):
    task = create(client, title="  Écrire le README  ")
    assert task["id"] == 1
    assert task["title"] == "Écrire le README"
    assert task["status"] == "a_faire"
    assert task["priority"] == "moyenne"
    assert task["due_date"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "x" * 121},
        {"title": "Ok", "priority": "urgente"},
        {"title": "Ok", "due_date": "pas-une-date"},
    ],
)
def test_create_task_rejects_invalid_payload(client, payload):
    assert client.post("/tasks", json=payload).status_code == 422


def test_get_task(client):
    task = create(client)
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_get_missing_task_returns_404(client):
    assert client.get("/tasks/999").status_code == 404


def test_list_tasks_newest_first(client):
    create(client, title="Première")
    create(client, title="Deuxième")
    titles = [task["title"] for task in client.get("/tasks").json()]
    assert titles == ["Deuxième", "Première"]


def test_list_tasks_filters(client):
    create(client, title="Payer la facture", priority="haute")
    done = create(client, title="Appeler le client", priority="basse")
    client.patch(f"/tasks/{done['id']}", json={"status": "terminee"})

    assert [t["title"] for t in client.get("/tasks?priority=haute").json()] == ["Payer la facture"]
    assert [t["title"] for t in client.get("/tasks?status=terminee").json()] == ["Appeler le client"]
    assert [t["title"] for t in client.get("/tasks?q=facture").json()] == ["Payer la facture"]
    assert client.get("/tasks?status=inconnu").status_code == 422


def test_search_treats_wildcards_literally(client):
    create(client, title="Remise de 50% sur tout")
    create(client, title="Autre tâche")
    assert len(client.get("/tasks", params={"q": "50%"}).json()) == 1
    assert client.get("/tasks", params={"q": "%"}).json()[0]["title"] == "Remise de 50% sur tout"


def test_pagination(client):
    for index in range(5):
        create(client, title=f"Tâche {index}")
    page = client.get("/tasks?limit=2&offset=2").json()
    assert [task["title"] for task in page] == ["Tâche 2", "Tâche 1"]


def test_update_only_changes_sent_fields(client):
    task = create(client, description="À garder", priority="haute")
    updated = client.patch(f"/tasks/{task['id']}", json={"status": "en_cours"}).json()
    assert updated["status"] == "en_cours"
    assert updated["description"] == "À garder"
    assert updated["priority"] == "haute"


def test_update_can_clear_optional_fields(client):
    task = create(client, description="À effacer", due_date="2030-01-01")
    updated = client.patch(
        f"/tasks/{task['id']}", json={"description": None, "due_date": None}
    ).json()
    assert updated["description"] is None
    assert updated["due_date"] is None


def test_update_rejects_null_title(client):
    task = create(client)
    assert client.patch(f"/tasks/{task['id']}", json={"title": None}).status_code == 422


def test_update_missing_task_returns_404(client):
    assert client.patch("/tasks/999", json={"status": "terminee"}).status_code == 404


def test_delete_task(client):
    task = create(client)
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
    assert client.delete(f"/tasks/{task['id']}").status_code == 404


def test_stats(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    create(client, priority="haute", due_date=yesterday)  # en retard
    create(client, priority="haute", due_date=tomorrow)
    late_but_done = create(client, priority="basse", due_date=yesterday)
    client.patch(f"/tasks/{late_but_done['id']}", json={"status": "terminee"})

    assert client.get("/stats").json() == {
        "total": 3,
        "by_status": {"a_faire": 2, "terminee": 1},
        "by_priority": {"basse": 1, "haute": 2},
        "overdue": 1,
    }


def test_stats_on_empty_database(client):
    assert client.get("/stats").json() == {
        "total": 0,
        "by_status": {},
        "by_priority": {},
        "overdue": 0,
    }
