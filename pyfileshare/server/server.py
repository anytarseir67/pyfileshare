import aiohttp
from aiohttp import web
import asyncpg
import secrets
from typing import Dict, Union, List, Any

try:
    import config
except ImportError:
    import sys
    sys.exit('config not found, create a config.py based on the example')

routes = web.RouteTableDef()

class PyFileShareServer(web.Application):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._port = config.port
        self.sockets: Dict[int, web.WebSocketResponse] = {}


    def run(self) -> None:
        self.on_startup.append(self.db_init)
        self.add_routes(routes)
        web.run_app(self, port=self._port)


    async def db_init(self, app):
        self.conn = await asyncpg.connect(user=config.db_user, password=config.db_password,
                                    database=config.db, host=config.db_host)


    async def is_taken(self, table: str, column: str, value: Any) -> bool:
        taken = await self.conn.fetch(f'SELECT {column} FROM {table} WHERE {column}=$1', value)
        taken = taken[0][column]
        return taken != None


    async def login(self, ws, msg: aiohttp.WSMessage, json):
        resp = await self.conn.fetch('SELECT id FROM accounts WHERE name=$1 AND key=$2', json['name'], json['key'])
        resp = resp[0]
        if len(str(resp['id'])) == 8:
            ws['user'] = resp['id']
            self.sockets[resp['id']] = ws
            return {'type': 'resp', 'id': resp['id']}
        return {'type': 'error', 'error': 'acc not found'}


    async def create_acc(self, ws, msg, json) -> Dict[str, Union[str, int]]:
        try:
            does_exist = await self.conn.fetch('SELECT id FROM accounts WHERE name=$1', json['name'])
            does_exist = does_exist[0]['id']
            if len(does_exist) == 0:
                id = secrets.choice(range(10000000, 99999999))
                while await self.is_taken('accounts', 'id', id) == True:
                    id = secrets.choice(range(10000000, 99999999))
                usr = json['name']
                key = json['key']
                await self.conn.execute('INSERT INTO accounts (name, key, id) VALUES ($1, $2, $3)', usr, key, id)
                id = await self.login(ws, msg, {'name': usr, 'key': key})
                return {'type': 'create_acc_resp', 'id': id}
            return {'type': 'error', 'error': 'name is taken'}
        except:
            return {'type': 'error', 'error': 'failed to create account'}


    @routes.get('/')
    async def listen(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()

                if data['type'] == 'login':
                    resp = await app.login(ws, msg, data)
                    await ws.send_json(resp)

                elif data['type'] == 'create_acc':
                    resp = await app.create_acc(ws, msg, data)
                    await ws.send_json(resp)

                elif ws.get('user'):
                    pass
                else:
                    await ws.send_json({'type': 'error', 'error': 'endpoint not found'})

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception %s' % ws.exception())

        app.sockets.pop(ws['user'])


if __name__ == "__main__":
    app = PyFileShareServer()
    app.run()