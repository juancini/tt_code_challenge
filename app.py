from fastapi import FastAPI
from routers.team_insight import router

app = FastAPI()
app.include_router(router)
