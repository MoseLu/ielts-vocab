from __future__ import annotations

import json

from service_models.admin_ops_models import FeatureWish, FeatureWishImage, db


def create_wish(
    *,
    user_id: int,
    username: str,
    title: str,
    content: str,
) -> FeatureWish:
    wish = FeatureWish(
        user_id=user_id,
        username_snapshot=username,
        title=title,
        content=content,
    )
    db.session.add(wish)
    db.session.commit()
    return wish


def get_wish(wish_id: int) -> FeatureWish | None:
    return FeatureWish.query.filter_by(id=wish_id).first()


def list_wishes(*, viewer_user_id: int, is_admin: bool, search: str = '') -> tuple[list[FeatureWish], int]:
    query = FeatureWish.query
    if not is_admin:
        query = query.filter(FeatureWish.user_id == viewer_user_id)
    if search:
        query = query.filter(FeatureWish.title.ilike(f'%{search}%'))
    total = query.count()
    rows = (
        query
        .order_by(FeatureWish.created_at.desc(), FeatureWish.id.desc())
        .all()
    )
    return rows, total


def update_wish(*, wish: FeatureWish, title: str, content: str) -> FeatureWish:
    wish.title = title
    wish.content = content
    db.session.commit()
    return wish


def replace_images(*, wish: FeatureWish, images: list[dict]) -> FeatureWish:
    wish.images = []
    db.session.flush()
    for index, image in enumerate(images):
        wish.images.append(FeatureWishImage(
            sort_order=index,
            original_filename=image['original_filename'],
            content_type=image['content_type'],
            byte_length=image['byte_length'],
            thumbnail_object_key=image['thumbnail_object_key'],
            thumbnail_url=image['thumbnail_url'],
            full_object_key=image['full_object_key'],
            full_url=image['full_url'],
            metadata_json=json.dumps(image.get('metadata') or {}, ensure_ascii=False),
        ))
    db.session.commit()
    return wish
