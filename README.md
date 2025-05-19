# Profile matcher service

Simple service to match and update player profile with active campaigns.

_API_ is built with **FastAPI** and _DB_ is run with **SQLite** mapped with **SQLAlchemy**.

_DB_ is saved locally in `profile_matcher.db`, if you modify models you need to stop server, erase file and run it again.

## Features

- Mock campaign and player data into an **SQLite** _DB_
- Retrieve a player profile by its ID
- Match player profile with active campaigns using matching rules
- Return an updated player profile with matching active campaigns

## Running instructions

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server:**
   ```bash
   uvicorn app:app --reload
   ```
   
3. **Open the Swagger UI:** http://localhost:8000/docs
   1. **Fill database with mock data:** POST _create_mock_data_
   2. **Test the endpoint:** GET _get_client_config/{**player_id**}_
      1. Use this _player_id_: **97983be2-98b7-11e7-90cf-082e5f28d836**

## Run tests

```bash
pip install pytest
pytest tests
```

## Improvements

- Set up **Alembic** for database migrations
- Set up pipelines with **GitHub Actions** for linting, type checking, code coverage, etc.
- Set up **PostgreSQL** instead of **SQLite**
- Use `uv` tool to manage dependencies
