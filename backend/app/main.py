from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="CitrusGuard AI API",
    description="为 CitrusGuard AI 提供后端服务的 API。",
    version="0.1.0",
)

# CORS Middleware Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to CitrusGuard AI API"}

# Mount static files directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Import and include routers
from .api.v1 import users, orchards, upload, diagnosis, health, dashboard, cases
app.include_router(users.router, prefix="/api/v1")
app.include_router(orchards.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(diagnosis.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1/dashboard")
app.include_router(cases.router, prefix="/api/v1")