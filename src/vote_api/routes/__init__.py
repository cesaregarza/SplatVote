# Routes package
from vote_api.routes.admin import router as admin_router
from vote_api.routes.categories import router as categories_router
from vote_api.routes.health import router as health_router
from vote_api.routes.results import router as results_router
from vote_api.routes.votes import router as votes_router

__all__ = [
    "admin_router",
    "categories_router",
    "health_router",
    "results_router",
    "votes_router",
]
