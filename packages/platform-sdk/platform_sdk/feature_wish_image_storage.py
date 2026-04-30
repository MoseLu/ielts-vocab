from __future__ import annotations

import os
import uuid
from io import BytesIO

from platform_sdk.storage.aliyun_oss import build_service_object_key, put_object_bytes, sanitize_segment


ALLOWED_IMAGE_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
    'image/gif': 'gif',
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_PREFIX = 'projects/ielts-vocab/feature-wishes'
THUMBNAIL_MAX_SIZE = (480, 480)


def _extension(content_type: str, filename: str) -> str:
    normalized_type = (content_type or '').strip().lower()
    if normalized_type in ALLOWED_IMAGE_TYPES:
        return ALLOWED_IMAGE_TYPES[normalized_type]
    suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return suffix if suffix in {'jpg', 'jpeg', 'png', 'webp', 'gif'} else 'bin'


def _thumbnail_body(body: bytes, content_type: str) -> bytes:
    try:
        from PIL import Image
    except Exception:
        return body

    output = BytesIO()
    try:
        with Image.open(BytesIO(body)) as image:
            image.thumbnail(THUMBNAIL_MAX_SIZE)
            save_format = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/webp': 'WEBP',
                'image/gif': 'GIF',
            }.get(content_type, 'PNG')
            image.save(output, format=save_format)
    except Exception:
        return body
    return output.getvalue() or body


def store_feature_wish_image(
    *,
    user_id: int,
    wish_id: int,
    filename: str,
    body: bytes,
    content_type: str,
) -> dict:
    normalized_type = (content_type or '').strip().lower()
    if normalized_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError('仅支持 JPG、PNG、WEBP、GIF 图片')
    if not body:
        raise ValueError('图片内容为空')
    if len(body) > MAX_IMAGE_BYTES:
        raise ValueError('单张图片不能超过 5MB')

    ext = _extension(normalized_type, filename)
    token = uuid.uuid4().hex[:16]
    prefix = (os.environ.get('FEATURE_WISH_OSS_PREFIX') or DEFAULT_PREFIX).strip()
    segments = (f'user-{int(user_id)}', f'wish-{int(wish_id)}')
    thumb_key = build_service_object_key(
        service_name='admin-ops-service',
        prefix=prefix,
        segments=segments,
        file_name=f'thumb-{token}.{ext}',
    )
    full_key = build_service_object_key(
        service_name='admin-ops-service',
        prefix=prefix,
        segments=segments,
        file_name=f'full-{token}.{ext}',
    )
    thumb_body = _thumbnail_body(body, normalized_type)
    thumb = put_object_bytes(object_key=thumb_key, body=thumb_body, content_type=normalized_type)
    full = put_object_bytes(object_key=full_key, body=body, content_type=normalized_type)
    if thumb is None or full is None:
        raise RuntimeError('OSS 图片上传失败')
    return {
        'original_filename': sanitize_segment(filename.rsplit('.', 1)[0] if filename else 'image'),
        'content_type': normalized_type,
        'byte_length': len(body),
        'thumbnail_object_key': thumb.object_key,
        'thumbnail_url': thumb.signed_url,
        'full_object_key': full.object_key,
        'full_url': full.signed_url,
        'metadata': {'variant_strategy': 'backend-thumb-and-full'},
    }
