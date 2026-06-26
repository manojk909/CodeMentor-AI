from datetime import datetime, timedelta
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    bio = db.Column(db.Text)
    learning_goals = db.Column(db.Text)
    target_companies = db.Column(db.Text)
    preferred_schedule = db.Column(db.String(100))
    
    # Platform accounts
    leetcode_username = db.Column(db.String(100))
    geeksforgeeks_profile = db.Column(db.String(200))
    hackerrank_username = db.Column(db.String(100))
    github_username = db.Column(db.String(100))
    
    # Relationships
    platform_stats = db.relationship('PlatformStats', backref='user', lazy=True, cascade='all, delete-orphan')
    problems_solved = db.relationship('ProblemSolved', backref='user', lazy=True, cascade='all, delete-orphan')
    flashcards = db.relationship('Flashcard', backref='user', lazy=True, cascade='all, delete-orphan')
    study_sessions = db.relationship('StudySession', backref='user', lazy=True, cascade='all, delete-orphan')
    forum_posts = db.relationship('ForumPost', backref='author', lazy=True, cascade='all, delete-orphan')
    study_group_memberships = db.relationship('StudyGroupMember', backref='user', lazy=True, cascade='all, delete-orphan')
    contest_participations = db.relationship('ContestParticipant', backref='participant_user', lazy=True, cascade='all, delete-orphan')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_student(self):
        return self.role == 'student'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PlatformStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # leetcode, geeksforgeeks, hackerrank, github
    total_problems = db.Column(db.Integer, default=0)
    basic_solved = db.Column(db.Integer, default=0)  # For GeeksforGeeks basic problems
    easy_solved = db.Column(db.Integer, default=0)
    medium_solved = db.Column(db.Integer, default=0)
    hard_solved = db.Column(db.Integer, default=0)
    contest_rating = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # Easy, Medium, Hard
    category = db.Column(db.String(100))
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProblemSolved(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    solved_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken = db.Column(db.Integer)  # in minutes
    approach_notes = db.Column(db.Text)
    time_complexity = db.Column(db.String(50))
    space_complexity = db.Column(db.String(50))
    personal_rating = db.Column(db.Integer)  # 1-5 stars
    review_notes = db.Column(db.Text)
    
    problem = db.relationship('Problem', backref='solutions')

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)  # Topic for AI generation
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    difficulty = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_reviewed = db.Column(db.DateTime)
    next_review = db.Column(db.DateTime)
    repetition_count = db.Column(db.Integer, default=0)
    review_count = db.Column(db.Integer, default=0)  # Added for AI generator
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=1)
    is_ai_generated = db.Column(db.Boolean, default=False)  # Track AI generated cards

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_type = db.Column(db.String(50), nullable=False)  # coding, revision, study
    duration = db.Column(db.Integer)  # in minutes
    topics_covered = db.Column(db.Text)
    problems_solved = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class StudyGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100))
    skill_level = db.Column(db.String(20))  # Beginner, Intermediate, Advanced
    max_members = db.Column(db.Integer, default=10)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    creator = db.relationship('User', foreign_keys=[created_by])
    members = db.relationship('StudyGroupMember', backref='group', lazy=True, cascade='all, delete-orphan')

class StudyGroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='member')  # member, moderator

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    study_group_id = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=True)  # For group-specific doubts
    category = db.Column(db.String(100))
    tags = db.Column(db.String(500))  # comma-separated tags
    votes = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_solved = db.Column(db.Boolean, default=False)
    is_anonymous = db.Column(db.Boolean, default=True)  # All doubts are now anonymous
    ai_answer_deadline = db.Column(db.DateTime, nullable=True)  # 24-hour deadline for AI fallback
    
    answers = db.relationship('ForumAnswer', backref='post', lazy=True, cascade='all, delete-orphan')
    study_group = db.relationship('StudyGroup', backref='doubts')

class ForumAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for AI answers
    votes = db.Column(db.Integer, default=0)
    is_accepted = db.Column(db.Boolean, default=False)
    is_ai_generated = db.Column(db.Boolean, default=False)
    is_anonymous = db.Column(db.Boolean, default=True)  # All answers are anonymous
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author = db.relationship('User', foreign_keys=[author_id])

class AIRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recommendation_type = db.Column(db.String(50), nullable=False)  # study_plan, problem, topic
    content = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.Text)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_applied = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='ai_recommendations')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, success, warning, error
    category = db.Column(db.String(50), default='general')  # contest, forum, study_group, system
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional references to related objects
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=True)
    forum_post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=True)
    study_group_id = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    contest = db.relationship('Contest', foreign_keys=[contest_id])
    forum_post = db.relationship('ForumPost', foreign_keys=[forum_post_id])
    study_group = db.relationship('StudyGroup', foreign_keys=[study_group_id])

class DailyCodingHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='daily_coding_hours')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_date'),)

class GroupChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, image
    file_url = db.Column(db.String(500))  # for file attachments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_edited = db.Column(db.Boolean, default=False)
    
    group = db.relationship('StudyGroup', backref='chat_messages')
    user = db.relationship('User', backref='chat_messages')

class ForumPostVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'upvote' or 'downvote'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    post = db.relationship('ForumPost', backref='post_votes')
    user = db.relationship('User', foreign_keys=[user_id])
    
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_post_user_vote'),)

class ForumAnswerVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('forum_answer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'upvote' or 'downvote'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    answer = db.relationship('ForumAnswer', backref='answer_votes')
    user = db.relationship('User', foreign_keys=[user_id])
    
    __table_args__ = (db.UniqueConstraint('answer_id', 'user_id', name='unique_answer_user_vote'),)

class QuestionDiscussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_anonymous = db.Column(db.Boolean, default=True)
    
    post = db.relationship('ForumPost', backref='discussions')
    user = db.relationship('User', foreign_keys=[user_id])

# Contest System Models
class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)  # Duration in minutes
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
    problems = db.relationship('ContestProblem', backref='contest', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('ContestSubmission', backref='contest', lazy=True, cascade='all, delete-orphan')
    
    def is_live(self):
        """Check if contest is currently live"""
        now = datetime.now()  # Use local time to match contest creation
        end_time = self.start_date + timedelta(minutes=self.duration_minutes)
        return self.start_date <= now <= end_time
    
    def is_upcoming(self):
        """Check if contest is upcoming"""
        return datetime.now() < self.start_date  # Use local time to match contest creation
    
    def is_finished(self):
        """Check if contest is finished"""
        end_time = self.start_date + timedelta(minutes=self.duration_minutes)
        return datetime.now() > end_time  # Use local time to match contest creation
    
    def get_end_time(self):
        """Get contest end time"""
        return self.start_date + timedelta(minutes=self.duration_minutes)

class ContestProblem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    constraints = db.Column(db.Text)
    examples = db.Column(db.Text)  # JSON string of example inputs/outputs
    points = db.Column(db.Integer, default=100)
    time_limit = db.Column(db.Integer, default=1)  # Time limit in seconds
    memory_limit = db.Column(db.Integer, default=256)  # Memory limit in MB
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    test_cases = db.relationship('ContestTestCase', backref='problem', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('ContestSubmission', backref='problem', lazy=True, cascade='all, delete-orphan')

class ContestTestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('contest_problem.id'), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text, nullable=False)
    is_sample = db.Column(db.Boolean, default=False)  # True if visible to students
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('contest_problem.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), default='python')
    status = db.Column(db.String(20), default='pending')  # pending, running, accepted, wrong_answer, runtime_error, time_limit_exceeded
    score = db.Column(db.Integer, default=0)
    execution_time = db.Column(db.Float, default=0.0)  # Time in seconds
    memory_used = db.Column(db.Integer, default=0)  # Memory in KB
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    test_results = db.relationship('ContestTestResult', backref='submission', lazy=True, cascade='all, delete-orphan')

class ContestTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('contest_submission.id'), nullable=False)
    test_case_id = db.Column(db.Integer, db.ForeignKey('contest_test_case.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # passed, failed, error
    actual_output = db.Column(db.Text)
    error_message = db.Column(db.Text)
    execution_time = db.Column(db.Float, default=0.0)
    memory_used = db.Column(db.Integer, default=0)
    
    # Relationships
    test_case = db.relationship('ContestTestCase', foreign_keys=[test_case_id])

class ContestParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    problems_solved = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    last_submission = db.Column(db.DateTime)
    
    # Relationships
    contest = db.relationship('Contest', foreign_keys=[contest_id])
    
    __table_args__ = (db.UniqueConstraint('contest_id', 'user_id', name='unique_contest_participant'),)
