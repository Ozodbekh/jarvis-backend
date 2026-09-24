from fastapi import APIRouter

from app.api.v1.command.router import router as command_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(command_router)

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)
