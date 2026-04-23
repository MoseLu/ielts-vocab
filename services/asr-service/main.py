from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env
from platform_sdk.service_app import create_service_shell_app
from platform_sdk.asr_runtime import (
    ASRServiceError,
    get_dashscope_api_key,
    transcribe_uploaded_audio,
)

load_split_service_env(service_name='asr-service')

def _dashscope_api_key_configured() -> bool:
    return bool(get_dashscope_api_key())


class UploadedAudioAdapter:
    def __init__(self, upload: UploadFile):
        self._upload = upload
        self.content_type = upload.content_type or ''

    def save(self, destination: str) -> None:
        self._upload.file.seek(0)
        with open(destination, 'wb') as output:
            shutil.copyfileobj(self._upload.file, output)


app = create_service_shell_app(
    service_name='asr-service',
    version='0.1.0',
    readiness_checks={'dashscope_api_key': _dashscope_api_key_configured},
    extra_health={'speech_namespace': '/speech'},
)


async def transcribe_speech(request: Request):
    form = await request.form()
    audio = form.get('audio')
    if not isinstance(audio, UploadFile):
        return JSONResponse(status_code=400, content={'error': '未收到音频文件'})
    try:
        text = transcribe_uploaded_audio(UploadedAudioAdapter(audio))
        return JSONResponse(content={'text': text})
    except ASRServiceError as error:
        return JSONResponse(
            status_code=error.status_code,
            content={'error': f'识别失败: {error}'},
        )


app.add_route('/v1/speech/transcribe', transcribe_speech, methods=['POST'])


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('ASR_SERVICE_PORT', '8106')))
