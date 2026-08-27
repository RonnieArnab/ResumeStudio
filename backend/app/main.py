from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.chat import router as chat_router
from app.api.routes.compile import router as compile_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resume import router as resume_router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Tear down the shared Playwright browser used by the job-apply flow.
    from app.services.jobs.apply.browser import shutdown as shutdown_apply_browser
    from app.services.jobs.apply.connected import shutdown as shutdown_connected

    await shutdown_apply_browser()
    await shutdown_connected()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_router)
app.include_router(compile_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
