from datetime import datetime, timedelta
import math
from app.models import Flashcard
from app import db

class SpacedRepetitionSystem:
    """Implementation of spaced repetition algorithm for flashcards"""
    
    def __init__(self):
        self.default_ease_factor = 2.5
        self.min_ease_factor = 1.3
        self.max_ease_factor = 4.0
    
    def get_due_cards(self, user_id, limit=20):
        """Get flashcards that are due for review"""
        now = datetime.utcnow()
        due_cards = Flashcard.query.filter(
            Flashcard.user_id == user_id,
            Flashcard.next_review <= now
        ).order_by(Flashcard.next_review.asc()).limit(limit).all()
        
        return due_cards
    
    def review_card(self, card_id, quality):
        """
        Review a flashcard and update its scheduling
        Quality: 1-5 scale
        1 = complete blackout
        2 = incorrect response, but correct one remembered
        3 = incorrect response, but correct one seemed easy to recall
        4 = correct response, but required significant difficulty to recall
        5 = correct response with perfect recall
        """
        card = Flashcard.query.get(card_id)
        if not card:
            return False
        
        card.last_reviewed = datetime.utcnow()
        card.repetition_count += 1
        
        if quality < 3:
            # Reset the card if quality is too low
            card.repetition_count = 0
            card.interval = 1
            card.ease_factor = max(self.min_ease_factor, card.ease_factor - 0.2)
        else:
            # Update ease factor based on quality
            card.ease_factor = max(
                self.min_ease_factor,
                min(
                    self.max_ease_factor,
                    card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
                )
            )
            
            # Calculate new interval
            if card.repetition_count == 1:
                card.interval = 1
            elif card.repetition_count == 2:
                card.interval = 6
            else:
                card.interval = math.ceil(card.interval * card.ease_factor)
        
        # Set next review date
        card.next_review = datetime.utcnow() + timedelta(days=card.interval)
        
        db.session.commit()
        return True
    
    def create_flashcard(self, user_id, question, answer, category=None, difficulty='Medium'):
        """Create a new flashcard"""
        card = Flashcard()
        card.user_id = user_id
        card.question = question
        card.answer = answer
        card.category = category
        card.topic = category or 'General'
        card.difficulty = difficulty
        card.next_review = datetime.utcnow()  # Available immediately
        card.ease_factor = self.default_ease_factor
        
        db.session.add(card)
        db.session.commit()
        return card
    
    def get_study_stats(self, user_id):
        """Get statistics about user's flashcard progress"""
        total_cards = Flashcard.query.filter_by(user_id=user_id).count()
        due_cards = len(self.get_due_cards(user_id, limit=1000))
        
        # Cards by difficulty
        easy_cards = Flashcard.query.filter_by(user_id=user_id, difficulty='Easy').count()
        medium_cards = Flashcard.query.filter_by(user_id=user_id, difficulty='Medium').count()
        hard_cards = Flashcard.query.filter_by(user_id=user_id, difficulty='Hard').count()
        
        # Cards by category
        category_stats = {}
        cards_by_category = db.session.query(
            Flashcard.category, 
            db.func.count(Flashcard.id)
        ).filter_by(user_id=user_id).group_by(Flashcard.category).all()
        
        for category, count in cards_by_category:
            category_stats[category or 'Uncategorized'] = count
        
        # Recent activity
        today = datetime.utcnow().date()
        cards_reviewed_today = Flashcard.query.filter(
            Flashcard.user_id == user_id,
            db.func.date(Flashcard.last_reviewed) == today
        ).count()
        
        return {
            'total_cards': total_cards,
            'due_cards': due_cards,
            'cards_reviewed_today': cards_reviewed_today,
            'difficulty_breakdown': {
                'Easy': easy_cards,
                'Medium': medium_cards,
                'Hard': hard_cards
            },
            'category_breakdown': category_stats,
            'completion_rate': round((total_cards - due_cards) / total_cards * 100, 1) if total_cards > 0 else 0
        }
    
    def get_suggested_cards(self, user_id, topic=None):
        """Get suggested flashcards based on common coding concepts"""
        suggestions = [
            {
                'question': 'What is the time complexity of binary search?',
                'answer': 'O(log n) - Binary search eliminates half of the search space in each iteration.',
                'category': 'Algorithms',
                'difficulty': 'Easy'
            },
            {
                'question': 'Explain the difference between BFS and DFS.',
                'answer': 'BFS explores nodes level by level (uses queue), DFS explores as far as possible along each branch (uses stack). BFS finds shortest path in unweighted graphs, DFS uses less memory.',
                'category': 'Algorithms',
                'difficulty': 'Medium'
            },
            {
                'question': 'What is a hash table collision and how do you handle it?',
                'answer': 'A collision occurs when two keys hash to the same index. Handle with: 1) Chaining (linked lists at each index), 2) Open addressing (linear/quadratic probing), 3) Double hashing.',
                'category': 'Data Structures',
                'difficulty': 'Medium'
            },
            {
                'question': 'What is the space complexity of merge sort?',
                'answer': 'O(n) - Merge sort requires additional space for the temporary arrays used during the merge process.',
                'category': 'Algorithms',
                'difficulty': 'Easy'
            },
            {
                'question': 'Explain dynamic programming.',
                'answer': 'DP solves complex problems by breaking them into simpler subproblems. Key principles: 1) Optimal substructure, 2) Overlapping subproblems. Use memoization (top-down) or tabulation (bottom-up).',
                'category': 'Algorithms',
                'difficulty': 'Hard'
            },
            {
                'question': 'What is the difference between TCP and UDP?',
                'answer': 'TCP: Connection-oriented, reliable, ordered delivery, flow control, slower. UDP: Connectionless, unreliable, no ordering guarantee, faster, used for real-time applications.',
                'category': 'System Design',
                'difficulty': 'Medium'
            },
            {
                'question': 'Explain Big O notation.',
                'answer': 'Big O describes the upper bound of algorithm complexity. Common complexities: O(1) constant, O(log n) logarithmic, O(n) linear, O(n log n) linearithmic, O(n²) quadratic, O(2ⁿ) exponential.',
                'category': 'Algorithms',
                'difficulty': 'Easy'
            },
            {
                'question': 'What is a balanced binary tree?',
                'answer': 'A binary tree where the height difference between left and right subtrees of any node is at most 1. Examples: AVL trees, Red-Black trees. Ensures O(log n) operations.',
                'category': 'Data Structures',
                'difficulty': 'Medium'
            },
            {
                'question': 'Explain the CAP theorem.',
                'answer': 'CAP theorem states that distributed systems can only guarantee 2 out of 3: Consistency (all nodes see same data), Availability (system remains operational), Partition tolerance (system continues despite network failures).',
                'category': 'System Design',
                'difficulty': 'Hard'
            },
            {
                'question': 'What is a deadlock in operating systems?',
                'answer': 'Deadlock occurs when processes wait indefinitely for resources held by each other. Four conditions: Mutual exclusion, Hold and wait, No preemption, Circular wait. Prevention: eliminate one condition.',
                'category': 'Operating Systems',
                'difficulty': 'Medium'
            }
        ]
        
        if topic:
            suggestions = [s for s in suggestions if topic.lower() in s['category'].lower()]
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def bulk_create_flashcards(self, user_id, cards_data):
        """Create multiple flashcards at once"""
        created_cards = []
        
        for card_data in cards_data:
            card = Flashcard()
            card.user_id = user_id
            card.question = card_data['question']
            card.answer = card_data['answer']
            card.category = card_data.get('category', 'General')
            card.topic = card_data.get('category', 'General')
            card.difficulty = card_data.get('difficulty', 'Medium')
            card.next_review = datetime.utcnow()
            card.ease_factor = self.default_ease_factor
            db.session.add(card)
            created_cards.append(card)
        
        db.session.commit()
        return created_cards
    
    def get_retention_rate(self, user_id, days=30):
        """Calculate retention rate over the past N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get cards reviewed in the period
        reviewed_cards = Flashcard.query.filter(
            Flashcard.user_id == user_id,
            Flashcard.last_reviewed >= cutoff_date,
            Flashcard.repetition_count > 0
        ).all()
        
        if not reviewed_cards:
            return 0
        
        # Calculate average ease factor as a proxy for retention
        total_ease = sum(card.ease_factor for card in reviewed_cards)
        avg_ease = total_ease / len(reviewed_cards)
        
        # Convert ease factor to percentage (2.5 = 100%, 1.3 = 0%)
        retention_rate = max(0, min(100, (avg_ease - 1.3) / (2.5 - 1.3) * 100))
        
        return round(retention_rate, 1)
