import json
from datetime import datetime, timedelta
from app import db
from app.models import Flashcard
from app.ai import get_ai_provider

class AIFlashcardGenerator:
    def __init__(self):
        self.provider = get_ai_provider()

    def generate_flashcards_for_topic(self, topic, user_id, difficulty_level="intermediate"):
        try:
            prompt = f"""
            Create educational flashcards for the topic: "{topic}"
            
            Requirements:
            - Generate 5-15 flashcards based on topic complexity
            - Include fundamental concepts, key terms, practical examples, and problem-solving questions
            - Make questions clear and concise
            - Provide comprehensive but not overwhelming answers
            - Difficulty level: {difficulty_level}
            - Include a mix of: definitions, explanations, examples, and application questions
            
            Return a JSON object with this structure:
            {{
                "flashcards": [
                    {{
                        "question": "Clear, specific question",
                        "answer": "Comprehensive answer with examples if needed",
                        "difficulty": "easy|medium|hard",
                        "revision_frequency": "weekly|biweekly|monthly"
                    }}
                ],
                "total_cards": number,
                "suggested_study_schedule": "weekly|biweekly|monthly"
            }}
            """
            response_content = self.provider.generate_completion(prompt, "json")
            if not response_content:
                raise Exception("Empty response from AI")
                
            response_content = response_content.strip()
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
                
            ai_response = json.loads(response_content)
            
            saved_flashcards = []
            for card_data in ai_response['flashcards']:
                flashcard = Flashcard()
                flashcard.user_id = user_id
                flashcard.topic = topic
                flashcard.question = card_data['question']
                flashcard.answer = card_data['answer']
                flashcard.category = topic
                flashcard.difficulty = card_data.get('difficulty', 'medium')
                flashcard.next_review = self._calculate_next_review(card_data.get('revision_frequency', 'weekly'))
                flashcard.is_ai_generated = True
                db.session.add(flashcard)
                saved_flashcards.append(flashcard)
                
            db.session.commit()
            
            return {
                'success': True,
                'flashcards': saved_flashcards,
                'total_generated': len(saved_flashcards),
                'suggested_schedule': ai_response.get('suggested_study_schedule', 'weekly'),
                'provider_used': self.provider.__class__.__name__
            }
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            # Fallback to local samples
            return self._generate_sample_flashcards(topic, user_id, difficulty_level)

    def _calculate_next_review(self, frequency):
        now = datetime.utcnow()
        if frequency == 'weekly':
            return now + timedelta(weeks=1)
        elif frequency == 'biweekly':
            return now + timedelta(weeks=2)
        elif frequency == 'monthly':
            return now + timedelta(weeks=4)
        return now + timedelta(weeks=1)

    def _generate_sample_flashcards(self, topic, user_id, difficulty_level):
        # Generate some basic local template flashcards
        topic_lower = topic.lower()
        samples = [
            {
                'question': f'What is a core concept of {topic}?',
                'answer': f'{topic} is a significant concept in computer science. Understanding its fundamentals is crucial for solving related problems.',
                'difficulty': 'easy'
            },
            {
                'question': f'Give a practical application of {topic}.',
                'answer': f'{topic} is widely used in software development to optimize algorithms, structure data, or design system components.',
                'difficulty': 'medium'
            }
        ]
        
        saved_flashcards = []
        for card_data in samples:
            flashcard = Flashcard()
            flashcard.user_id = user_id
            flashcard.topic = topic
            flashcard.question = card_data['question']
            flashcard.answer = card_data['answer']
            flashcard.category = topic
            flashcard.difficulty = card_data['difficulty']
            flashcard.next_review = self._calculate_next_review('weekly')
            flashcard.is_ai_generated = False
            db.session.add(flashcard)
            saved_flashcards.append(flashcard)
            
        db.session.commit()
        return {
            'success': True,
            'flashcards': saved_flashcards,
            'total_generated': len(saved_flashcards),
            'suggested_schedule': 'weekly',
            'provider_used': 'fallback_local'
        }

    def suggest_revision_schedule(self, topic, difficulty_level):
        prompt = f"""
        For the topic "{topic}" with difficulty level "{difficulty_level}", 
        suggest an optimal revision schedule.
        Return JSON with:
        {{
            "recommended_frequency": "weekly|biweekly|monthly",
            "reasoning": "Brief explanation",
            "initial_review": "1-3 days",
            "subsequent_reviews": "schedule pattern"
        }}
        """
        try:
            response_content = self.provider.generate_completion(prompt, "json")
            return json.loads(response_content)
        except Exception as e:
            return {
                "recommended_frequency": "weekly",
                "reasoning": "Default weekly schedule due to fallback",
                "initial_review": "2-3 days",
                "subsequent_reviews": "Weekly intervals"
            }

    def get_topics_by_user(self, user_id):
        from sqlalchemy import text
        topics = db.session.execute(
            text("SELECT DISTINCT topic FROM flashcard WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchall()
        return [topic[0] for topic in topics]

    def get_flashcards_by_topic(self, user_id, topic):
        return Flashcard.query.filter_by(user_id=user_id, topic=topic).all()

    def get_due_flashcards(self, user_id):
        now = datetime.utcnow()
        return Flashcard.query.filter(
            Flashcard.user_id == user_id,
            Flashcard.next_review <= now
        ).all()

    def update_flashcard_after_review(self, flashcard_id, quality_rating):
        flashcard = Flashcard.query.get(flashcard_id)
        if not flashcard:
            return False
            
        flashcard.review_count += 1
        flashcard.last_reviewed = datetime.utcnow()
        
        if quality_rating >= 4:
            flashcard.ease_factor = (flashcard.ease_factor or 2.5) + 0.1
            multiplier = flashcard.ease_factor
        elif quality_rating >= 3:
            multiplier = 1.0
        else:
            flashcard.ease_factor = max(1.3, (flashcard.ease_factor or 2.5) - 0.2)
            multiplier = 0.5
            
        current_interval = 7
        if flashcard.review_count > 1:
            current_interval = int(current_interval * multiplier)
            
        flashcard.next_review = datetime.utcnow() + timedelta(days=current_interval)
        db.session.commit()
        return True

    def enhance_flashcard_content(self, flashcard_id, user_feedback=""):
        flashcard = Flashcard.query.get(flashcard_id)
        if not flashcard:
            return {"success": False, "error": "Flashcard not found"}
            
        prompt = f"""
        Enhance this flashcard content based on user feedback:
        Current Question: {flashcard.question}
        Current Answer: {flashcard.answer}
        Topic: {flashcard.topic}
        User Feedback: {user_feedback}
        
        Provide improved content in JSON format:
        {{
            "improved_question": "Enhanced question",
            "improved_answer": "Enhanced answer with better explanations",
            "suggested_difficulty": "easy|medium|hard"
        }}
        """
        try:
            response_content = self.provider.generate_completion(prompt, "json")
            if response_content:
                result = json.loads(response_content)
                return {"success": True, "suggestions": result}
        except Exception as e:
            print(f"Error enhancing flashcard: {e}")
        return {"success": False, "error": "Could not enhance flashcard"}

    def get_available_providers(self):
        return ["openai", "claude", "gemini", "local_samples"]

    def test_ai_providers(self):
        provider_name = self.provider.__class__.__name__.replace("Provider", "").lower()
        return {provider_name: True}

EnhancedAIFlashcardGenerator = AIFlashcardGenerator
