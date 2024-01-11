from fastapi import FastAPI
import uvicorn
import API.endpoints as endpoints


app = FastAPI()
app.include_router(endpoints.router)


def start_uvicorn(loop):
    config = uvicorn.Config(app, loop=loop, port=8080, host="0.0.0.0")
    server = uvicorn.Server(config)
    loop.create_task(server.serve())
