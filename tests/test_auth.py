import unittest
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret'

from app import app, db
from app.models import User

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_register_login_flow(self):
        # 1. Register a new student
        resp = self.client.post('/register', data={
            'username': 'teststudent',
            'email': 'student@example.com',
            'password': 'studentpassword',
            'confirm_password': 'studentpassword',
            'role': 'student'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        
        # Verify student exists in db
        user = User.query.filter_by(username='teststudent').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'student@example.com')
        self.assertEqual(user.role, 'student')
        
        # 2. Login
        resp = self.client.post('/login', data={
            'username': 'teststudent',
            'password': 'studentpassword'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        
        # Logout
        resp = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
