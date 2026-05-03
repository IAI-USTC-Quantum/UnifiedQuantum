"""Gateway REST API routes."""

from fastapi import APIRouter

from uniqc.gateway.api import archive, backends, circuits, tasks

router = APIRouter()
router.include_router(backends.router, prefix="/backends", tags=["backends"])
router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
router.include_router(archive._archive_router, tags=["archive"])
router.include_router(archive._archive_move_router, tags=["tasks"])
router.include_router(circuits.router, prefix="/circuits", tags=["circuits"])
