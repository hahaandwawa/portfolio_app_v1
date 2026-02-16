from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.db import init_database
from src.app.api.routers import accounts, transactions, portfolio, net_value


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="投资记录 API",
    description="Investment record management",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "file://",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(net_value.router)


@app.get("/")
def root():
    return {"message": "投资记录 API", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check for Electron/load balancers. Returns quickly."""
    return {"status": "ok"}
