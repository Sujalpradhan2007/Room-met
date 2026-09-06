import uuid

import app as room_app


def get_client():
    client = room_app.app.test_client()
    client.application.config['TESTING'] = True
    return client


def test_room_delete_only_for_host():
    host_client = get_client()
    member_client = get_client()

    host_email = f"host_{uuid.uuid4().hex[:8]}@example.com"
    member_email = f"member_{uuid.uuid4().hex[:8]}@example.com"

    host_register = host_client.post('/api/register', json={
        'username': 'Host User',
        'email': host_email,
        'password': 'secret123'
    })
    assert host_register.status_code == 200, host_register.get_data(as_text=True)

    room_code = f"R{uuid.uuid4().hex[:5].upper()}"
    room_create = host_client.post('/api/room/create', json={
        'room_name': 'Test Room',
        'room_code': room_code
    })
    assert room_create.status_code == 200, room_create.get_data(as_text=True)

    member_register = member_client.post('/api/register', json={
        'username': 'Member User',
        'email': member_email,
        'password': 'secret123'
    })
    assert member_register.status_code == 200, member_register.get_data(as_text=True)

    join = member_client.post('/api/room/join', json={'room_code': room_code})
    assert join.status_code == 200, join.get_data(as_text=True)

    host_delete = host_client.delete('/api/room/delete')
    assert host_delete.status_code == 200, host_delete.get_data(as_text=True)

    conn = room_app.get_db()
    deleted_room = conn.execute('SELECT room_code FROM rooms WHERE room_code = ?', (room_code,)).fetchone()
    member_user = conn.execute('SELECT room_code FROM users WHERE email = ?', (member_email,)).fetchone()
    conn.close()

    assert deleted_room is None
    assert member_user['room_code'] is None

    member_delete = member_client.delete('/api/room/delete')
    assert member_delete.status_code == 403


def test_host_can_remove_member_from_room():
    host_client = get_client()
    member_client = get_client()

    host_email = f"host_remove_{uuid.uuid4().hex[:8]}@example.com"
    member_email = f"member_remove_{uuid.uuid4().hex[:8]}@example.com"

    host_register = host_client.post('/api/register', json={
        'username': 'Host Remove',
        'email': host_email,
        'password': 'secret123'
    })
    assert host_register.status_code == 200, host_register.get_data(as_text=True)

    room_code = f"R{uuid.uuid4().hex[:5].upper()}"
    create_room = host_client.post('/api/room/create', json={
        'room_name': 'Remove Member Room',
        'room_code': room_code
    })
    assert create_room.status_code == 200, create_room.get_data(as_text=True)

    member_register = member_client.post('/api/register', json={
        'username': 'Member Remove',
        'email': member_email,
        'password': 'secret123'
    })
    assert member_register.status_code == 200, member_register.get_data(as_text=True)

    join = member_client.post('/api/room/join', json={'room_code': room_code})
    assert join.status_code == 200, join.get_data(as_text=True)

    member = room_app.get_db().execute('SELECT id FROM users WHERE email = ?', (member_email,)).fetchone()
    remove_member = host_client.post('/api/room/member/remove', json={'member_id': member['id']})
    assert remove_member.status_code == 200, remove_member.get_data(as_text=True)

    conn = room_app.get_db()
    user_after_remove = conn.execute('SELECT room_code FROM users WHERE email = ?', (member_email,)).fetchone()
    conn.close()
    assert user_after_remove['room_code'] is None


def test_room_creation_requires_login_in_english():
    client = get_client()

    response = client.post('/api/room/create', json={'room_name': 'Guest Room'})

    assert response.status_code == 401
    assert response.get_json()['error'] == 'Please login first!'


if __name__ == '__main__':
    test_room_delete_only_for_host()
    test_host_can_remove_member_from_room()
    test_room_creation_requires_login_in_english()
    print('room delete test passed')
