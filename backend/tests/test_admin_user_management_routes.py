from models import User, db


def register_user(client, username, password='password123'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    assert response.status_code == 201


def login_user(client, username, password='password123'):
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def test_admin_set_admin_updates_target_user(client, app):
    register_user(client, 'admin-manage-admin')
    register_user(client, 'admin-manage-target')

    with app.app_context():
        admin = User.query.filter_by(username='admin-manage-admin').first()
        target = User.query.filter_by(username='admin-manage-target').first()
        assert admin is not None and target is not None
        admin.is_admin = True
        target_id = target.id
        db.session.commit()

    login_user(client, 'admin-manage-admin')
    response = client.post(f'/api/admin/users/{target_id}/set-admin', json={'is_admin': True})

    assert response.status_code == 200
    assert response.get_json()['user']['is_admin'] is True

    with app.app_context():
        refreshed = User.query.get(target_id)
        assert refreshed is not None
        assert refreshed.is_admin is True


def test_admin_set_admin_rejects_self_update(client, app):
    register_user(client, 'admin-manage-self')

    with app.app_context():
        admin = User.query.filter_by(username='admin-manage-self').first()
        assert admin is not None
        admin.is_admin = True
        admin_id = admin.id
        db.session.commit()

    login_user(client, 'admin-manage-self')
    response = client.post(f'/api/admin/users/{admin_id}/set-admin', json={'is_admin': False})

    assert response.status_code == 400
    assert response.get_json()['error'] == '不能修改自己的管理员状态'
