import datetime
import json
import logging
import os
import websockets

from WSEndpoints.ws_initiative import get_user_tables

api_keys = os.environ.get("WEB_APP").split(",")


class WebsocketHandler:
    def __init__(self):
        self.connections = set()
        self.library = {}

    async def handle(self, websocket):
        self.connections.add(websocket)
        await websocket.send("Connected")
        while True:
            try:
                async for message in websocket:
                    print(message)

                    msg = json.loads(message)
                    if msg["auth"] in api_keys:
                        match msg["header"].lower():  # noqa
                            case "init":
                                match msg["func"]:
                                    case "user_tables":
                                        print("user tables")
                                        print(msg)
                                        await websocket.send(await get_user_tables(msg))
                    else:
                        await websocket.send(json.dumps({"result": False}))

                    match message[:3].lower():  # noqa
                        case "pin":
                            await self.ping(websocket)
                        case "con":
                            await self.register(websocket, message)
                        case "clo":
                            await self.disconnect(websocket)

                await websocket.wait_closed()
            finally:
                await self.disconnect(websocket)

    async def disconnect(self, websocket):
        del_list = []

        for g in self.library.keys():
            if websocket in self.library[g]:
                self.library[g].remove(websocket)
                if len(self.library[g]) == 0:
                    del_list.append(g)

        for g in del_list:
            del self.library[g]

        try:
            self.connections.remove(websocket)
        except KeyError:
            pass

    async def ping(self, websocket):
        timestamp = datetime.datetime.now()
        await websocket.send(f"Pong {timestamp}")

    async def register(self, websocket, message):
        try:
            guild_id = int(message.split(":")[1])
        except ValueError as e:
            logging.error(f"Value Error:websocket {message}{e}")
            return False
        except TypeError as e:
            logging.error(f"Type Error: websocket {message}{e}")
            return False
        except Exception as e:
            logging.error(f"Error: websocket {message}{e}")
            return False

        if guild_id in self.library.keys():
            self.library[guild_id].append(websocket)
        else:
            self.library[guild_id] = [websocket]

        await websocket.send(f"Connected to: {guild_id}")

    async def stream_channel(self, guild_id, tracker_data, header):
        processed_data = {"type": header, "data": tracker_data}

        output = json.dumps(processed_data)
        channel = self.library[guild_id]
        for ws in channel:
            try:
                await ws.send(output)
            except Exception as e:
                logging.error(f"Websocket stream_channel error: {e}")

    async def library_check(self, guild_id):
        if guild_id in self.library.keys():
            return True
        else:
            return False

    async def broadcast(self, message):
        websockets.broadcast(self.connections, str(message))

    async def stream(self, guild_id, message, header: str):
        try:
            if await self.library_check(guild_id):
                await socket.stream_channel(guild_id, message, header)
        except Exception as e:
            logging.error(f"websocket stream {e}")


socket = WebsocketHandler()
