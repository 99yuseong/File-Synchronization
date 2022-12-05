import os
import time
import json
import asyncio
# from main import app
from pathlib import Path
try:
    import aiohttp
    import aiofiles
except ModuleNotFoundError as e:
    print("Module \'aiohttp or aiofiles\' is not found")
    os.system("python -m pip install aiohttp")
    os.system("python -m pip install aiofiles")
    import aiohttp
    import aiofiles
    
class API():
    def __init__(self, app, config, logger):
        self.app = app
        self.config = config
        self.logger = logger
        self.server_ip = config.getConfig("CLIENT_CONFIG", "server_ip")
        self.port = config.getConfig("CLIENT_CONFIG", "port")
        self.target = config.getConfig("CLIENT_CONFIG", "target_path")
        self.url = "%s:%s" % (self.server_ip, self.port)

    def _url(self, url=""):
        return self.url + url
    
    async def getFileList(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self._url("/list")) as res:
                # try:
                files = await res.json()
                return files
                # except:
                    # self.logger.print_log("SERVER IS NOT READY")

    async def createFile(self, file):
        fileJson = { "id": str(file.id), "name": file.name, "path": str(file.sync_path.as_posix()), "md5": file.md5 }
        async with aiohttp.ClientSession() as session:
            async with session.post(self._url("/"), json=fileJson) as res:
                self.logger.print_log_server("CREATE FILE", "RES HTTP/1.1 %s" % res.status, await res.text())
    
    async def modifyFile(self, file):
        fileJson = { "id": str(file.id), "name": file.name, "path": str(file.sync_path.as_posix()), "md5": file.md5 }
        async with aiohttp.ClientSession() as session:
            async with session.put(self._url("/%s" % str(file.id)), json=fileJson) as res:
                self.logger.print_log_server("MODIFIY FILE", "RES HTTP/1.1 %s" % res.status, await res.json())
            
    async def deleteFile(self, file):
        async with aiohttp.ClientSession() as session:
            async with session.delete(self._url("/%s" % str(file.id))) as res:
                self.logger.print_log_server("DELETE FILE", "RES HTTP/1.1 %s" % res.status, await res.text())
                
    async def uploadFile(self, file):
        file_to_send = aiohttp.FormData()
        file_to_send.add_field('file', open(file.real_path, 'rb'), filename="%s.%s" % (str(file.id),file.name.split(".")[-1]), content_type="multipart/form-data")
        async with aiohttp.ClientSession() as session:
            async with session.post(self._url("/file"), data=file_to_send) as res:
                self.logger.print_log_server("UPLOAD FILE", "RES HTTP/1.1 %s" % res.status, await res.text())
                
    async def downloadFile(self, file_id):
        async with aiohttp.ClientSession() as session:
            url = None
            async with session.get(self._url("/download/file/%s" % str(file_id))) as res:
                f = await res.json()
                url = "%s/static/%s.%s" % (self.url, f["id"], f["name"].split(".")[-1])
            async with session.get(url) as res:
                    if res.status == 200:
                        tmp_path = Path(self.target) / f["path"][5:]
                        if not tmp_path.parent.is_dir():
                            tmp_path.parent.mkdir()
                        _f = await aiofiles.open(str(tmp_path.resolve()), mode='wb')
                        await _f.write(await res.read())
                        await _f.close()
                
    async def connectSocket(self, fileChecker):
        async with aiohttp.ClientSession() as session:     
            async with session.ws_connect(self._url("/ws")) as ws:
                    while True:
                        # 5초마다 오는 전체 파일 확인
                        try:
                            filelist = await ws.receive_json()
                            # print("----socket comming DATA----")
                            # print(filelist)
                            await fileChecker.socketDataCheck(json.loads(filelist))
                        except TypeError as e:
                            print(e)
                            print("SOCKET DISCONNECTED")
                            self.app.socketError = True
                            await ws.close()
                            break
                        
                        
            