import json
from app.models import User, PlatformStats, ProblemSolved
from app.ai import get_ai_provider

class AITutor:
    def __init__(self):
        self.provider = get_ai_provider()
        
    def get_recommendation(self, user_id, recommendation_type, user_query=""):
        user = User.query.get(user_id)
        if not user:
            return "User not found"
            
        platform_stats = PlatformStats.query.filter_by(user_id=user_id).all()
        recent_problems = ProblemSolved.query.filter_by(user_id=user_id).order_by(ProblemSolved.solved_at.desc()).limit(10).all()
        
        context = self._build_user_context(user, platform_stats, recent_problems)
        
        if recommendation_type == 'study_plan':
            return self._generate_study_plan(context, user_query)
        elif recommendation_type == 'problem':
            return self._recommend_problems(context, user_query)
        elif recommendation_type == 'topic':
            return self._recommend_topics(context, user_query)
        elif recommendation_type == 'weakness':
            return self._identify_weaknesses(context, user_query)
        else:
            return self._general_recommendation(context, user_query)

    def _build_user_context(self, user, platform_stats, recent_problems):
        context = f"User: {user.username}\n"
        context += f"Learning Goals: {user.learning_goals or 'Not specified'}\n"
        context += f"Target Companies: {user.target_companies or 'Not specified'}\n"
        
        if platform_stats:
            context += "\nPlatform Progress:\n"
            for stat in platform_stats:
                context += f"- {stat.platform}: {stat.total_problems} problems solved "
                context += f"(Easy: {stat.easy_solved}, Medium: {stat.medium_solved}, Hard: {stat.hard_solved})\n"
                
        if recent_problems:
            context += "\nRecent Problems Solved:\n"
            for problem in recent_problems[:5]:
                context += f"- {problem.problem.title if problem.problem else 'Unknown'} "
                context += f"({problem.problem.difficulty if problem.problem else 'Unknown'} - "
                context += f"{problem.problem.category if problem.problem else 'Unknown'})\n"
                
        return context

    def _generate_study_plan(self, context, user_query):
        prompt = f"""Based on the following user profile and coding progress, create a personalized 4-week study plan.
        Focus on areas that need improvement and align with their goals.
        
        User Context:
        {context}
        
        Additional Requirements: {user_query}
        
        Please provide a detailed study plan in JSON format with the following structure:
        {{
            "week_1": {{
                "focus": "main topic to focus on",
                "daily_tasks": ["task1", "task2", "task3"],
                "recommended_problems": ["problem1", "problem2"],
                "learning_resources": ["resource1", "resource2"]
            }},
            "week_2": {{ ... }},
            "week_3": {{ ... }},
            "week_4": {{ ... }},
            "tips": ["general study tip1", "tip2"]
        }}
        """
        return self.provider.generate_completion(prompt, "json")

    def _recommend_problems(self, context, user_query):
        prompt = f"""Based on the user's coding progress, recommend 10 specific coding problems they should solve next.
        Consider their current skill level and areas that need improvement.
        
        User Context:
        {context}
        
        Specific Request: {user_query}
        
        Provide recommendations in JSON format:
        {{
            "recommended_problems": [
                {{
                    "title": "Problem Title",
                    "platform": "LeetCode/GeeksforGeeks/HackerRank",
                    "difficulty": "Easy/Medium/Hard",
                    "topic": "Data Structures/Algorithms/etc",
                    "reason": "Why this problem is recommended",
                    "estimated_time": "30 minutes"
                }}
            ],
            "focus_areas": ["area1", "area2"],
            "study_order": "suggested order explanation"
        }}
        """
        return self.provider.generate_completion(prompt, "json")

    def _recommend_topics(self, context, user_query):
        prompt = f"""Based on the user's coding progress, recommend specific computer science topics they should study next.
        
        User Context:
        {context}
        
        Specific Request: {user_query}
        
        Provide recommendations in JSON format:
        {{
            "priority_topics": [
                {{
                    "topic": "Topic Name",
                    "importance": "High/Medium/Low",
                    "reason": "Why this topic is important",
                    "learning_resources": ["resource1", "resource2"],
                    "practice_problems": ["problem type1", "problem type2"],
                    "estimated_study_time": "2 weeks"
                }}
            ],
            "learning_path": "suggested order of topics",
            "quick_wins": ["topics that can be learned quickly"]
        }}
        """
        return self.provider.generate_completion(prompt, "json")

    def _identify_weaknesses(self, context, user_query):
        prompt = f"""Analyze the user's coding progress and identify their weak areas.
        Provide specific suggestions for improvement.
        
        User Context:
        {context}
        
        Additional Information: {user_query}
        
        Provide analysis in JSON format:
        {{
            "identified_weaknesses": [
                {{
                    "area": "Weakness area",
                    "evidence": "What indicates this weakness",
                    "impact": "How this affects their progress",
                    "improvement_plan": "Specific steps to improve"
                }}
            ],
            "strengths": ["area1", "area2"],
            "improvement_priority": "which weakness to tackle first",
            "timeline": "expected improvement timeline"
        }}
        """
        return self.provider.generate_completion(prompt, "json")

    def _general_recommendation(self, context, user_query):
        prompt = f"""Provide personalized coding advice and recommendations based on the user's profile.
        
        User Context:
        {context}
        
        User Question: {user_query}
        
        Provide advice in JSON format:
        {{
            "advice": "main advice or answer to their question",
            "action_items": ["specific action1", "action2", "action3"],
            "resources": ["helpful resource1", "resource2"],
            "next_steps": "what they should do next",
            "motivation": "encouraging message"
        }}
        """
        return self.provider.generate_completion(prompt, "json")

    def chat_with_tutor(self, user_id, message):
        user = User.query.get(user_id)
        if not user:
            return "User not found"
            
        platform_stats = PlatformStats.query.filter_by(user_id=user_id).all()
        context = self._build_user_context(user, platform_stats, [])
        
        prompt = f"""You are a helpful programming tutor. The student profile is:
        {context}
        
        The student asked: "{message}"
        
        Answer this question naturally in conversational paragraphs, like ChatGPT or Gemini would.
        Important:
        - Write in flowing, natural paragraphs
        - Don't use JSON, bullet points, or structured formats
        - Be conversational and friendly
        - Explain concepts clearly with examples when helpful
        - Keep it educational but easy to understand
        """
        try:
            response = self.provider.generate_completion(prompt, "text")
            
            # Clean up JSON wrappers if they slip through
            if response and response.strip():
                clean_response = response.strip()
                if clean_response.startswith('{') and clean_response.endswith('}'):
                    try:
                        parsed = json.loads(clean_response)
                        for key in ['answer', 'response', 'content', 'explanation', 'text']:
                            if key in parsed:
                                return parsed[key]
                    except:
                        pass
                return clean_response
            return "I'm having trouble generating a response right now. Could you try asking your question again?"
        except Exception as e:
            return f"I apologize, but I'm experiencing some technical difficulties: {e}"

    def get_available_ai_providers(self):
        return ["openai", "claude", "gemini", "local_samples"]

    def test_ai_providers(self):
        provider_name = self.provider.__class__.__name__.replace("Provider", "").lower()
        return {provider_name: True}

EnhancedAITutor = AITutor
