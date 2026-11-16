# TaskFlow API ✅

Une API REST de gestion de tâches, écrite en Python avec **FastAPI** et **SQLite**.

- Création, lecture, modification et suppression de tâches (CRUD)
- Filtres par statut et priorité, recherche par titre, pagination
- Statistiques : répartition par statut et priorité, tâches en retard
- Validation des données avec Pydantic
- Documentation interactive générée automatiquement (Swagger)
- 20 tests automatisés avec pytest, lancés à chaque push par GitHub Actions
- Image Docker prête à l'emploi

## Démarrage rapide

Prérequis : Python 3.12 ou plus récent.

```bash
git clone https://github.com/VOTRE-UTILISATEUR/taskflow-api.git
cd taskflow-api

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
uvicorn app.main:app --reload
```

L'API est disponible sur http://localhost:8000 et la documentation interactive sur
http://localhost:8000/docs.

### Avec Docker

```bash
docker build -t taskflow-api .
docker run -p 8000:8000 -v taskflow-data:/data taskflow-api
```

## Points d'accès

| Méthode  | Chemin         | Description                               |
|----------|----------------|-------------------------------------------|
| `GET`    | `/health`      | Vérifie que l'API répond                  |
| `POST`   | `/tasks`       | Crée une tâche                            |
| `GET`    | `/tasks`       | Liste les tâches (filtres et pagination)  |
| `GET`    | `/tasks/{id}`  | Récupère une tâche                        |
| `PATCH`  | `/tasks/{id}`  | Modifie une tâche (champs envoyés seulement) |
| `DELETE` | `/tasks/{id}`  | Supprime une tâche                        |
| `GET`    | `/stats`       | Statistiques globales                     |

Paramètres de `GET /tasks` : `status`, `priority`, `q` (recherche dans le titre), `limit` (1 à 100), `offset`.

Valeurs possibles :

- `status` : `a_faire`, `en_cours`, `terminee`
- `priority` : `basse`, `moyenne`, `haute`

## Exemples

Créer une tâche :

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Préparer la démo", "priority": "haute", "due_date": "2026-12-01"}'
```

```json
{
  "id": 1,
  "title": "Préparer la démo",
  "description": null,
  "status": "a_faire",
  "priority": "haute",
  "due_date": "2026-12-01",
  "created_at": "2026-11-16T22:04:38Z",
  "updated_at": "2026-11-16T22:04:38Z"
}
```

Passer la tâche à « en cours » :

```bash
curl -X PATCH http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "en_cours"}'
```

Lister les tâches prioritaires encore à faire :

```bash
curl "http://localhost:8000/tasks?status=a_faire&priority=haute"
```

Sous Windows PowerShell, le plus simple est de tester depuis http://localhost:8000/docs.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

Chaque test utilise une base SQLite temporaire : vos données ne sont jamais touchées.

## Structure

```
taskflow-api/
├── app/
│   ├── main.py          # Routes de l'API
│   ├── schemas.py       # Modèles de données et validation
│   └── database.py      # Connexion SQLite et schéma
├── tests/
│   └── test_api.py      # Tests de bout en bout
├── .github/workflows/
│   └── ci.yml           # Tests automatiques à chaque push
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## Choix techniques

- **SQLite via le module standard `sqlite3`** : aucune base à installer, et des requêtes SQL
  lisibles. Toutes les valeurs passent par des paramètres (`?`), jamais par concaténation.
- **`PATCH` partiel** : seuls les champs présents dans la requête sont modifiés, ce qui permet
  aussi de vider un champ optionnel en envoyant `null`.
- **Configuration par variable d'environnement** : `TASKFLOW_DB` définit le fichier de base
  (`taskflow.db` par défaut).

## Idées d'amélioration

- Authentification par jeton (JWT) et tâches par utilisateur
- Étiquettes sur les tâches
- Tri configurable (`?sort=due_date`)
- Migration vers PostgreSQL avec SQLAlchemy
