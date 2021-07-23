# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import httpx
import logging
import ujson
import json
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .ContentService import *
from .AuthService import AuthContentService
import shutil
from io import BytesIO
import aiofiles
from aiofiles.os import wrap

import logging

logger = logging.getLogger(__name__)

movefile = wrap(shutil.move)


class AttachmentService(AuthContentService):

    @classmethod
    def create(cls, gateway, remote_data):
        self = AttachmentService()
        self.init(gateway, remote_data)
        return self

    async def handle_attachment(self, components_files, submit_data, stored_data):
        logger.info(f"")
        logger.info(f"handle form attachment {submit_data}")
        """ file node is list of dict """
        res_data = submit_data.copy()
        if components_files:
            for component in components_files:
                if component.key in res_data:
                    list_files = []
                    res_data[component.key] = []
                    if not isinstance(submit_data[component.key], list):
                        list_files.append(submit_data[component.key])
                    else:
                        list_files = submit_data[component.key]
                    # logger.info(f"handle form list files  {list_files}")
                    for data_file in list_files:
                        if data_file and data_file.filename:
                            file_data = await self.save_attachment(
                                submit_data.get('data_model'), data_file
                            )
                            self.attachments_to_save.append(file_data)
                            res_data[component.key].append(file_data)
                    if stored_data.get(component.key):
                        res_data[component.key] += stored_data.get(component.key)
        return res_data.copy()

    async def save_attachment(self, data_model, spooled_file, file_name_prefix=""):
        logger.info(f"save on tmp spooled_file: {spooled_file.filename}")
        rec_name = str(uuid.uuid4())
        file_path = await self.create_folder(
            "/tmp", data_model, sub_folder=rec_name)
        file_name = spooled_file.filename
        if file_name_prefix:
            file_name = f"{file_name_prefix}_{spooled_file.filename}"
        out_file_path = f"{file_path}/{file_name}"
        async with aiofiles.open(out_file_path, 'wb') as out_file:
            while content := await spooled_file.read(1024):  # async read chunk
                await out_file.write(content)

        row = {
            "filename": file_name,
            "content_type": spooled_file.content_type,
            "file_path": f"{data_model}/{rec_name}",
            "url": f"/{data_model}/{rec_name}/{file_name}",
            "key": f"{rec_name}"
        }
        return row

    async def move_attachment(self, attachment):
        logger.info(f"save {attachment['filename']}")
        form_upload = f"/tmp/{attachment['file_path']}/{attachment['filename']}"
        to_upload_folder = f"{self.local_settings.upload_folder}/{attachment['file_path']}"
        to_upload_file = f"{to_upload_folder}/{attachment['filename']}"
        await AsyncPath(to_upload_folder).mkdir(parents=True, exist_ok=True)
        # prevent [Errno 18] Invalid cross-device link of AsyncPath
        await movefile(form_upload, to_upload_file)
        return to_upload_file

    async def move_attachment_to_trash(self, attachment):
        logger.info(f"move to trash {attachment['filename']}")
        form_upload = f"{self.local_settings.upload_folder}/{attachment['file_path']}/{attachment['filename']}"
        trash_folder = f"{self.local_settings.upload_folder}/trash/{attachment['file_path']}"
        to_trash_file = f"{trash_folder}/{attachment['filename']}"
        await AsyncPath(trash_folder).mkdir(parents=True, exist_ok=True)
        await movefile(form_upload, to_trash_file)
        return to_trash_file

    async def restore_attachment_from_trash(self, attachment):
        logger.info(f"restore from trash {attachment['filename']}")
        form_trash = f"{self.local_settings.upload_folder}/trash/{attachment['file_path']}"
        upload_folder = f"{self.local_settings.upload_folder}/{attachment['file_path']}"
        path_file = f"{upload_folder}/{attachment['filename']}"
        await AsyncPath(upload_folder).mkdir(parents=True, exist_ok=True)
        await movefile(form_upload, path_file)
        return path_file

    async def remove_attachment(self, attachment):
        logger.info(f"remove from trash {attachment['filename']}")
        to_upload_folder = f"{self.local_settings.upload_folder}/trash/{attachment['file_path']}"
        # to_upload_file = f"{to_upload_folder}/{attachment['filename']}"
        await AsyncPath(to_upload_folder).remove(missing_ok=True)
        return True

    async def download_attachment(self, data_model, uuidpath, file_name):
        base_upload = self.local_settings.upload_folder
        attachmnet = f"{base_upload}/{data_model}/{uuidpath}/{file_name}"
        output = BytesIO()
        async with aiofiles.open(attachmnet, 'rb') as in_file:
            while content := await in_file.read(1024):  # async read chunk
                output.write(content)  # async write chunk
        output.seek(0)
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
        }
        logger.info(f"Download attachment Done: {file_name}")
        return StreamingResponse(output, headers=headers, media_type='application/octet-stream')

    async def attachment_to_trash(self, model, rec_name, data):
        url = f"/attachment/trash/{model}/{rec_name}"
        res = await self.gateway.post_remote_object(url, data=data)
        if "error" in res.get("status", ""):
            return await self.form_post_complete_response(res, res)
        await self.move_attachment_to_trash(data)
        return res
