from .start import router as start_router
from .teams import router as teams_router
from .admin import router as admin_router
from .game import router as game_router

__all__ = ["start_router", "teams_router", "admin_router", "game_router"]
