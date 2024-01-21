from fastapi import FastAPI
import uvicorn
import API.endpoints as endpoints
import API.roll_endpoints as roll_endpoints
import API.macro_endpoints as macro_endpoints
import API.initiative_endpoints as initiative_endpoints
import API.character_endpoints as character_endpoints
import API.automation_endpoints as automation_endpoints


app = FastAPI()
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
