from __future__ import annotations

from fastapi import APIRouter

from app.web.routes.accounts import router as accounts_router
from app.web.routes.home import router as home_router
from app.web.routes.media import router as media_router
from app.web.routes.system import router as system_router
from app.web.routes.workflow import router as workflow_router

router = APIRouter()
router.include_router(accounts_router)
router.include_router(home_router)
router.include_router(media_router)
router.include_router(workflow_router)
router.include_router(system_router)
