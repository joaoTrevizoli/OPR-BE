from fastapi import FastAPI, APIRouter
from project.api.v1.authentication import authentication
from project.api.v1.admin import admin
from project.config import settings
from project.db import initiate_database, close_db_connect
from fastapi.middleware.cors import CORSMiddleware


def register_blueprint(app: FastAPI):
    app.include_router(authentication.router)
    app.include_router(admin.router)


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_event_handler("startup", initiate_database)
    app.add_event_handler("shutdown", close_db_connect)
    register_blueprint(app)
    return app
