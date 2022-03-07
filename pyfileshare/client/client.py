import aiohttp
from aiohttp import web
from typing import Dict, Union, List, Any
import json

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
            await ws.send_json({'type': 'login', 'name': config['name'], 'key': config['key']})
            x = await ws.receive()
            await ws.send_json({'type': 'file_reg', 'files': self.files})
            async for msg in ws:
                data = msg.json()
                print(data)

    def get_by_val(self, dict, value):
        for x, y in dict.items():
            if y == value:
                return x
        return None

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