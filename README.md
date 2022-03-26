```
poetry env use python3.7
poetry install
poetry shell
alembic upgrade head
```

How to generate Alembic migrations:
```
alembic revision --autogenerate -m "my migration"
```
