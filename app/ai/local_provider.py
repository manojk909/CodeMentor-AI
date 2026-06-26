import json
from app.ai.provider import BaseAIProvider

class LocalSampleProvider(BaseAIProvider):
    def generate_completion(self, prompt: str, response_format: str = "text") -> str:
        prompt_lower = prompt.lower()
        
        # Study plan generation
        if any(word in prompt_lower for word in ['study plan', 'learning plan', 'week']):
            return json.dumps({
                "week_1": {
                    "focus": "Data Structures Fundamentals",
                    "daily_tasks": ["Review arrays and linked lists", "Practice 2-3 easy problems", "Study time complexity"],
                    "recommended_problems": ["Two Sum", "Remove Duplicates from Sorted Array"],
                    "learning_resources": ["LeetCode Arrays section", "GeeksforGeeks Data Structures"]
                },
                "week_2": {
                    "focus": "Algorithms - Sorting and Searching", 
                    "daily_tasks": ["Learn binary search", "Practice sorting algorithms", "Solve medium problems"],
                    "recommended_problems": ["Binary Search", "Merge Sorted Array"],
                    "learning_resources": ["Algorithm visualization tools", "Practice on HackerRank"]
                },
                "week_3": {
                    "focus": "Dynamic Programming Basics",
                    "daily_tasks": ["Understand memoization", "Practice simple DP problems", "Review problem patterns"],
                    "recommended_problems": ["Climbing Stairs", "House Robber"],
                    "learning_resources": ["DP pattern recognition guides", "YouTube DP tutorials"]
                },
                "week_4": {
                    "focus": "System Design Concepts",
                    "daily_tasks": ["Learn scalability basics", "Practice design questions", "Review case studies"],
                    "recommended_problems": ["Design URL Shortener", "Design Chat System"],
                    "learning_resources": ["System Design Primer", "High-level design examples"]
                },
                "tips": [
                    "Practice consistently every day",
                    "Focus on understanding, not just solving",
                    "Review your solutions and optimize them",
                    "Join study groups for motivation"
                ]
            })
        
        # Problem recommendations
        elif any(word in prompt_lower for word in ['problem', 'recommend', 'solve']):
            return json.dumps({
                "recommended_problems": [
                    {
                        "title": "Two Sum",
                        "platform": "LeetCode",
                        "difficulty": "Easy",
                        "topic": "Arrays/Hash Tables",
                        "reason": "Fundamental problem that teaches hash table usage",
                        "estimated_time": "20 minutes"
                    },
                    {
                        "title": "Valid Parentheses",
                        "platform": "LeetCode",
                        "difficulty": "Easy", 
                        "topic": "Stack",
                        "reason": "Essential for understanding stack data structure",
                        "estimated_time": "25 minutes"
                    },
                    {
                        "title": "Binary Search",
                        "platform": "LeetCode",
                        "difficulty": "Easy",
                        "topic": "Binary Search",
                        "reason": "Foundation for all binary search problems",
                        "estimated_time": "25 minutes"
                    }
                ],
                "focus_areas": ["Data Structures", "Basic Algorithms", "Problem-solving patterns"],
                "study_order": "Start with easy problems to build confidence, then gradually move to medium difficulty"
            })
        
        # Flashcard content
        elif any(word in prompt_lower for word in ['flashcard', 'generate flashcards']):
            return json.dumps({
                "flashcards": [
                    {
                        "question": "What is time complexity?",
                        "answer": "Time complexity measures how the runtime of an algorithm grows with input size. Common complexities: O(1), O(log n), O(n), O(n²).",
                        "difficulty": "easy",
                        "revision_frequency": "weekly"
                    },
                    {
                        "question": "Explain Big O notation",
                        "answer": "Big O describes the upper bound of algorithm performance. It helps compare efficiency and scalability of different approaches.",
                        "difficulty": "medium", 
                        "revision_frequency": "biweekly"
                    },
                    {
                        "question": "What is a hash table?",
                        "answer": "A hash table stores key-value pairs with O(1) average lookup time. Uses hash function to map keys to array indices.",
                        "difficulty": "medium",
                        "revision_frequency": "weekly"
                    }
                ],
                "total_cards": 3,
                "suggested_study_schedule": "weekly"
            })
        
        # Tutoring chat explanations
        elif 'linked list' in prompt_lower:
            return """A linked list is a fundamental data structure where elements (called nodes) are stored in sequence, but unlike arrays, they're not stored in contiguous memory locations. Each node contains two parts: the data and a pointer (or reference) to the next node in the sequence."""
        elif 'hash table' in prompt_lower or 'hash map' in prompt_lower:
            return """A hash table (also called a hash map) is a data structure that implements an associative array, which means it can map keys to values."""
        elif 'binary search' in prompt_lower:
            return """Binary search is an incredibly efficient algorithm for finding a specific element in a sorted array or list. It works by repeatedly dividing the search space in half."""
        elif 'recursion' in prompt_lower:
            return """Recursion is a programming technique where a function calls itself to solve a problem by breaking it down into smaller, similar subproblems."""
        
        # General advice or default JSON
        if response_format == "json":
            return json.dumps({
                "advice": "Focus on consistent daily practice and understanding fundamentals",
                "action_items": ["Set aside 1-2 hours daily for coding practice"],
                "resources": ["LeetCode for algorithm practice"],
                "next_steps": "Start with easy problems",
                "motivation": "Consistent practice leads to mastery!"
            })
        return "Focus on consistent daily practice and understanding programming fundamentals. Start with easy problems and gradually build up your skills."
