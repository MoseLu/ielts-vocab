from __future__ import annotations

from platform_sdk.feature_wish_image_storage import store_feature_wish_image
from services import feature_wish_repository


MAX_IMAGES_PER_WISH = 3


def _normalize_text(value, *, max_length: int) -> str:
    return ' '.join(str(value or '').split())[:max_length]


def _wish_payload(wish, *, viewer_user_id: int) -> dict:
    return wish.to_dict(viewer_user_id=viewer_user_id)


def list_feature_wishes_response(current_user, args) -> tuple[dict, int]:
    search = _normalize_text(args.get('search', ''), max_length=120)
    rows, total = feature_wish_repository.list_wishes(
        viewer_user_id=int(current_user.id),
        is_admin=bool(current_user.is_admin),
        search=search,
    )
    return {
        'items': [_wish_payload(row, viewer_user_id=int(current_user.id)) for row in rows],
        'total': total,
    }, 200


def _read_body(payload: dict | None, form) -> tuple[str, str]:
    source = payload or form or {}
    title = _normalize_text(source.get('title'), max_length=120)
    content = _normalize_text(source.get('content'), max_length=1200)
    return title, content


def _validate_wish_text(title: str, content: str) -> tuple[dict, int] | None:
    if not title:
        return {'error': '愿望名不能为空'}, 400
    if not content:
        return {'error': '愿望内容不能为空'}, 400
    return None


def _store_uploaded_images(*, current_user, wish_id: int, files) -> tuple[list[dict], tuple[dict, int] | None]:
    uploads = list(files.getlist('images')) if files else []
    stored_images: list[dict] = []
    for upload in uploads:
        filename = getattr(upload, 'filename', '') or 'image'
        content_type = getattr(upload, 'content_type', '') or ''
        try:
            stored_images.append(store_feature_wish_image(
                user_id=int(current_user.id),
                wish_id=wish_id,
                filename=filename,
                body=upload.read(),
                content_type=content_type,
            ))
        except ValueError as exc:
            return [], {'error': str(exc)}, 400
        except RuntimeError as exc:
            return [], {'error': str(exc)}, 503
    return stored_images, None


def _image_count_error(files) -> tuple[dict, int] | None:
    uploads = list(files.getlist('images')) if files else []
    if len(uploads) > MAX_IMAGES_PER_WISH:
        return {'error': '每个愿望最多上传三张图片'}, 400
    return None


def create_feature_wish_response(current_user, payload: dict | None, form, files) -> tuple[dict, int]:
    title, content = _read_body(payload, form)
    error = _validate_wish_text(title, content)
    if error is not None:
        return error
    error = _image_count_error(files)
    if error is not None:
        return error
    wish = feature_wish_repository.create_wish(
        user_id=int(current_user.id),
        username=_normalize_text(current_user.username, max_length=100) or f'user-{current_user.id}',
        title=title,
        content=content,
    )
    stored_images, image_error = _store_uploaded_images(current_user=current_user, wish_id=wish.id, files=files)
    if image_error is not None:
        return image_error
    if stored_images:
        wish = feature_wish_repository.replace_images(wish=wish, images=stored_images)
    return {'message': '愿望已提交', 'wish': _wish_payload(wish, viewer_user_id=int(current_user.id))}, 201


def update_feature_wish_response(current_user, wish_id: int, payload: dict | None, form, files) -> tuple[dict, int]:
    wish = feature_wish_repository.get_wish(wish_id)
    if wish is None:
        return {'error': '愿望不存在'}, 404
    if int(wish.user_id) != int(current_user.id):
        return {'error': '只能编辑自己的愿望'}, 403
    title, content = _read_body(payload, form)
    error = _validate_wish_text(title, content)
    if error is not None:
        return error
    error = _image_count_error(files)
    if error is not None:
        return error
    wish = feature_wish_repository.update_wish(wish=wish, title=title, content=content)
    if files and files.getlist('images'):
        stored_images, image_error = _store_uploaded_images(current_user=current_user, wish_id=wish.id, files=files)
        if image_error is not None:
            return image_error
        wish = feature_wish_repository.replace_images(wish=wish, images=stored_images)
    return {'message': '愿望已更新', 'wish': _wish_payload(wish, viewer_user_id=int(current_user.id))}, 200
