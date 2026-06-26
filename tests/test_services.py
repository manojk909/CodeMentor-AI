import unittest
import os
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret'

from app import app, db
from app.models import User, ForumPost, ForumAnswer, StudyGroup, StudyGroupMember, PlatformStats
from app.services.doubt_forum_service import DoubtForumService
from app.services.study_group_matcher import StudyGroupMatcher

class TestDoubtForumService(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        self.user = User(username="test_forum", email="forum@example.com")
        self.user.set_password("password")
        db.session.add(self.user)
        db.session.commit()
        
        self.service = DoubtForumService()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_create_post(self):
        post = self.service.create_post(
            title="How to learn recursion?",
            content="I am trying to learn python recursion, any tips?",
            author_id=self.user.id,
            category="Algorithms"
        )
        self.assertEqual(post.title, "How to learn recursion?")
        self.assertEqual(post.category, "Algorithms")
        self.assertIn("python", post.tags.lower())
        self.assertIn("recursion", post.tags.lower())

    def test_create_answer_and_accept(self):
        post = self.service.create_post(
            title="How to learn recursion?",
            content="I am trying to learn python recursion, any tips?",
            author_id=self.user.id
        )
        answer = self.service.create_answer(
            post_id=post.id,
            content="Recursion requires a base case and a recursive case.",
            author_id=self.user.id
        )
        self.assertEqual(answer.post_id, post.id)
        self.assertEqual(answer.content, "Recursion requires a base case and a recursive case.")
        
        # Accept answer
        success = self.service.mark_answer_accepted(answer.id, self.user.id)
        self.assertTrue(success)
        self.assertTrue(answer.is_accepted)
        self.assertTrue(post.is_solved)

    def test_vote_post_and_answer(self):
        post = self.service.create_post(
            title="How to learn recursion?",
            content="I am trying to learn python recursion, any tips?",
            author_id=self.user.id
        )
        answer = self.service.create_answer(
            post_id=post.id,
            content="Recursion requires a base case and a recursive case.",
            author_id=self.user.id
        )
        
        # Vote post
        success = self.service.vote_post(post.id, self.user.id, "up")
        self.assertTrue(success)
        self.assertEqual(post.votes, 1)
        
        # Vote answer
        success = self.service.vote_answer(answer.id, self.user.id, "down")
        self.assertTrue(success)
        self.assertEqual(answer.votes, -1)


class TestStudyGroupMatcher(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        self.user = User(
            username="test_matcher", 
            email="matcher@example.com",
            learning_goals="Learn System Design",
            target_companies="Netflix"
        )
        self.user.set_password("password")
        db.session.add(self.user)
        db.session.commit()
        
        self.matcher = StudyGroupMatcher()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_assess_user_skill_level_default(self):
        skill = self.matcher._assess_user_skill_level(self.user.id)
        self.assertEqual(skill, "Beginner")

    def test_assess_user_skill_level_advanced(self):
        stats = PlatformStats(
            user_id=self.user.id,
            platform="leetcode",
            total_problems=300,
            hard_solved=50
        )
        db.session.add(stats)
        db.session.commit()
        
        skill = self.matcher._assess_user_skill_level(self.user.id)
        self.assertEqual(skill, "Advanced")

    def test_extract_user_interests(self):
        interests = self.matcher._extract_user_interests(self.user)
        self.assertIn("System Design", interests)

    def test_find_matching_groups(self):
        # Create groups
        group1 = StudyGroup(
            name="System Design Advanced",
            topic="System Design",
            skill_level="Advanced",
            created_by=self.user.id
        )
        group2 = StudyGroup(
            name="Beginner Python",
            topic="Programming Languages",
            skill_level="Beginner",
            created_by=self.user.id
        )
        db.session.add(group1)
        db.session.add(group2)
        db.session.commit()
        
        # User is advanced (due to stats)
        stats = PlatformStats(
            user_id=self.user.id,
            platform="leetcode",
            total_problems=300,
            hard_solved=50
        )
        db.session.add(stats)
        db.session.commit()
        
        matches = self.matcher.find_matching_groups(self.user.id)
        self.assertTrue(len(matches) > 0)
        # Advanced System Design group should be first since it matches advanced skill level and system design topic
        self.assertEqual(matches[0].name, "System Design Advanced")
