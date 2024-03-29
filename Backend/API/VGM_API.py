import uvicorn
from fastapi import FastAPI

import Backend.API.automation_endpoints as automation_endpoints
import Backend.API.character_endpoints as character_endpoints
import Backend.API.endpoints as endpoints
import Backend.API.initiative_endpoints as initiative_endpoints
import Backend.API.macro_endpoints as macro_endpoints
import Backend.API.roll_endpoints as roll_endpoints
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://localhost:5173",
    "https://virtualgm.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_credentials=True,
    # allow_origin_regex=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(endpoints.router)
app.include_router(roll_endpoints.router)
app.include_router(macro_endpoints.router)
app.include_router(initiative_endpoints.router)
app.include_router(character_endpoints.router)
app.include_router(automation_endpoints.router)


def start_uvicorn(loop):
    config = uvicorn.Config(app, loop=loop, port=8080, host="0.0.0.0")
    server = uvicorn.Server(config)
    loop.create_task(server.serve())
