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
        self.ports: Dict[int, str] = {}
        self.sockets: Dict[int, web.WebSocketResponse] = {}
        self.files: Dict[int, int] = {}


    def run(self) -> None:
        self.on_startup.append(self.db_init)
        self.add_routes(routes)
        web.run_app(self, port=self._port)


    def get_by_val(self, dict: dict, value: Any) -> Any:
        for x, y in dict.items():
            if y == value:
                return x
        return None


    async def db_init(self, app):
        self.conn = await asyncpg.connect(user=config.db_user, password=config.db_password,
                                    database=config.db, host=config.db_host)


    async def is_taken(self, table: str, column: str, value: Any) -> bool:
        taken = await self.conn.fetch(f'SELECT {column} FROM {table} WHERE {column}=$1', value)
        return taken != []


    async def login(self, ws, msg: aiohttp.WSMessage, json):
        resp = await self.conn.fetch('SELECT id FROM accounts WHERE name=$1 AND key=$2', json['name'], json['key'])
        resp = resp[0]
        if len(str(resp['id'])) == 8:
            ws['user'] = resp['id']
            self.sockets[resp['id']] = ws
            self.ports[resp['id']] = json['port']
            return {'type': 'resp', 'id': int(resp['id'])}
        return {'type': 'error', 'error': 'acc not found'}


    async def create_acc(self, ws, msg, json) -> Dict[str, Union[str, int]]:
        try:
            does_exist = await self.conn.fetch('SELECT id FROM accounts WHERE name=$1', json['name'])
            if len(does_exist) == 0:
                id = int(secrets.choice(range(10000000, 99999999)))
                while await self.is_taken('accounts', 'id', id) == True:
                    id = int(secrets.choice(range(10000000, 99999999)))
                usr = json['name']
                key = json['key']
                await self.conn.execute('INSERT INTO accounts (name, key, id) VALUES ($1, $2, $3)', usr, key, id)
                id = await self.login(ws, msg, {'name': usr, 'key': key})
                return {'type': 'create_acc_resp', 'id': id}
            return {'type': 'error', 'error': 'name is taken'}
        except Exception as e:
            print(e)
            return {'type': 'error', 'error': 'failed to create account'}


    async def get_file(self, file_id):
        try:
            file_id = int(file_id)
            resp = await self.conn.fetch('SELECT id FROM accounts WHERE $1 = ANY(files)', file_id)
            file = await self.conn.fetch('SELECT filename FROM files WHERE id=$1', file_id)
            host = resp[0]['id']
            file = file[0]['filename']
            if file_id in self.files:
                socket = self.sockets.get(host)
                if socket:
                    return {'type': 'file_resp', 'host': f"http://{socket._req.remote}:{str(self.ports[host])}", 'filename': file}
                else:
                    return {'type': 'error', 'error': 'host not connected to the network'}
            else:
                return {'type': 'error', 'error': 'host is not sharing that file currently'}
        except Exception as e:
            print(e)
            return {'type': 'error', 'error': 'failed to get file'}


    async def register_files(self, ws, msg, data):
        try:
            ids: Dict[str, int] = {}
            for file in data['files'].values():
                if file == None:
                    name = self.get_by_val(data['files'], file)
                    id = int(secrets.choice(range(10000000, 99999999)))
                    while await self.is_taken('files', 'id', id) == True:
                        id = int(secrets.choice(range(10000000, 99999999)))
                    await self.conn.execute('INSERT INTO files (filename, id, owner) VALUES ($1, $2, $3)', name, id, ws['user'])
                    await self.conn.execute('UPDATE accounts SET files=array_append(files, $1) WHERE id=$2', id, ws['user'])
                    ids[name] = id
                else:
                    file = int(file)
                    self.files[file] = ws['user']
            if ids != {}:
                return {'type': 'file_reg_resp', 'files': ids}
            else:
                return {'type': 'file_reg_success'}
        except Exception as e:
            print(e)
            return {'type': 'error', 'error': 'failed to register files'}


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
                    if data['type'] == 'file_reg':
                        resp = await app.register_files(ws, msg, data)
                        return await ws.send_json(resp)
                else:
                    await ws.send_json({'type': 'error', 'error': 'endpoint not found'})

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception %s' % ws.exception())

        for key, value in dict(app.files).items():
            if value == ws['user']:
                del app.files[key]
        app.sockets.pop(ws['user'])
        print('disconnected')

    
    @routes.get('/file')
    async def file_listen(request):
        resp = await app.get_file(request.rel_url.query['file_id'])
        return web.json_response(resp)


if __name__ == "__main__":
    app = PyFileShareServer()
    app.run()