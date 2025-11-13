from fastapi import FastAPI, APIRouter
from project.api.v1.authentication import authentication
from project.api.v1.admin import admin
from project.api.v1.feed_dry_matter import feed_dry_matter
from project.api.v1.farm import farm
from project.api.v1.manure_score import manure_score
from project.api.v1.diet_cost import diet_cost
from project.api.v1.penn_state import penn_state
from project.api.v1.penn_state_diet import penn_state_diet
from project.api.v1.scale import scale
from project.api.v1.environment import environment
from project.api.v1.factory import factory
from project.api.v1.trough_score import trough_score
from project.api.v1.storage_inspection import storage_inspection
from project.config import settings
from project.db import initiate_database, close_db_connect
from fastapi.middleware.cors import CORSMiddleware


def register_blueprint(app: FastAPI):
    app.include_router(authentication.router)
    app.include_router(admin.router)
    app.include_router(feed_dry_matter.router)
    app.include_router(farm.router)
    app.include_router(manure_score.router)
    app.include_router(diet_cost.router)
    app.include_router(penn_state.router)
    app.include_router(penn_state_diet.router)
    app.include_router(scale.router)
    app.include_router(environment.router)
    app.include_router(factory.router)
    app.include_router(trough_score.router)
    app.include_router(storage_inspection.router)


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
