# SplatVote

Community voting platform for Splatoon 3.

## Local development

```bash
make compose-up
make compose-migrate
```

Frontend: http://localhost:3000  
API: http://localhost:8000

## Backend (manual)

```bash
pip install -e .
alembic upgrade head
python -m vote_api.app
```

## Frontend (manual)

```bash
cd src/vote_frontend
npm install
npm start
```
