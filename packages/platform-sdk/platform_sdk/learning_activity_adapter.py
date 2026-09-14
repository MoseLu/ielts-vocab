def delete_learning_activity_scope(*args, **kwargs):
    from services.learning_activity_service import delete_learning_activity_scope as delete_scope

    return delete_scope(*args, **kwargs)


__all__ = ['delete_learning_activity_scope']
