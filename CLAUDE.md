# SplatVote

Community voting platform for Splatoon 3 at `vote.splat.top`.

## Overview

SplatVote allows users to vote on A vs B (or N options) in different categories. It supports multiple comparison modes, uses browser fingerprinting for vote deduplication, and displays results with statistical confidence intervals.

## Architecture

```
Frontend (React)  →  Backend (FastAPI)  →  PostgreSQL (voting schema)
                           ↓
                        Redis (rate limiting, caching)
```

### Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, asyncpg, Redis
- **Frontend**: React 18, React Router, Tailwind CSS, dnd-kit
- **Database**: PostgreSQL (shared with SplatTop, `voting` schema)
- **Deployment**: Docker, Kubernetes, Helm, ArgoCD

## Project Structure

```
src/
├── vote_api/                    # FastAPI backend
│   ├── app.py                   # Application entry point
│   ├── connections.py           # DB/Redis connections
│   ├── middleware.py            # Rate limiting
│   ├── models/
│   │   ├── database.py          # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   └── enums.py             # ComparisonMode enum
│   ├── routes/
│   │   ├── categories.py        # GET /categories
│   │   ├── votes.py             # POST /vote, GET /vote/status
│   │   ├── results.py           # GET /results/{id}
│   │   ├── admin.py             # Admin endpoints
│   │   └── health.py            # Health checks
│   └── services/
│       ├── fingerprint.py       # Browser fingerprint validation
│       ├── statistics.py        # Wilson score, percentages
│       ├── elo.py               # ELO rating calculations
│       └── category_sync.py     # YAML category loader
├── vote_frontend/               # React frontend
│   └── src/
│       ├── components/
│       │   ├── VoteMode/        # SingleChoice, EloTournament, RankedList
│       │   ├── Results/         # Charts and rankings
│       │   └── Categories/      # Category listing
│       └── hooks/
│           ├── useFingerprint.js
│           └── useVoteAPI.js
└── shared_lib/
    └── db.py                    # Database URI builder

data/
├── categories/                  # Category definitions (YAML)
└── item_groups/                 # Item group definitions (YAML)

migrations/
└── versions/                    # Alembic migrations

dockerfiles/
├── dockerfile.vote-api
├── dockerfile.vote-frontend
└── nginx.conf
```

## Database Schema

All tables are in the `voting` schema:

```
item_groups      - Groups of items (Weapons, Maps, Modes)
items            - Individual votable items with metadata
categories       - Voting categories with comparison mode
category_items   - Links items to categories (N items per category)
votes            - User votes (unique per fingerprint+category)
vote_choices     - Choices within a vote (supports ranking)
comments         - Optional user comments
elo_ratings      - ELO ratings for tournament mode
```

## Comparison Modes

### Single Choice (`single_choice`)
User selects one option from N choices. Results show percentages with Wilson confidence intervals.

### ELO Tournament (`elo_tournament`)
Head-to-head matchups. Each vote updates ELO ratings for both items. Results show ranked leaderboard by ELO.

### Ranked List (`ranked_list`)
Drag-and-drop to rank all items. Results show average rank and first-place percentages.

## Anti-Manipulation

### Browser Fingerprinting
Collects: canvas, WebGL, audio context, hardware info, screen, timezone, language, plugins. Hashed client-side with SHA-256.

### Server-Side Validation
- Fingerprint format validation (64-char hex)
- IP hashing with server-side pepper
- Unique constraint: one vote per fingerprint per category
- Rate limiting: 10 votes/minute per IP
- Pattern detection: flags IPs with many fingerprints or fingerprints from many IPs

## Statistics

### Wilson Score Confidence Interval
For single-choice voting, calculates 95% confidence bounds. Better than simple percentages for small sample sizes.

```python
wilson_confidence_interval(successes, total, confidence=0.95)
# Returns (lower_bound, upper_bound) as percentages
```

### ELO Rating
Standard ELO with K-factor of 32, initial rating 1500.

```python
calculate_elo_update(winner_rating, loser_rating, k_factor=32)
# Returns (new_winner, new_loser)
```

## Category Management

Categories and items are defined in YAML files in `data/`:

```yaml
# data/item_groups/weapons.yaml
name: "Weapons"
items:
  - name: "Splattershot"
    image_url: "https://..."
    metadata:
      type: "shooter"
      class: "Shooter"

# data/categories/best_weapon.yaml
name: "Best Weapon for Beginners"
comparison_mode: single_choice
item_group: "Weapons"
filter:
  metadata:
    class: ["Shooter", "Roller"]
```

Sync via admin API: `POST /api/v1/admin/sync`

## API Endpoints

### Public
- `GET /api/v1/categories` - List active categories
- `GET /api/v1/categories/{id}` - Get category with items
- `POST /api/v1/vote` - Submit vote (requires fingerprint)
- `GET /api/v1/vote/status/{category_id}?fingerprint=...` - Check if voted
- `GET /api/v1/results/{category_id}` - Get results with statistics

### Admin (requires `X-Admin-Token` header)
- `POST /api/v1/admin/sync` - Sync categories from YAML
- `GET /api/v1/admin/comments/pending` - List pending comments
- `PUT /api/v1/admin/comments/{id}/approve` - Approve/reject comment

## Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL with `voting` schema
- Redis

### Backend
```bash
cd /root/dev/SplatVote
pip install -e .
alembic upgrade head
python -m vote_api.app
```

### Frontend
```bash
cd src/vote_frontend
npm install
npm start
```

### Environment Variables
```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=splattop
REDIS_HOST=localhost
REDIS_PORT=6379
VOTE_IP_PEPPER=dev-pepper
ADMIN_TOKEN_PEPPER=dev-admin-pepper
ADMIN_API_TOKENS_HASHED=<sha256_of_your_token>
DEV_MODE=true
```

## Deployment

See [SplatTopConfig/SPLATVOTE.md](https://github.com/cesaregarza/SplatTopConfig/blob/main/SPLATVOTE.md) for Kubernetes deployment.

### Build Images
```bash
docker build -f dockerfiles/dockerfile.vote-api -t vote-api:latest .
docker build -f dockerfiles/dockerfile.vote-frontend -t vote-frontend:latest .
```

### Run Migration
```bash
alembic upgrade head
```
