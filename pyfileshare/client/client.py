import aiohttp
from aiohttp import web
from typing import Dict, Union, List, Any
import json
import asyncio

routes = web.RouteTableDef()

with open('config.json', 'r') as f:
    config = json.load(f)

class _ws(web.Application):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._port = config['port']
        self.files = config['files']


    def run(self) -> None:
        self.on_startup.append(self.server_con)
        self.add_routes(routes)
        web.run_app(self, port=self._port)


    async def server_con(self, app: web.Application):
        self.session = aiohttp.ClientSession()
        async with self.session.ws_connect(config['server']) as ws:
            #await ws.send_json({'type': 'create_acc', 'name': 'cartman', 'key': 'test'})
            
            #perform the inital connection to the server
            self.socket = ws
            await ws.send_json({'type': 'login', 'name': config['name'], 'key': config['key'], 'port': config['port']})
            x = await ws.receive()
            await ws.send_json({'type': 'file_reg', 'files': self.files})
            x = await ws.receive()
            data = x.json()
            # if data['type'] == 'file_reg_resp':
            #     for file in data['files']:
            #         self.files[file] = data['files'][file]
            #         config['files'][file] = data['files'][file]
            #     with open('config.json', 'w') as f:
            #         json.dump(config, f, indent=4)

            async for msg in ws:
                data = msg.json()
                print(data)
                # if data['type'] == 'file_resp':
                #     await self.local.send_json({'type': 'file', 'host': data['host'], 'filename': data['filename']})


    def get_by_val(self, dict: dict, value: Any) -> Any:
        for x, y in dict.items():
            if y == value:
                return x
        return None


    # @routes.get('/ws')
    # async def local_conn(request):
    #     if request.remote == '127.0.0.1':
    #         ws = web.WebSocketResponse()
    #         await ws.prepare(request)
    #         await ws.send_json({'type': 'ready'})
    #         app.local = ws
    #         async for msg in ws:
    #             data = msg.json()
    #             if data['type'] == "download":
    #                 await app.socket.send_json({'type': 'req_file', 'file_id': data['file_id']})


    @routes.get('/file')
    async def file_handle(request):
        # check if file is in hosting list
        id = int(request.rel_url.query['id'])
        print(app.files.values())
        if id in app.files.values():
            return web.FileResponse(path=app.get_by_val(app.files, id))
        else:
            return web.Response(body="file not found", status=404)
        


if __name__ == "__main__":
    app = _ws()
    app.run()