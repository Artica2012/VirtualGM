from fastapi import FastAPI
import uvicorn

app = FastAPI()


def start_uvicorn(loop):
    config = uvicorn.Config(app, loop=loop)
    server = uvicorn.Server(config)
    loop.create_task(server.serve())
