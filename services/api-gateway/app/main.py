from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
	init_db()
	yield

app = FastAPI(title="AegisOps API Gateway", version="0.1.0", lifespan=lifespan)
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:3000",
		"http://127.0.0.1:3000",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")
