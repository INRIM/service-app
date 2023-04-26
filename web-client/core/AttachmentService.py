# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import aiofile
import httpx
import logging
import ujson
import json
from fastapi.responses import (
    RedirectResponse, FileResponse, StreamingResponse, JSONResponse
)
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .ContentService import *
from .AuthService import AuthContentService
from fastapi.concurrency import run_in_threadpool
import shutil
from io import BytesIO
import aiofiles
from aiofiles.os import wrap
import asyncio
from aioclamd import ClamdAsyncClient
import logging
import os

logger = logging.getLogger(__name__)

movefile = wrap(shutil.move)
copyfile = wrap(shutil.copyfile)


class AttachmentService(AuthContentService):

    @classmethod
    def create(cls, gateway, remote_data):
        self = AttachmentService()
        self.init(gateway, remote_data)
        return self

    def init(self, gateway, remote_data):
        super().init(gateway, remote_data)
        self.clamd = ClamdAsyncClient("av", 3310)

    async def check_and_save_attachment(self):
        if self.attachments_to_save:
            logger.info("save attachment")
            for attachment in self.attachments_to_save:
                await self.move_attachment(attachment)

    async def handle_attachment(
            self, components_files, submit_data, stored_data):
        logger.info(f"handle form attachment")

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
                    for data_file in list_files:
                        if (
                                data_file and
                                not isinstance(data_file, dict)
                                and data_file.filename
                        ):
                            file_data = await self.save_attachment(
                                submit_data.get('data_model'), data_file
                            )
                            self.attachments_to_save.append(file_data)
                            res_data[component.key].append(file_data)
                        elif (
                                data_file and
                                isinstance(data_file, dict)

                        ):
                            res_data[component.key].append(data_file)

                    # if stored_data.get(component.key) and isinstance(
                    #         stored_data.get(component.key), dict):
                    #     res_data[component.key] += stored_data.get(
                    #         component.key)
        return res_data.copy()

    async def save_attachment(
            self, data_model, spooled_file, file_name_prefix="") -> dict:
        logger.info(
            f"check and save on tmp spooled_file: {spooled_file.filename}")

        rec_name = str(uuid.uuid4())
        file_path = await self.create_folder(
            "/tmp", data_model, sub_folder=rec_name)
        file_name = spooled_file.filename
        if file_name_prefix:
            file_name = f"{file_name_prefix}_{spooled_file.filename}"
        out_file_path = f"{file_path}/{file_name}"
        output = BytesIO()

        async with aiofiles.open(out_file_path, 'wb') as out_file:
            while content := await spooled_file.read(1024):  # async read chunk
                output.write(content)
                await out_file.write(content)

        output.seek(0)
        scan_virus = await self.clamd.instream(output)
        logger.info(f"scan_virus --> {scan_virus}")
        if scan_virus.get("stream", {})[0] == "OK":
            row = {
                "filename": file_name,
                "content_type": spooled_file.content_type,
                "file_path": f"{data_model}/{rec_name}",
                "url": f"/{data_model}/{rec_name}/{file_name}",
                "key": f"{rec_name}"
            }
        else:
            detect = scan_virus.get("stream", {})[1]
            await AsyncPath(out_file_path).remove(missing_ok=True)
            logger.error(
                f"Virus detected  in file "
                f"removed {file_name} --> {detect}"
            )
            row = {
                "filename": f"{file_name} virus detect {detect}",
                "content_type": "",
                "file_path": f"",
                "url": f"/dashboard",
                "key": f"{rec_name}"
            }
            self.attachments_attacks.append(row)

        return row

    async def move_attachment(self, attachment) -> str:
        logger.info(f"save {attachment['filename']}")
        form_upload = f"/tmp/{attachment['file_path']}/{attachment['filename']}"
        to_upload_folder = f"{self.local_settings.upload_folder}/{attachment['file_path']}"
        to_upload_file = f"{to_upload_folder}/{attachment['filename']}"
        await AsyncPath(to_upload_folder).mkdir(parents=True, exist_ok=True)
        await movefile(form_upload, to_upload_file)
        return to_upload_file

    async def copy_attachment(self, attachment, dest) -> dict:

        logger.info(f"copy {attachment['filename']}")
        fsrc = f"{self.local_settings.upload_folder}/{attachment['file_path']}/{attachment['filename']}"
        dest_folder = f"{self.local_settings.upload_folder}/{dest}"
        dest_f = f"{dest_folder}/{attachment['key']}/{attachment['filename']}"
        await AsyncPath(dest_folder).mkdir(parents=True, exist_ok=True)
        # prevent [Errno 18] Invalid cross-device link of AsyncPath
        await copyfile(fsrc, dest_f)
        row = {
            "filename": attachment['filename'],
            "content_type": attachment['content_type'],
            "file_path": f"{dest}/{attachment['key']}",
            "url": f"/{dest}/{attachment['key']}/{attachment['filename']}",
            "key": f"{attachment['key']}"
        }
        return row

    async def move_attachment_to_trash(self, attachment) -> str:
        logger.info(
            f"move to trash {attachment['filename']} path {attachment['file_path']}")
        form_upload = f"{self.local_settings.upload_folder}/{attachment['file_path']}/{attachment['filename']}"
        trash_folder = f"{self.local_settings.upload_folder}/trash/{attachment['file_path']}"
        to_trash_file = f"{trash_folder}/{attachment['filename']}"
        await AsyncPath(trash_folder).mkdir(parents=True, exist_ok=True)
        await movefile(form_upload, to_trash_file)
        logger.info(f"moved to trash {to_trash_file}")
        return to_trash_file

    async def restore_attachment_from_trash(self, attachment) -> str:
        logger.info(f"restore from trash {attachment['filename']}")
        form_trash = f"{self.local_settings.upload_folder}" \
                     f"/trash/{attachment['file_path']}"
        upload_folder = f"{self.local_settings.upload_folder}/{attachment['file_path']}"
        path_file = f"{upload_folder}/{attachment['filename']}"
        await AsyncPath(upload_folder).mkdir(parents=True, exist_ok=True)
        await movefile(form_upload, path_file)
        return path_file

    async def remove_attachment(self, attachment) -> bool:
        logger.info(f"remove from trash {attachment['filename']}")
        to_upload_folder = f"{self.local_settings.upload_folder}" \
                           f"/trash/{attachment['file_path']}"
        await AsyncPath(to_upload_folder).remove(missing_ok=True)
        return True

    async def download_attachment(self, data_model, uuidpath,
                                  file_name) -> StreamingResponse:
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
        return StreamingResponse(output, headers=headers,
                                 media_type='application/octet-stream')

    async def copy_attachments(
            self, model, rec_name, field, dest) -> JSONResponse:

        data = self.content.get("data", {})
        attachments = []
        res = {"status": "error", "data": attachments, "msg": "no data"}
        if data:
            if data.get(field):
                for attachment in data.get(field):
                    dat = await self.copy_attachment(attachment, dest)
                    attachments.append(dat.copy())
                res['status'] = "ok"
                res['data'] = attachments
                res['msg'] = f"{len(attachments)} files copies done"
            else:
                res['msg'] = f"no field {field} form {model} record {rec_name}"
        return await self.gateway.complete_json_response(res)

    async def attachment_to_trash(self, model, rec_name, data) -> Any:
        url = f"/attachment/trash/{model}/{rec_name}"
        res = await self.gateway.post_remote_object(url, data=data)
        if "error" in res.get("status", ""):
            return await self.form_post_complete_response(res, res)
        await self.move_attachment_to_trash(data)
        return res

    async def attachment_unlink(self, model, rec_name, data) -> Any:
        url = f"/attachment/unlink/{model}/{rec_name}"
        res = await self.gateway.post_remote_object(url, data=data)
        if "error" in res.get("status", ""):
            return await self.form_post_complete_response(res, res)
        return res
