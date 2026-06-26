from datetime import datetime, timedelta
from app.models import ForumPost, ForumAnswer, User
from app import db
import re

class DoubtForumService:
    """Service for managing the doubt forum functionality"""
    
    def __init__(self):
        self.categories = [
            'Data Structures', 'Algorithms', 'System Design', 'Database',
            'Web Development', 'Mobile Development', 'Machine Learning',
            'DevOps', 'Programming Languages', 'Debugging', 'Other'
        ]
        
        self.common_tags = [
            'python', 'java', 'javascript', 'cpp', 'arrays', 'linkedlist',
            'trees', 'graphs', 'dp', 'recursion', 'sorting', 'searching',
            'sql', 'react', 'nodejs', 'algorithms', 'leetcode', 'interview'
        ]
    
    def create_post(self, title, content, author_id, category=None, tags=None):
        """Create a new forum post"""
        # Auto-extract tags from content if not provided
        if not tags:
            tags = self._extract_tags_from_content(content)
        
        post = ForumPost()
        post.title = title
        post.content = content
        post.author_id = author_id
        post.category = category or 'Other'
        post.tags = tags
        
        db.session.add(post)
        db.session.commit()
        return post
    
    def create_answer(self, post_id, content, author_id):
        """Create an answer to a forum post"""
        answer = ForumAnswer()
        answer.post_id = post_id
        answer.content = content
        answer.author_id = author_id
        
        db.session.add(answer)
        db.session.commit()
        return answer
    
    def vote_post(self, post_id, user_id, vote_type):
        """Vote on a forum post (upvote/downvote)"""
        post = ForumPost.query.get(post_id)
        if not post:
            return False
        
        # In a full implementation, you'd track individual votes
        # For now, just increment/decrement the vote count
        if vote_type == 'up':
            post.votes += 1
        elif vote_type == 'down':
            post.votes -= 1
        
        db.session.commit()
        return True
    
    def vote_answer(self, answer_id, user_id, vote_type):
        """Vote on a forum answer"""
        answer = ForumAnswer.query.get(answer_id)
        if not answer:
            return False
        
        if vote_type == 'up':
            answer.votes += 1
        elif vote_type == 'down':
            answer.votes -= 1
        
        db.session.commit()
        return True
    
    def mark_answer_accepted(self, answer_id, post_author_id):
        """Mark an answer as accepted (only post author can do this)"""
        answer = ForumAnswer.query.get(answer_id)
        if not answer:
            return False
        
        post = ForumPost.query.get(answer.post_id)
        if not post or post.author_id != post_author_id:
            return False
        
        # Unmark other accepted answers for this post
        ForumAnswer.query.filter_by(post_id=answer.post_id).update({'is_accepted': False})
        
        # Mark this answer as accepted
        answer.is_accepted = True
        post.is_solved = True
        
        db.session.commit()
        return True
    
    def search_posts(self, query, category=None, tags=None):
        """Search forum posts by title, content, category, or tags"""
        search_query = ForumPost.query
        
        if query:
            search_query = search_query.filter(
                db.or_(
                    ForumPost.title.contains(query),
                    ForumPost.content.contains(query)
                )
            )
        
        if category and category != 'All':
            search_query = search_query.filter(ForumPost.category == category)
        
        if tags:
            # Search for posts that contain any of the specified tags
            tag_conditions = [ForumPost.tags.contains(tag) for tag in tags]
            search_query = search_query.filter(db.or_(*tag_conditions))
        
        return search_query.order_by(ForumPost.created_at.desc()).all()
    
    def get_trending_posts(self, limit=10):
        """Get trending posts based on recent activity and votes"""
        # Simple trending algorithm: recent posts with high votes
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        trending = ForumPost.query.filter(
            ForumPost.created_at >= cutoff_date
        ).order_by(
            (ForumPost.votes + ForumPost.views * 0.1).desc()
        ).limit(limit).all()
        
        return trending
    
    def get_user_reputation(self, user_id):
        """Calculate user's reputation based on their forum activity"""
        user = User.query.get(user_id)
        if not user:
            return 0
        
        # Calculate reputation based on:
        # - Posts created
        # - Answers given
        # - Votes received
        # - Accepted answers
        
        posts_count = ForumPost.query.filter_by(author_id=user_id).count()
        answers_count = ForumAnswer.query.filter_by(author_id=user_id).count()
        
        total_post_votes = db.session.query(db.func.sum(ForumPost.votes)).filter_by(author_id=user_id).scalar() or 0
        total_answer_votes = db.session.query(db.func.sum(ForumAnswer.votes)).filter_by(author_id=user_id).scalar() or 0
        accepted_answers = ForumAnswer.query.filter_by(author_id=user_id, is_accepted=True).count()
        
        reputation = (
            posts_count * 2 +
            answers_count * 3 +
            total_post_votes * 5 +
            total_answer_votes * 5 +
            accepted_answers * 15
        )
        
        return max(0, reputation)
    
    def get_similar_posts(self, post_id, limit=5):
        """Find similar posts based on tags and category"""
        post = ForumPost.query.get(post_id)
        if not post:
            return []
        
        post_tags = post.tags.split(',') if post.tags else []
        
        similar_posts = ForumPost.query.filter(
            ForumPost.id != post_id,
            ForumPost.category == post.category
        )
        
        # If post has tags, find posts with similar tags
        if post_tags:
            tag_conditions = [ForumPost.tags.contains(tag.strip()) for tag in post_tags]
            similar_posts = similar_posts.filter(db.or_(*tag_conditions))
        
        return similar_posts.order_by(ForumPost.votes.desc()).limit(limit).all()
    
    def _extract_tags_from_content(self, content):
        """Extract relevant tags from post content"""
        content_lower = content.lower()
        found_tags = []
        
        # Look for common programming terms
        for tag in self.common_tags:
            if tag in content_lower:
                found_tags.append(tag)
        
        # Extract code-like patterns
        code_patterns = [
            r'\b(def|function|class|public|private|void|int|string|bool)\b',
            r'\b(if|else|for|while|switch|case|return)\b',
            r'\b(array|list|dict|map|set|queue|stack)\b'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, content_lower)
            found_tags.extend(matches)
        
        # Remove duplicates and limit to top 5 tags
        unique_tags = list(set(found_tags))[:5]
        return ', '.join(unique_tags)
    
    def get_post_statistics(self, post_id):
        """Get detailed statistics for a post"""
        post = ForumPost.query.get(post_id)
        if not post:
            return None
        
        answers_count = ForumAnswer.query.filter_by(post_id=post_id).count()
        accepted_answers = ForumAnswer.query.filter_by(post_id=post_id, is_accepted=True).count()
        
        return {
            'views': post.views,
            'votes': post.votes,
            'answers_count': answers_count,
            'has_accepted_answer': accepted_answers > 0,
            'created_at': post.created_at,
            'is_solved': post.is_solved
        }
    
    def generate_ai_answer_suggestion(self, post_id):
        """Generate AI-powered answer suggestions for a post"""
        # This would integrate with AI service in a real implementation
        post = ForumPost.query.get(post_id)
        if not post:
            return None
        
        # Mock AI response based on common patterns
        suggestions = {
            'data structures': "Consider using appropriate data structures like hash maps for O(1) lookups, or trees for hierarchical data. Make sure to analyze the time and space complexity of your chosen approach.",
            'algorithms': "Break down the problem into smaller subproblems. Consider if this could be solved with dynamic programming, greedy approach, or divide and conquer. Don't forget to handle edge cases.",
            'debugging': "Try using print statements or a debugger to trace through your code. Check for common issues like off-by-one errors, null pointer exceptions, or incorrect loop conditions.",
            'sql': "Make sure your JOIN conditions are correct and consider using appropriate indexes for better performance. EXPLAIN PLAN can help you understand query execution.",
            'web development': "Check the browser's developer tools for any console errors. Ensure your API endpoints are working correctly and returning the expected data format."
        }
        
        content_lower = post.content.lower()
        for category, suggestion in suggestions.items():
            if category in content_lower:
                return {
                    'suggestion': suggestion,
                    'confidence': 0.7,
                    'category': category
                }
        
        return {
            'suggestion': "Try breaking down your problem into smaller steps. Consider drawing out the problem or using pseudocode first. Don't forget to test with different input cases.",
            'confidence': 0.5,
            'category': 'general'
        }
