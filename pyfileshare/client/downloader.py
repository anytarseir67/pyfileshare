import aiohttp
import asyncio
import json
import aiofiles
import os


with open('config.json', 'r') as f:
    config = json.load(f)


class PYFSDownloader():
    def __init__(self, file: str, _dir: str, filename: str) -> None:
        self.file: int = file
        self._dir: str = _dir
        self.filename = filename or None


    def run(self) -> None:
        asyncio.run(self.main())


    async def main(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config['server']}/file?file_id={self.file}") as resp:
                data = await resp.json()
            if data['type'] == 'file_resp':
                async with session.get(f"{data['host']}/file?id={self.file}") as file:
                    raw = await file.read()
                dir = self._dir or os.getcwd()
                filename = self.filename or data['filename']
                async with aiofiles.open(f"{dir}/{filename}", 'wb') as f:
                    await f.write(raw)
            else:
                print(data)


def main():
    while True:
        file = input('file id:\n')
        try:
            file = int(file)
        except:
            continue
        if type(file) == int:
            print('')

        filename = input('file name:\n')
        if filename != "":
            print('')

        _dir = input('save location:\n')
        downloader = PYFSDownloader(file, _dir, filename)
        downloader.run()


if __name__ == '__main__':
    main()