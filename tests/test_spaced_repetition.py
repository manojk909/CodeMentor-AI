import unittest
import os
from datetime import datetime, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SESSION_SECRET'] = 'test-secret'

from app import app, db
from app.models import User, Flashcard
from app.ai.flashcard import AIFlashcardGenerator

class TestSpacedRepetition(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Create test user
        self.user = User(username="test_spaced", email="spaced@example.com")
        self.user.set_password("password")
        db.session.add(self.user)
        db.session.commit()
        
        self.generator = AIFlashcardGenerator()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_calculate_next_review(self):
        # Test calculation of next review interval
        now = datetime.utcnow()
        
        # Test weekly
        weekly_date = self.generator._calculate_next_review('weekly')
        self.assertAlmostEqual((weekly_date - now).days, 7, delta=1)
        
        # Test biweekly
        biweekly_date = self.generator._calculate_next_review('biweekly')
        self.assertAlmostEqual((biweekly_date - now).days, 14, delta=1)
        
        # Test monthly
        monthly_date = self.generator._calculate_next_review('monthly')
        self.assertAlmostEqual((monthly_date - now).days, 28, delta=1)
        
        # Test default
        default_date = self.generator._calculate_next_review('invalid_freq')
        self.assertAlmostEqual((default_date - now).days, 7, delta=1)

    def test_local_sample_flashcards_fallback(self):
        # When calling generator with fallback, it should generate sample flashcards
        result = self.generator._generate_sample_flashcards("Recursion", self.user.id, "easy")
        self.assertTrue(result['success'])
        self.assertEqual(result['total_generated'], 2)
        self.assertEqual(result['provider_used'], 'fallback_local')
        
        # Check flashcards in db
        cards = Flashcard.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].topic, "Recursion")
        self.assertFalse(cards[0].is_ai_generated)

    def test_update_flashcard_after_review(self):
        # Create flashcard
        card = Flashcard(
            user_id=self.user.id,
            topic="Binary Search",
            question="What is binary search?",
            answer="A fast search algorithm.",
            difficulty="easy",
            ease_factor=2.5,
            review_count=0
        )
        db.session.add(card)
        db.session.commit()
        
        card_id = card.id
        
        # Review with high rating (quality_rating = 5) -> ease_factor increases, review_count increases
        success = self.generator.update_flashcard_after_review(card_id, 5)
        self.assertTrue(success)
        
        card = Flashcard.query.get(card_id)
        self.assertEqual(card.review_count, 1)
        self.assertAlmostEqual(card.ease_factor, 2.6)
        self.assertIsNotNone(card.last_reviewed)
        
        # Review with high rating again (review_count > 1) -> interval increases
        success = self.generator.update_flashcard_after_review(card_id, 4)
        self.assertTrue(success)
        card = Flashcard.query.get(card_id)
        self.assertEqual(card.review_count, 2)
        self.assertAlmostEqual(card.ease_factor, 2.7)
        self.assertTrue((card.next_review - datetime.utcnow()).days > 7)
        
        # Review with poor rating (quality_rating = 2) -> ease_factor decreases
        success = self.generator.update_flashcard_after_review(card_id, 2)
        self.assertTrue(success)
        card = Flashcard.query.get(card_id)
        self.assertAlmostEqual(card.ease_factor, 2.5)

    def test_get_due_flashcards(self):
        # Create due card (next_review is in the past)
        due_card = Flashcard(
            user_id=self.user.id,
            topic="Python",
            question="What is Python?",
            answer="A programming language.",
            next_review=datetime.utcnow() - timedelta(days=1)
        )
        # Create not-due card (next_review is in the future)
        future_card = Flashcard(
            user_id=self.user.id,
            topic="Java",
            question="What is Java?",
            answer="A programming language.",
            next_review=datetime.utcnow() + timedelta(days=5)
        )
        db.session.add(due_card)
        db.session.add(future_card)
        db.session.commit()
        
        due_cards = self.generator.get_due_flashcards(self.user.id)
        self.assertEqual(len(due_cards), 1)
        self.assertEqual(due_cards[0].topic, "Python")

    def test_get_topics_and_flashcards_by_topic(self):
        card1 = Flashcard(
            user_id=self.user.id,
            topic="Dynamic Programming",
            question="Q1",
            answer="A1"
        )
        card2 = Flashcard(
            user_id=self.user.id,
            topic="Graphs",
            question="Q2",
            answer="A2"
        )
        db.session.add(card1)
        db.session.add(card2)
        db.session.commit()
        
        topics = self.generator.get_topics_by_user(self.user.id)
        self.assertIn("Dynamic Programming", topics)
        self.assertIn("Graphs", topics)
        self.assertEqual(len(topics), 2)
        
        cards = self.generator.get_flashcards_by_topic(self.user.id, "Graphs")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].question, "Q2")

