from __future__ import annotations

from services import auth_repository


def set_internal_identity_admin_response(
    current_admin_id: int,
    target_user_id: int,
    data: dict | None,
) -> tuple[dict, int]:
    if current_admin_id == target_user_id:
        return {'error': '不能修改自己的管理员状态'}, 400

    user = auth_repository.get_user(target_user_id)
    if user is None:
        return {'error': '用户不存在'}, 404

    user.is_admin = bool((data or {}).get('is_admin', False))
    auth_repository.commit_user(user)
    return {'message': '已更新', 'user': user.to_dict()}, 200
