from datetime import datetime
from app.models import User, StudyGroup, StudyGroupMember, PlatformStats
from app import db
import random

class StudyGroupMatcher:
    """Service for matching users with appropriate study groups"""
    
    def __init__(self):
        self.skill_levels = ['Beginner', 'Intermediate', 'Advanced']
        self.topics = [
            'Data Structures', 'Algorithms', 'System Design', 'Database',
            'Web Development', 'Machine Learning', 'Mobile Development',
            'DevOps', 'Competitive Programming', 'Interview Preparation'
        ]
    
    def find_matching_groups(self, user_id, limit=5):
        """Find study groups that match user's skill level and interests"""
        user = User.query.get(user_id)
        if not user:
            return []
        
        user_skill_level = self._assess_user_skill_level(user_id)
        user_interests = self._extract_user_interests(user)
        
        # Get groups user is not already in
        user_group_ids = [m.group_id for m in StudyGroupMember.query.filter_by(user_id=user_id).all()]
        
        available_groups = StudyGroup.query.filter(
            StudyGroup.is_active == True,
            ~StudyGroup.id.in_(user_group_ids) if user_group_ids else True
        ).all()
        
        # Score and rank groups
        scored_groups = []
        for group in available_groups:
            score = self._calculate_match_score(group, user_skill_level, user_interests)
            if score > 0:
                scored_groups.append((group, score))
        
        # Sort by score and return top matches
        scored_groups.sort(key=lambda x: x[1], reverse=True)
        return [group for group, score in scored_groups[:limit]]
    
    def _assess_user_skill_level(self, user_id):
        """Assess user's skill level based on their platform statistics"""
        stats = PlatformStats.query.filter_by(user_id=user_id).all()
        
        if not stats:
            return 'Beginner'
        
        total_problems = sum(stat.total_problems for stat in stats)
        total_hard = sum(stat.hard_solved for stat in stats)
        avg_rating = sum(stat.contest_rating for stat in stats if stat.contest_rating > 0) / len([s for s in stats if s.contest_rating > 0]) if any(s.contest_rating > 0 for s in stats) else 0
        
        # Simple scoring system
        if total_problems < 50 or (avg_rating > 0 and avg_rating < 1200):
            return 'Beginner'
        elif total_problems < 200 or total_hard < 20 or (avg_rating > 0 and avg_rating < 1800):
            return 'Intermediate'
        else:
            return 'Advanced'
    
    def _extract_user_interests(self, user):
        """Extract user interests from their profile and goals"""
        interests = set()
        
        if user.learning_goals:
            goals = user.learning_goals.lower()
            for topic in self.topics:
                if topic.lower() in goals:
                    interests.add(topic)
        
        if user.target_companies:
            companies = user.target_companies.lower()
            # Infer interests from target companies
            if any(company in companies for company in ['google', 'facebook', 'amazon', 'apple', 'microsoft']):
                interests.update(['Algorithms', 'System Design', 'Interview Preparation'])
            
            if any(company in companies for company in ['netflix', 'uber', 'airbnb']):
                interests.add('System Design')
        
        # Default interests if none found
        if not interests:
            interests = {'Algorithms', 'Data Structures'}
        
        return interests
    
    def _calculate_match_score(self, group, user_skill_level, user_interests):
        """Calculate how well a group matches a user"""
        score = 0
        
        # Skill level match (high weight)
        if group.skill_level == user_skill_level:
            score += 50
        elif abs(self.skill_levels.index(group.skill_level) - self.skill_levels.index(user_skill_level)) == 1:
            score += 25  # Adjacent skill levels get partial credit
        
        # Topic interest match
        if group.topic in user_interests:
            score += 30
        
        # Group size preference (not too full, not too empty)
        current_members = StudyGroupMember.query.filter_by(group_id=group.id).count()
        if 3 <= current_members <= group.max_members - 2:
            score += 20
        elif current_members < group.max_members:
            score += 10
        
        # Activity level (prefer newer groups or recently active ones)
        import datetime
        days_since_creation = (datetime.datetime.utcnow() - group.created_at).days
        if days_since_creation < 7:
            score += 15  # New group bonus
        elif days_since_creation < 30:
            score += 10
        
        return score
    
    def create_suggested_groups(self, user_id):
        """Create suggested study groups based on user profile"""
        user = User.query.get(user_id)
        if not user:
            return []
        
        user_skill_level = self._assess_user_skill_level(user_id)
        user_interests = self._extract_user_interests(user)
        
        suggestions = []
        
        # Generate group suggestions based on interests
        for interest in list(user_interests)[:3]:  # Top 3 interests
            group_name = f"{interest} Study Group - {user_skill_level}"
            description = f"A collaborative space for {user_skill_level.lower()} level learners to master {interest.lower()}. Share resources, solve problems together, and track progress."
            
            suggestions.append({
                'name': group_name,
                'description': description,
                'topic': interest,
                'skill_level': user_skill_level,
                'max_members': random.randint(8, 15)
            })
        
        # Add some general suggestions
        general_suggestions = [
            {
                'name': f'Daily Problem Solvers - {user_skill_level}',
                'description': 'Solve one coding problem together every day. Perfect for building consistency and learning from peers.',
                'topic': 'Competitive Programming',
                'skill_level': user_skill_level,
                'max_members': 10
            },
            {
                'name': f'Interview Preparation Group - {user_skill_level}',
                'description': 'Prepare for technical interviews together. Mock interviews, problem discussions, and tips sharing.',
                'topic': 'Interview Preparation',
                'skill_level': user_skill_level,
                'max_members': 12
            }
        ]
        
        suggestions.extend(general_suggestions)
        return suggestions[:5]
    
    def get_group_activity_score(self, group_id):
        """Calculate activity score for a study group"""
        # This would track group interactions, problem-solving sessions, etc.
        # For now, return a mock score based on member count and age
        group = StudyGroup.query.get(group_id)
        if not group:
            return 0
        
        member_count = StudyGroupMember.query.filter_by(group_id=group_id).count()
        days_since_creation = (datetime.utcnow() - group.created_at).days
        
        # Score based on member engagement and recency
        score = member_count * 10
        if days_since_creation < 7:
            score += 50
        elif days_since_creation < 30:
            score += 25
        
        return min(score, 100)  # Cap at 100
    
    def find_study_buddy(self, user_id):
        """Find individual study buddies with similar skill levels"""
        user = User.query.get(user_id)
        if not user:
            return []
        
        user_skill_level = self._assess_user_skill_level(user_id)
        user_interests = self._extract_user_interests(user)
        
        # Find users with similar skill levels
        all_users = User.query.filter(User.id != user_id).all()
        potential_buddies = []
        
        for candidate in all_users:
            candidate_skill = self._assess_user_skill_level(candidate.id)
            candidate_interests = self._extract_user_interests(candidate)
            
            # Calculate compatibility
            score = 0
            if candidate_skill == user_skill_level:
                score += 50
            
            # Interest overlap
            common_interests = user_interests.intersection(candidate_interests)
            score += len(common_interests) * 20
            
            if score > 40:  # Minimum compatibility threshold
                potential_buddies.append({
                    'user': candidate,
                    'score': score,
                    'common_interests': list(common_interests),
                    'skill_level': candidate_skill
                })
        
        # Sort by compatibility score
        potential_buddies.sort(key=lambda x: x['score'], reverse=True)
        return potential_buddies[:5]