class TestSpacedRepetitionSystem(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        self.user = User(username="test_srs", email="srs@example.com")
        self.user.set_password("password")
        db.session.add(self.user)
        db.session.commit()
        
        from app.services.spaced_repetition import SpacedRepetitionSystem
        self.srs = SpacedRepetitionSystem()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_create_flashcard(self):
        card = self.srs.create_flashcard(
            user_id=self.user.id,
            question="What is a set?",
            answer="A collection of unique elements.",
            category="Data Structures",
            difficulty="Easy"
        )
        self.assertEqual(card.user_id, self.user.id)
        self.assertEqual(card.question, "What is a set?")
        self.assertEqual(card.category, "Data Structures")
        self.assertEqual(card.difficulty, "Easy")
        self.assertIsNotNone(card.next_review)

    def test_bulk_create_flashcards(self):
        cards_data = [
            {"question": "Q1", "answer": "A1", "category": "C1", "difficulty": "Easy"},
            {"question": "Q2", "answer": "A2", "category": "C2", "difficulty": "Medium"}
        ]
        created = self.srs.bulk_create_flashcards(self.user.id, cards_data)
        self.assertEqual(len(created), 2)
        self.assertEqual(created[0].question, "Q1")
        self.assertEqual(created[1].question, "Q2")

    def test_review_card_low_quality(self):
        card = self.srs.create_flashcard(
            user_id=self.user.id,
            question="Q",
            answer="A"
        )
        # Quality = 2 (incorrect response) -> repetition_count reset to 0, interval reset to 1
        card.repetition_count = 5
        card.interval = 10
        card.ease_factor = 2.5
        db.session.commit()
        
        success = self.srs.review_card(card.id, 2)
        self.assertTrue(success)
        
        updated_card = Flashcard.query.get(card.id)
        self.assertEqual(updated_card.repetition_count, 0)
        self.assertEqual(updated_card.interval, 1)
        self.assertAlmostEqual(updated_card.ease_factor, 2.3)

    def test_review_card_high_quality(self):
        card = self.srs.create_flashcard(
            user_id=self.user.id,
            question="Q",
            answer="A"
        )
        card.repetition_count = 2
        card.interval = 6
        card.ease_factor = 2.5
        db.session.commit()
        
        # Quality = 5 -> repetition_count becomes 3, ease_factor increases
        success = self.srs.review_card(card.id, 5)
        self.assertTrue(success)
        
        updated_card = Flashcard.query.get(card.id)
        self.assertEqual(updated_card.repetition_count, 3)
        self.assertTrue(updated_card.ease_factor > 2.5)
        self.assertTrue(updated_card.interval > 6)

    def test_get_study_stats(self):
        card = self.srs.create_flashcard(
            user_id=self.user.id,
            question="Q",
            answer="A",
            category="Alg",
            difficulty="Medium"
        )
        stats = self.srs.get_study_stats(self.user.id)
        self.assertEqual(stats['total_cards'], 1)
        self.assertEqual(stats['due_cards'], 1)
        self.assertEqual(stats['difficulty_breakdown']['Medium'], 1)
        self.assertEqual(stats['category_breakdown']['Alg'], 1)

    def test_get_retention_rate(self):
        card = self.srs.create_flashcard(
            user_id=self.user.id,
            question="Q",
            answer="A"
        )
        # Mark card reviewed today
        card.last_reviewed = datetime.utcnow()
        card.repetition_count = 1
        card.ease_factor = 2.5
        db.session.commit()
        
        rate = self.srs.get_retention_rate(self.user.id)
        self.assertEqual(rate, 100.0)

