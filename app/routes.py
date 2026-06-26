from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from app.models import User, PlatformStats, Problem, ProblemSolved, Flashcard, StudySession, StudyGroup, StudyGroupMember, ForumPost, ForumAnswer, AIRecommendation, Notification, DailyCodingHours, GroupChatMessage, ForumPostVote, ForumAnswerVote, QuestionDiscussion, Contest, ContestProblem, ContestTestCase, ContestSubmission, ContestTestResult, ContestParticipant
from app.services.code_executor import CodeExecutor
from app.ai.tutor import AITutor, EnhancedAITutor
from app.services.coding_tracker import CodingTracker
from app.services.spaced_repetition import SpacedRepetitionSystem
from app.services.study_group_matcher import StudyGroupMatcher
from app.services.doubt_forum_service import DoubtForumService
from app.ai.flashcard import AIFlashcardGenerator, EnhancedAIFlashcardGenerator
from app.services.notification_service import NotificationService
from flask import jsonify
from datetime import datetime, date, timedelta
import json

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(f"Internal Server Error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.svg', mimetype='image/svg+xml')

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    try:
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error in index route: {e}")
        return f"Application Error: {e}", 500

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'student')  # Default to student
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        user = User()
        user.username = username
        user.email = email
        user.role = role
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create welcome notification and notify about existing forum posts
        create_notification(
            user_id=user.id,
            title='🏆 Welcome to CodeMentor AI!',
            message='Welcome to the platform! You will receive notifications for contests, forum posts, and study group activities. Check out existing questions in the forum and join study groups to start learning!',
            notification_type='success',
            category='welcome'
        )
        
        # Notify about existing unanswered forum questions
        existing_posts = ForumPost.query.filter(ForumPost.author_id != user.id).all()
        if existing_posts:
            for post in existing_posts[:5]:  # Limit to 5 most recent
                create_notification(
                    user_id=user.id,
                    title='❓ Question Waiting for Answer',
                    message=f'Help the community! There is a question in the forum:\\n📝 {post.title}\\n👤 By: {post.author.username}\\n💭 Share your knowledge and help solve this doubt!',
                    notification_type='info',
                    category='forum',
                    forum_post_id=post.id
                )
        
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Registration successful!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    platform_stats = PlatformStats.query.filter_by(user_id=user.id).all()
    recent_sessions = StudySession.query.filter_by(user_id=user.id).order_by(StudySession.started_at.desc()).limit(10).all()
    recent_problems = ProblemSolved.query.filter_by(user_id=user.id).order_by(ProblemSolved.solved_at.desc()).limit(5).all()
    study_sessions = StudySession.query.filter_by(user_id=user.id).order_by(StudySession.started_at.desc()).all()
    
    # Calculate total problems solved
    total_problems = sum(stat.total_problems or 0 for stat in platform_stats)
    
    # Calculate total study time
    total_study_time = sum(session.duration or 0 for session in study_sessions)
    
    # Ensure duration is not None for sessions
    for session_obj in recent_sessions:
        if session_obj.duration is None:
            session_obj.duration = 0
    
    return render_template('dashboard.html', 
                         user=user, 
                         platform_stats=platform_stats,
                         recent_sessions=recent_sessions,
                         recent_problems=recent_problems,
                         study_sessions=study_sessions,
                         total_problems=total_problems,
                         total_study_time=total_study_time)

@app.route('/coding')
@login_required
def coding():
    user = User.query.get(session['user_id'])
    tracker = CodingTracker()
    platform_stats = PlatformStats.query.filter_by(user_id=user.id).all()
    problems = Problem.query.all()
    user_solutions = ProblemSolved.query.filter_by(user_id=user.id).all()
    
    return render_template('coding.html', 
                         user=user, 
                         platform_stats=platform_stats,
                         problems=problems,
                         user_solutions=user_solutions)

@app.route('/sync_platform', methods=['POST'])
@login_required
def sync_platform():
    platform = request.form.get('platform')
    username = request.form.get('username')
    
    if not platform or not username:
        flash('Platform and username are required', 'error')
        return redirect(url_for('coding'))
    
    user = User.query.get(session['user_id'])
    tracker = CodingTracker()
    
    try:
        # Update user's platform username
        if platform == 'leetcode':
            user.leetcode_username = username
        elif platform == 'geeksforgeeks':
            user.geeksforgeeks_profile = username
        elif platform == 'hackerrank':
            user.hackerrank_username = username
        elif platform == 'github':
            user.github_username = username
        
        # Sync platform data
        stats = tracker.sync_platform_data(user.id, platform, username)
        
        db.session.commit()
        flash(f'Successfully synced {platform} data!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error syncing {platform}: {str(e)}', 'error')
    
    return redirect(url_for('coding'))

@app.route('/ai_tutor')
@login_required
def ai_tutor():
    user = User.query.get(session['user_id'])
    enhanced_ai_tutor = EnhancedAITutor()
    recommendations = AIRecommendation.query.filter_by(user_id=user.id).order_by(AIRecommendation.created_at.desc()).limit(10).all()
    
    return render_template('ai_tutor.html', user=user, recommendations=recommendations)

@app.route('/text_chat', methods=['POST'])
@login_required
def text_chat():
    """Text chatbot for answering coding questions"""
    user = User.query.get(session['user_id'])
    enhanced_ai_tutor = EnhancedAITutor()
    user_message = request.form.get('message', '').strip()
    
    if not user_message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    
    try:
        # Use the chat_with_tutor method for direct question answering
        ai_response = enhanced_ai_tutor.chat_with_tutor(user.id, user_message)
        
        # Save the interaction
        ai_rec = AIRecommendation()
        ai_rec.user_id = user.id
        ai_rec.recommendation_type = 'text_chat'
        ai_rec.content = ai_response
        ai_rec.extra_data = json.dumps({'question': user_message})
        db.session.add(ai_rec)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'response': ai_response,
            'message': 'AI responded successfully'
        })
    except Exception as e:
        app.logger.error(f"Error in text_chat: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'response': 'Sorry, I encountered an error while processing your question. Please try again.'
        })

@app.route('/generate_video', methods=['POST'])
@login_required
def generate_video():
    """Search for YouTube videos or generate educational content for programming topics"""
    user = User.query.get(session['user_id'])
    enhanced_ai_tutor = EnhancedAITutor()
    topic = request.form.get('topic', '').strip()
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic cannot be empty'})
    
    try:
        # First, search for real YouTube videos on the topic  
        search_query = f"{topic} tutorial YouTube programming coding"
        
        try:
            # Use web search to find real YouTube videos
            import subprocess
            import json
            
            # For now, provide curated real YouTube videos for common programming topics
            # These are actual, clickable YouTube videos from popular educational channels
            
            # Curated real YouTube videos from popular educational channels
            youtube_videos = []
            
            # Find matching videos based on topic
            topic_lower = topic.lower()
            if 'python' in topic_lower and 'loop' in topic_lower:
                youtube_videos = [{
                    'title': 'Python For Loops Tutorial - Programming with Mosh',
                    'url': 'https://www.youtube.com/watch?v=6iF8Xb7Z3wQ',
                    'description': 'Learn Python for loops with clear examples and practical applications from one of the best programming instructors.'
                }, {
                    'title': 'Python For Loop Tutorial - Corey Schafer',
                    'url': 'https://www.youtube.com/watch?v=0hhfLnDUJzM', 
                    'description': 'Comprehensive Python for loop tutorial covering all the basics and advanced techniques with real-world examples.'
                }, {
                    'title': 'Python Loops Explained - freeCodeCamp',
                    'url': 'https://www.youtube.com/watch?v=OnDr4J2UXSA',
                    'description': 'Complete guide to Python loops including for loops, while loops, and nested loops with hands-on coding examples.'
                }]
            elif 'python' in topic_lower:
                    youtube_videos = [{
                        'title': 'Python Tutorial for Beginners - Programming with Mosh',
                        'url': 'https://www.youtube.com/watch?v=_uQrJ0TkZlc',
                        'description': 'Complete Python course for beginners covering all fundamentals.'
                    }, {
                        'title': 'Python Full Course - freeCodeCamp',
                        'url': 'https://www.youtube.com/watch?v=rfscVS0vtbw',
                        'description': 'Learn Python programming from scratch with this comprehensive tutorial.'
                    }]
            elif 'javascript' in topic_lower:
                    youtube_videos = [{
                        'title': 'JavaScript Tutorial for Beginners - Programming with Mosh',
                        'url': 'https://www.youtube.com/watch?v=PkZNo7MFNFg',
                        'description': 'Complete JavaScript course covering all the fundamentals and modern features.'
                    }, {
                        'title': 'JavaScript Full Course - freeCodeCamp',
                        'url': 'https://www.youtube.com/watch?v=jS4aFq5-91M',
                        'description': 'Learn JavaScript from beginner to advanced with practical examples.'
                    }]
            elif any(word in topic_lower for word in ['html', 'css', 'web']):
                    youtube_videos = [{
                        'title': 'HTML & CSS Tutorial - SuperSimpleDev',
                        'url': 'https://www.youtube.com/watch?v=G3e-cpL7ofc',
                        'description': 'Learn HTML and CSS fundamentals to build modern websites.'
                    }, {
                        'title': 'HTML Tutorial for Beginners - Programming with Mosh',
                        'url': 'https://www.youtube.com/watch?v=qz0aGYrrlhU',
                        'description': 'Complete HTML tutorial covering all essential concepts and tags.'
                    }]
            
            # If we found YouTube videos, return them
            if youtube_videos:
                # Show only the best video (or max 2 if multiple good ones)
                best_videos = youtube_videos[:1]  # Show only 1 video
                
                video_response = f"""🎥 **YouTube Tutorial Found for: {topic}**

<a href="{best_videos[0]['url']}" target="_blank" style="color: #4FC3F7; text-decoration: underline; font-weight: bold;">{best_videos[0]['title']}</a>

{best_videos[0]['description']}"""
                
                # Save the interaction
                ai_rec = AIRecommendation()
                ai_rec.user_id = user.id
                ai_rec.recommendation_type = 'video_search'
                ai_rec.content = video_response
                ai_rec.extra_data = json.dumps({'topic': topic, 'videos_found': len(youtube_videos)})
                db.session.add(ai_rec)
                db.session.commit()
                
                return jsonify({
                    'success': True, 
                    'video_content': video_response,
                    'message': f'Found {len(youtube_videos)} YouTube videos for "{topic}"!'
                })
                
        except Exception as search_error:
            app.logger.warning(f"YouTube search failed: {str(search_error)}")
        
        # Fallback: If no videos found or search failed, generate AI content
        video_prompt = f"""Create an engaging tutorial for: {topic}

Format this as if you're a friendly programming instructor. Use conversational language and structure it like a comprehensive lesson.

Structure:
🎬 Introduction & What You'll Learn
📖 Concept Explanation  
💻 Live Coding Examples
⚠️ Common Mistakes to Avoid
🏋️ Practice Challenges
🎯 Summary & Next Steps

Make it conversational, engaging, and include step-by-step code explanations."""
        
        video_content = enhanced_ai_tutor.chat_with_tutor(user.id, video_prompt)
        
        # Format fallback response
        video_response = f"""❌ **No YouTube Videos Available for: {topic}**

Sorry, we couldn't find any YouTube videos for this topic. Here's a written tutorial instead:

{video_content}

Ask me specific questions about {topic} if you need clarification on any concept."""
        
        # Save the interaction
        ai_rec = AIRecommendation()
        ai_rec.user_id = user.id
        ai_rec.recommendation_type = 'video_fallback'
        ai_rec.content = video_response
        ai_rec.extra_data = json.dumps({'topic': topic, 'fallback_reason': 'no_youtube_videos'})
        db.session.add(ai_rec)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'video_content': video_response,
            'message': f'No videos found for "{topic}", but here\'s a comprehensive tutorial!'
        })
        
    except Exception as e:
        app.logger.error(f"Error in generate_video: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e),
            'video_content': f'Sorry, I encountered an error while searching for videos about "{topic}". Please try again.'
        })

@app.route('/revision')
@login_required
def revision():
    user = User.query.get(session['user_id'])
    ai_generator = AIFlashcardGenerator()
    
    # Get topics with flashcard counts and due dates
    topics = ai_generator.get_topics_by_user(user.id)
    topic_info = []
    
    for topic in topics:
        cards = ai_generator.get_flashcards_by_topic(user.id, topic)
        due_cards = [c for c in cards if c.next_review and c.next_review <= datetime.utcnow()]
        next_review = min([c.next_review for c in cards if c.next_review], default=None)
        
        topic_info.append({
            'topic': topic,
            'count': len(cards),
            'due_count': len(due_cards),
            'next_review': next_review
        })
    
    due_cards = ai_generator.get_due_flashcards(user.id)
    total_cards = Flashcard.query.filter_by(user_id=user.id).count()
    
    return render_template('revision.html', 
                         user=user, 
                         due_cards=due_cards,
                         total_cards=total_cards,
                         topics=topic_info)

@app.route('/create_flashcard', methods=['POST'])
@login_required
def create_flashcard():
    topic = request.form.get('topic')
    question = request.form.get('question')
    answer = request.form.get('answer')
    category = request.form.get('category', 'General')
    difficulty = request.form.get('difficulty', 'Medium')
    
    if not topic or not question or not answer:
        flash('Topic, question and answer are required', 'error')
        return redirect(url_for('revision'))
    
    flashcard = Flashcard()
    flashcard.user_id = session['user_id']
    flashcard.topic = topic
    flashcard.question = question
    flashcard.answer = answer
    flashcard.category = category
    flashcard.difficulty = difficulty
    flashcard.is_ai_generated = False
    flashcard.next_review = datetime.utcnow() + timedelta(days=1)
    
    db.session.add(flashcard)
    db.session.commit()
    flash('Flashcard created successfully!', 'success')
    
    return redirect(url_for('revision'))

@app.route('/ai_generate_flashcards', methods=['POST'])
@login_required
def ai_generate_flashcards():
    topic = request.form.get('topic')
    difficulty_level = request.form.get('difficulty_level', 'intermediate')
    
    if not topic:
        flash('Topic is required for AI generation', 'error')
        return redirect(url_for('revision'))
    
    try:
        # Use enhanced AI flashcard generator with free providers
        enhanced_ai_generator = EnhancedAIFlashcardGenerator()
        result = enhanced_ai_generator.generate_flashcards_for_topic(
            topic=topic,
            user_id=session['user_id'],
            difficulty_level=difficulty_level
        )
        
        if result['success']:
            flash(f'Successfully generated {result["total_generated"]} AI flashcards for {topic} using free AI providers!', 'success')
            if result.get("suggested_schedule"):
                flash(f'Suggested review schedule: {result["suggested_schedule"]}', 'info')
        else:
            flash(f'Error generating flashcards: {result["error"]}', 'error')
            
    except Exception as e:
        flash(f'Unexpected error: {str(e)}', 'error')
    
    return redirect(url_for('revision'))

@app.route('/review_flashcard/<int:card_id>', methods=['POST'])
@login_required
def review_flashcard(card_id):
    card = Flashcard.query.get_or_404(card_id)
    if card.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('revision'))
    
    quality = int(request.form.get('quality', 3))  # 1-5 rating
    ai_generator = AIFlashcardGenerator()
    ai_generator.update_flashcard_after_review(card_id, quality)
    
    flash('Flashcard reviewed!', 'success')
    return redirect(url_for('revision'))

@app.route('/rate_flashcard', methods=['POST'])
@login_required
def rate_flashcard():
    """Rate a flashcard for spaced repetition algorithm"""
    card_id = request.form.get('card_id')
    rating = int(request.form.get('rating', 3))
    
    if not card_id:
        return jsonify({'success': False, 'error': 'Card ID is required'})
    
    try:
        flashcard = Flashcard.query.get(card_id)
        if not flashcard or flashcard.user_id != session['user_id']:
            return jsonify({'success': False, 'error': 'Flashcard not found'})
        
        # Update spaced repetition data based on rating
        # Rating: 1=Again, 2=Hard, 3=Good, 4=Easy
        flashcard.last_reviewed = datetime.utcnow()
        flashcard.review_count += 1
        
        if rating == 1:  # Again - review soon
            flashcard.interval = 1
            flashcard.ease_factor = max(1.3, flashcard.ease_factor - 0.2)
        elif rating == 2:  # Hard - review sooner than usual
            flashcard.interval = max(1, int(flashcard.interval * 0.6))
            flashcard.ease_factor = max(1.3, flashcard.ease_factor - 0.15)
        elif rating == 3:  # Good - normal interval
            flashcard.interval = int(flashcard.interval * flashcard.ease_factor)
        elif rating == 4:  # Easy - longer interval
            flashcard.interval = int(flashcard.interval * flashcard.ease_factor * 1.3)
            flashcard.ease_factor = min(2.5, flashcard.ease_factor + 0.15)
        
        # Calculate next review date
        flashcard.next_review = datetime.utcnow() + timedelta(days=flashcard.interval)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'next_review': flashcard.next_review.strftime('%Y-%m-%d'),
            'interval': flashcard.interval
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/review_topic/<topic>')
@login_required  
def review_topic(topic):
    ai_generator = AIFlashcardGenerator()
    cards = ai_generator.get_flashcards_by_topic(session['user_id'], topic)
    due_cards = [c for c in cards if c.next_review and c.next_review <= datetime.utcnow()]
    
    if not due_cards:
        flash('No cards due for review in this topic', 'info')
        return redirect(url_for('revision'))
    
    return render_template('review_flashcards.html', 
                         user=User.query.get(session['user_id']),
                         cards=due_cards,
                         total_cards=len(cards),
                         current_topic=topic,
                         review_type='due')

@app.route('/revise_early/<topic>')
@login_required  
def revise_early(topic):
    """Allow users to review all flashcards for a topic anytime, not just when due"""
    ai_generator = AIFlashcardGenerator()
    cards = ai_generator.get_flashcards_by_topic(session['user_id'], topic)
    
    if not cards:
        flash('No flashcards found for this topic', 'info')
        return redirect(url_for('revision'))
    
    return render_template('review_flashcards.html', 
                         user=User.query.get(session['user_id']),
                         cards=cards,
                         total_cards=len(cards),
                         current_topic=topic,
                         review_type='early')

@app.route('/edit_topic_cards/<topic>')
@login_required
def edit_topic_cards(topic):
    ai_generator = AIFlashcardGenerator()
    cards = ai_generator.get_flashcards_by_topic(session['user_id'], topic)
    
    return render_template('edit_flashcards.html',
                         user=User.query.get(session['user_id']),
                         cards=cards,
                         topic=topic)

@app.route('/edit_flashcard/<int:card_id>', methods=['POST'])
@login_required
def edit_flashcard(card_id):
    card = Flashcard.query.get_or_404(card_id)
    if card.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('revision'))
    
    card.question = request.form.get('question', card.question)
    card.answer = request.form.get('answer', card.answer)
    card.difficulty = request.form.get('difficulty', card.difficulty)
    
    db.session.commit()
    flash('Flashcard updated successfully!', 'success')
    
    return redirect(url_for('edit_topic_cards', topic=card.topic))

@app.route('/study_groups')
@login_required
def study_groups():
    user = User.query.get(session['user_id'])
    matcher = StudyGroupMatcher()
    
    all_groups = StudyGroup.query.filter_by(is_active=True).all()
    user_groups = StudyGroup.query.join(StudyGroupMember).filter(StudyGroupMember.user_id == user.id).all()
    recommended_groups = matcher.find_matching_groups(user.id)
    
    # Get public forum posts (not group-specific)
    public_forum_posts = ForumPost.query.filter_by(study_group_id=None).order_by(ForumPost.created_at.desc()).limit(10).all()
    
    return render_template('study_groups.html', 
                         user=user,
                         all_groups=all_groups,
                         user_groups=user_groups,
                         recommended_groups=recommended_groups,
                         forum_posts=public_forum_posts)

@app.route('/create_study_group', methods=['POST'])
@login_required
def create_study_group():
    name = request.form.get('name')
    description = request.form.get('description')
    topic = request.form.get('topic')
    skill_level = request.form.get('skill_level')
    max_members = int(request.form.get('max_members', 10))
    
    if not name or not topic:
        flash('Name and topic are required', 'error')
        return redirect(url_for('study_groups'))
    
    group = StudyGroup()
    group.name = name
    group.description = description
    group.topic = topic
    group.skill_level = skill_level
    group.max_members = max_members
    group.created_by = session['user_id']
    
    db.session.add(group)
    db.session.flush()  # Get the group ID
    
    # Add creator as a member
    member = StudyGroupMember()
    member.group_id = group.id
    member.user_id = session['user_id']
    member.role = 'moderator'
    db.session.add(member)
    db.session.commit()
    
    flash('Study group created successfully!', 'success')
    return redirect(url_for('study_groups'))

@app.route('/join_study_group/<int:group_id>')
@login_required
def join_study_group(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    # Check if already a member
    existing_member = StudyGroupMember.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
    if existing_member:
        flash('You are already a member of this group', 'info')
        return redirect(url_for('study_groups'))
    
    # Check if group is full
    current_members = StudyGroupMember.query.filter_by(group_id=group_id).count()
    if current_members >= group.max_members:
        flash('This study group is full', 'error')
        return redirect(url_for('study_groups'))
    
    member = StudyGroupMember()
    member.group_id = group_id
    member.user_id = session['user_id']
    db.session.add(member)
    db.session.commit()
    
    flash(f'Successfully joined {group.name}!', 'success')
    return redirect(url_for('study_groups'))

@app.route('/doubts')
@login_required
def doubts():
    user = User.query.get(session['user_id'])
    forum_service = DoubtForumService()
    
    posts = ForumPost.query.order_by(ForumPost.created_at.desc()).all()
    categories = ['Data Structures', 'Algorithms', 'System Design', 'Database', 'Web Development', 'Other']
    
    return render_template('doubts.html', 
                         user=user,
                         posts=posts,
                         categories=categories)

@app.route('/create_doubt', methods=['POST'])
@login_required
def create_doubt():
    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category')
    tags = request.form.get('tags', '')
    
    if not title or not content:
        flash('Title and content are required', 'error')
        return redirect(url_for('doubts'))
    
    post = ForumPost()
    post.title = title
    post.content = content
    post.author_id = session['user_id']
    post.category = category
    post.tags = tags
    
    db.session.add(post)
    db.session.commit()
    
    # Send notification to all users about new forum question
    NotificationService.notify_forum_question_posted(post)
    
    flash('Question posted successfully!', 'success')
    return redirect(url_for('doubts'))

@app.route('/doubt/<int:post_id>')
@login_required
def doubt_detail(post_id):
    post = ForumPost.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    
    answers = ForumAnswer.query.filter_by(post_id=post_id).order_by(ForumAnswer.votes.desc()).all()
    
    return render_template('doubt_detail.html', post=post, answers=answers)

@app.route('/answer_doubt/<int:post_id>', methods=['POST'])
@login_required
def answer_doubt(post_id):
    content = request.form.get('content')
    
    if not content:
        flash('Answer content is required', 'error')
        return redirect(url_for('doubt_detail', post_id=post_id))
    
    answer = ForumAnswer()
    answer.post_id = post_id
    answer.content = content
    answer.author_id = session['user_id']
    
    db.session.add(answer)
    db.session.commit()
    
    # Send notification to the question author
    forum_post = ForumPost.query.get(post_id)
    answer_author = User.query.get(session['user_id'])
    if forum_post and answer_author:
        NotificationService.notify_forum_answer_posted(forum_post, answer_author)
    
    flash('Answer posted successfully!', 'success')
    return redirect(url_for('doubt_detail', post_id=post_id))

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])
    
    user.first_name = request.form.get('first_name', '')
    user.last_name = request.form.get('last_name', '')
    user.bio = request.form.get('bio', '')
    user.learning_goals = request.form.get('learning_goals', '')
    user.target_companies = request.form.get('target_companies', '')
    user.preferred_schedule = request.form.get('preferred_schedule', '')
    user.leetcode_username = request.form.get('leetcode_username', '')
    user.geeksforgeeks_profile = request.form.get('geeksforgeeks_profile', '')
    user.hackerrank_username = request.form.get('hackerrank_username', '')
    user.github_username = request.form.get('github_username', '')
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    
    return redirect(url_for('profile'))



@app.route('/start_study_session', methods=['POST'])
@login_required
def start_study_session():
    session_type = request.form.get('type', 'coding')
    topics = request.form.get('topics', '')
    
    study_session = StudySession()
    study_session.user_id = session['user_id']
    study_session.session_type = session_type
    study_session.topics_covered = topics
    
    db.session.add(study_session)
    db.session.commit()
    
    session['active_session_id'] = study_session.id
    flash('Study session started!', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/end_study_session', methods=['POST'])
@login_required
def end_study_session():
    session_id = session.get('active_session_id')
    if not session_id:
        flash('No active study session', 'error')
        return redirect(url_for('dashboard'))
    
    study_session = StudySession.query.get(session_id)
    if study_session and study_session.user_id == session['user_id']:
        duration = int(request.form.get('duration', 0))
        problems_solved = int(request.form.get('problems_solved', 0))
        notes = request.form.get('notes', '')
        
        study_session.duration = duration
        study_session.problems_solved = problems_solved
        study_session.notes = notes
        study_session.completed_at = datetime.utcnow()
        
        db.session.commit()
        session.pop('active_session_id', None)
        flash('Study session completed!', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/submit_daily_hours', methods=['POST'])
@login_required
def submit_daily_hours():
    try:
        data = request.get_json()
        hours = float(data.get('hours', 0))
        
        if hours < 0 or hours > 24:
            return jsonify({'success': False, 'error': 'Hours must be between 0 and 24'})
        
        user_id = session['user_id']
        today = date.today()
        
        # Check if entry already exists for today
        existing = DailyCodingHours.query.filter_by(user_id=user_id, date=today).first()
        
        if existing:
            existing.hours = hours
        else:
            daily_hours = DailyCodingHours()
            daily_hours.user_id = user_id
            daily_hours.date = today
            daily_hours.hours = hours
            db.session.add(daily_hours)
        
        db.session.commit()
        create_notification(user_id, 'Hours Recorded', f'Logged {hours} coding hours for today', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/notifications')
def get_notifications():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'error': 'Not authenticated',
            'notifications': []
        }), 401
    
    try:
        user_id = session['user_id']
        notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(20).all()
        
        return jsonify({
            'success': True,
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'category': n.category,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'contest_id': getattr(n, 'contest_id', None),
                'forum_post_id': getattr(n, 'forum_post_id', None),
                'study_group_id': getattr(n, 'study_group_id', None)
            } for n in notifications]
        })
    except Exception as e:
        app.logger.error(f"Error in get_notifications: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'notifications': []
        }), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['user_id']
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        
        if notification:
            notification.is_read = True
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    except Exception as e:
        app.logger.error(f"Error marking notification as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def create_notification(user_id, title, message, notification_type='info', category='general', contest_id=None, forum_post_id=None, study_group_id=None):
    """Helper function to create notifications"""
    try:
        notification = Notification()
        notification.user_id = user_id
        notification.title = title
        notification.message = message
        notification.type = notification_type
        notification.category = category
        notification.contest_id = contest_id
        notification.forum_post_id = forum_post_id
        notification.study_group_id = study_group_id
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        app.logger.error(f"Error creating notification: {e}")
        db.session.rollback()
        return None

# Enhanced Study Group Routes
@app.route('/group_chat/<int:group_id>')
@login_required
def group_chat(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    # Check if user is a member of the group
    member = StudyGroupMember.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
    if not member:
        flash('You must be a member to access group chat', 'error')
        return redirect(url_for('study_groups'))
    
    # Get chat messages
    messages = GroupChatMessage.query.filter_by(group_id=group_id).order_by(GroupChatMessage.created_at.asc()).limit(100).all()
    
    # Get group doubts (forum posts specific to this group)
    group_doubts = ForumPost.query.filter_by(study_group_id=group_id).order_by(ForumPost.created_at.desc()).all()
    
    return render_template('group_chat.html', group=group, messages=messages, group_doubts=group_doubts, member=member)

@app.route('/send_group_message/<int:group_id>', methods=['POST'])
@login_required
def send_group_message(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    # Check if user is a member
    member = StudyGroupMember.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
    if not member:
        return jsonify({'success': False, 'error': 'Not a member'})
    
    message_text = request.form.get('message', '').strip()
    if not message_text:
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    
    message = GroupChatMessage()
    message.group_id = group_id
    message.user_id = session['user_id']
    message.message = message_text
    
    db.session.add(message)
    db.session.commit()
    
    # Send notification to group members about new message
    sender = User.query.get(session['user_id'])
    NotificationService.notify_study_group_message(message_text, group, sender)
    
    return jsonify({'success': True, 'message': {
        'id': message.id,
        'message': message.message,
        'username': message.user.username,
        'created_at': message.created_at.isoformat()
    }})

@app.route('/create_group_doubt/<int:group_id>', methods=['POST'])
@login_required
def create_group_doubt(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    # Check if user is a member
    member = StudyGroupMember.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
    if not member:
        flash('You must be a member to post doubts', 'error')
        return redirect(url_for('study_groups'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    category = request.form.get('category')
    tags = request.form.get('tags', '')
    
    if not title or not content:
        flash('Title and content are required', 'error')
        return redirect(url_for('group_chat', group_id=group_id))
    
    post = ForumPost()
    post.title = title
    post.content = content
    post.author_id = session['user_id']
    post.study_group_id = group_id
    post.category = category
    post.tags = tags
    post.is_anonymous = True
    # Set AI deadline to 24 hours from now
    post.ai_answer_deadline = datetime.utcnow() + timedelta(hours=24)
    
    db.session.add(post)
    db.session.commit()
    
    # Send notification to group members about new question
    NotificationService.notify_study_group_question(post, group)
    
    flash('Anonymous doubt posted successfully!', 'success')
    
    return redirect(url_for('group_chat', group_id=group_id))

# Enhanced Forum Routes with Voting
@app.route('/vote_post/<int:post_id>/<vote_type>', methods=['POST'])
@login_required
def vote_post(post_id, vote_type):
    if vote_type not in ['upvote', 'downvote']:
        return jsonify({'success': False, 'error': 'Invalid vote type'})
    
    post = ForumPost.query.get_or_404(post_id)
    user_id = session['user_id']
    
    # Check if user already voted
    existing_vote = ForumPostVote.query.filter_by(post_id=post_id, user_id=user_id).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote if same type
            db.session.delete(existing_vote)
            vote_change = -1 if vote_type == 'upvote' else 1
        else:
            # Change vote type
            existing_vote.vote_type = vote_type
            vote_change = 2 if vote_type == 'upvote' else -2
    else:
        # Create new vote
        vote = ForumPostVote()
        vote.post_id = post_id
        vote.user_id = user_id
        vote.vote_type = vote_type
        db.session.add(vote)
        vote_change = 1 if vote_type == 'upvote' else -1
    
    # Update post votes count
    post.votes = (post.votes or 0) + vote_change
    db.session.commit()
    
    return jsonify({'success': True, 'new_vote_count': post.votes})

@app.route('/vote_answer/<int:answer_id>/<vote_type>', methods=['POST'])
@login_required
def vote_answer(answer_id, vote_type):
    if vote_type not in ['upvote', 'downvote']:
        return jsonify({'success': False, 'error': 'Invalid vote type'})
    
    answer = ForumAnswer.query.get_or_404(answer_id)
    user_id = session['user_id']
    
    # Check if user already voted
    existing_vote = ForumAnswerVote.query.filter_by(answer_id=answer_id, user_id=user_id).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote if same type
            db.session.delete(existing_vote)
            vote_change = -1 if vote_type == 'upvote' else 1
        else:
            # Change vote type
            existing_vote.vote_type = vote_type
            vote_change = 2 if vote_type == 'upvote' else -2
    else:
        # Create new vote
        vote = ForumAnswerVote()
        vote.answer_id = answer_id
        vote.user_id = user_id
        vote.vote_type = vote_type
        db.session.add(vote)
        vote_change = 1 if vote_type == 'upvote' else -1
    
    # Update answer votes count
    answer.votes = (answer.votes or 0) + vote_change
    db.session.commit()
    
    return jsonify({'success': True, 'new_vote_count': answer.votes})

@app.route('/add_discussion/<int:post_id>', methods=['POST'])
@login_required
def add_discussion(post_id):
    post = ForumPost.query.get_or_404(post_id)
    message = request.form.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'error': 'Message cannot be empty'})
    
    discussion = QuestionDiscussion()
    discussion.post_id = post_id
    discussion.user_id = session['user_id']
    discussion.message = message
    discussion.is_anonymous = True
    
    db.session.add(discussion)
    db.session.commit()
    
    return jsonify({'success': True, 'discussion': {
        'id': discussion.id,
        'message': discussion.message,
        'created_at': discussion.created_at.isoformat(),
        'is_anonymous': discussion.is_anonymous
    }})

@app.route('/enhanced_doubt_detail/<int:post_id>')
@login_required
def enhanced_doubt_detail(post_id):
    post = ForumPost.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    
    # Get answers with vote counts
    answers = ForumAnswer.query.filter_by(post_id=post_id).order_by(ForumAnswer.votes.desc()).all()
    
    # Get discussions for this question
    discussions = QuestionDiscussion.query.filter_by(post_id=post_id).order_by(QuestionDiscussion.created_at.asc()).all()
    
    # Check if user has voted on this post
    user_vote = ForumPostVote.query.filter_by(post_id=post_id, user_id=session['user_id']).first()
    
    # Get answer votes for user
    answer_votes = {}
    if answers:
        user_answer_votes = ForumAnswerVote.query.filter(
            ForumAnswerVote.answer_id.in_([a.id for a in answers]),
            ForumAnswerVote.user_id == session['user_id']
        ).all()
        answer_votes = {v.answer_id: v.vote_type for v in user_answer_votes}
    
    return render_template('enhanced_doubt_detail.html', 
                         post=post, 
                         answers=answers, 
                         discussions=discussions,
                         user_vote=user_vote,
                         answer_votes=answer_votes)

# AI Fallback for unanswered questions
@app.route('/check_ai_fallback')
@login_required
def check_ai_fallback():
    """Background task to check for questions that need AI answers"""
    current_time = datetime.utcnow()
    
    # Find posts that are past AI deadline and don't have answers
    unanswered_posts = ForumPost.query.filter(
        ForumPost.ai_answer_deadline <= current_time,
        ForumPost.is_solved == False,
        ~ForumPost.answers.any(ForumAnswer.is_ai_generated == True)
    ).all()
    
    enhanced_ai_tutor = EnhancedAITutor()
    
    for post in unanswered_posts:
        try:
            # Generate AI answer
            ai_response = enhanced_ai_tutor.get_recommendation(
                post.author_id, 
                'general', 
                f"Question: {post.title}\n\nDetails: {post.content}\n\nCategory: {post.category}"
            )
            
            # Create AI answer
            ai_answer = ForumAnswer()
            ai_answer.post_id = post.id
            ai_answer.content = ai_response
            ai_answer.author_id = None  # AI answer has no human author
            ai_answer.is_ai_generated = True
            ai_answer.is_anonymous = True
            
            db.session.add(ai_answer)
            
            # Mark post as having AI fallback
            post.is_solved = True
            
        except Exception as e:
            app.logger.error(f"Failed to generate AI answer for post {post.id}: {e}")
    
    db.session.commit()
    return jsonify({'success': True, 'processed': len(unanswered_posts)})

# Better group visibility and joining
@app.route('/leave_study_group/<int:group_id>', methods=['POST'])
@login_required
def leave_study_group(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = StudyGroupMember.query.filter_by(group_id=group_id, user_id=session['user_id']).first()
    
    if not member:
        flash('You are not a member of this group', 'error')
        return redirect(url_for('study_groups'))
    
    # Don't allow creator to leave if there are other members
    if group.created_by == session['user_id']:
        other_members = StudyGroupMember.query.filter(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id != session['user_id']
        ).count()
        
        if other_members > 0:
            flash('You cannot leave a group as creator while other members exist. Transfer ownership first.', 'error')
            return redirect(url_for('study_groups'))
    
    db.session.delete(member)
    db.session.commit()
    
    flash(f'Successfully left {group.name}', 'info')
    return redirect(url_for('study_groups'))

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.route('/ai_provider_status')
@login_required
def ai_provider_status():
    """Show status of available AI providers"""
    try:
        enhanced_tutor = EnhancedAITutor()
        enhanced_flashcard = EnhancedAIFlashcardGenerator()
        
        provider_status = enhanced_tutor.test_ai_providers()
        available_providers = enhanced_tutor.get_available_ai_providers()
        
        return jsonify({
            'success': True,
            'available_providers': available_providers,
            'provider_status': provider_status,
            'message': 'AI providers status retrieved successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'available_providers': ['local_samples'],
            'message': 'Using local fallback responses'
        })

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Contest System Routes
@app.route('/contests')
@login_required
def contests():
    """Main contests page showing all contests based on user role"""
    user = User.query.get(session['user_id'])
    current_time = datetime.now()  # Use local time to match contest creation
    
    if user.is_admin():
        # Admin view - show all contests they created
        contests = Contest.query.filter_by(created_by=user.id).order_by(Contest.start_date.desc()).all()
        return render_template('contests_admin.html', contests=contests, user=user)
    else:
        # Student view - show upcoming and live contests
        upcoming_contests = Contest.query.filter(Contest.start_date > current_time, Contest.is_active == True).order_by(Contest.start_date.asc()).all()
        live_contests = []
        finished_contests = []
        
        # Get all contests and filter in Python for now (can optimize later)
        all_contests = Contest.query.filter_by(is_active=True).all()
        for contest in all_contests:
            end_time = contest.start_date + timedelta(minutes=contest.duration_minutes)
            if contest.start_date <= current_time <= end_time:
                live_contests.append(contest)
            elif end_time < current_time:
                finished_contests.append(contest)
        
        # Sort finished contests by date descending, limit to 10
        finished_contests.sort(key=lambda x: x.start_date, reverse=True)
        finished_contests = finished_contests[:10]
        
        return render_template('contests_student.html', 
                             upcoming_contests=upcoming_contests,
                             live_contests=live_contests,
                             finished_contests=finished_contests,
                             user=user)

@app.route('/contest/create', methods=['GET', 'POST'])
@admin_required
def create_contest():
    """Admin route to create a new contest"""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        start_date_str = request.form['start_date']
        start_time_str = request.form['start_time']
        duration_minutes = int(request.form['duration_minutes'])
        
        # Parse datetime
        start_datetime_str = f"{start_date_str} {start_time_str}"
        start_date = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
        
        # Create contest
        contest = Contest()
        contest.title = title
        contest.description = description
        contest.start_date = start_date
        contest.duration_minutes = duration_minutes
        contest.created_by = session['user_id']
        
        db.session.add(contest)
        db.session.commit()
        
        # Send notification to all students about new contest
        NotificationService.notify_contest_created(contest)
        
        flash('Contest created successfully!', 'success')
        return redirect(url_for('contest_edit', contest_id=contest.id))
    
    return render_template('contest_create.html')

@app.route('/contest/<int:contest_id>/edit')
@admin_required
def contest_edit(contest_id):
    """Admin route to edit contest and add problems"""
    contest = Contest.query.get_or_404(contest_id)
    
    # Check if user is the creator
    if contest.created_by != session['user_id']:
        flash('You can only edit contests you created', 'error')
        return redirect(url_for('contests'))
    
    problems = ContestProblem.query.filter_by(contest_id=contest_id).all()
    return render_template('contest_edit.html', contest=contest, problems=problems)

@app.route('/contest/<int:contest_id>/add_problem', methods=['POST'])
@admin_required
def add_contest_problem(contest_id):
    """Admin route to add a problem to contest"""
    contest = Contest.query.get_or_404(contest_id)
    
    if contest.created_by != session['user_id']:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    title = request.form['title']
    description = request.form['description']
    constraints = request.form.get('constraints', '')
    examples = request.form.get('examples', '')
    points = int(request.form.get('points', 100))
    time_limit = int(request.form.get('time_limit', 1))
    memory_limit = int(request.form.get('memory_limit', 256))
    
    problem = ContestProblem()
    problem.contest_id = contest_id
    problem.title = title
    problem.description = description
    problem.constraints = constraints
    problem.examples = examples
    problem.points = points
    problem.time_limit = time_limit
    problem.memory_limit = memory_limit
    
    db.session.add(problem)
    db.session.commit()
    
    flash('Problem added successfully!', 'success')
    return redirect(url_for('contest_edit', contest_id=contest_id))

@app.route('/contest/<int:contest_id>/problem/<int:problem_id>/add_test_case', methods=['POST'])
@admin_required
def add_test_case(contest_id, problem_id):
    """Admin route to add test cases to a problem"""
    contest = Contest.query.get_or_404(contest_id)
    problem = ContestProblem.query.get_or_404(problem_id)
    
    if contest.created_by != session['user_id']:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    input_data = request.form['input_data']
    expected_output = request.form['expected_output']
    is_sample = 'is_sample' in request.form
    
    test_case = ContestTestCase()
    test_case.problem_id = problem_id
    test_case.input_data = input_data
    test_case.expected_output = expected_output
    test_case.is_sample = is_sample
    
    db.session.add(test_case)
    db.session.commit()
    
    flash('Test case added successfully!', 'success')
    return redirect(url_for('contest_edit', contest_id=contest_id))

@app.route('/contest/<int:contest_id>/participate')
@login_required
def contest_participate(contest_id):
    """Student route to participate in a live contest"""
    contest = Contest.query.get_or_404(contest_id)
    user = User.query.get(session['user_id'])
    
    # Allow participation if contest is live (for all users)
    if not contest.is_live():
        if contest.is_upcoming():
            flash(f'Contest starts at {contest.start_date.strftime("%Y-%m-%d %H:%M:%S")} UTC. Please wait.', 'info')
        else:
            flash('Contest has ended', 'error')
        return redirect(url_for('contests'))
    
    # Get or create participant record
    participant = ContestParticipant.query.filter_by(contest_id=contest_id, user_id=user.id).first()
    if not participant:
        participant = ContestParticipant()
        participant.contest_id = contest_id
        participant.user_id = user.id
        db.session.add(participant)
        db.session.commit()
    
    problems = ContestProblem.query.filter_by(contest_id=contest_id).order_by(ContestProblem.id.asc()).all()
    
    # Get user's submissions for this contest
    submissions = ContestSubmission.query.filter_by(contest_id=contest_id, user_id=user.id).all()
    submission_map = {s.problem_id: s for s in submissions}
    
    # Calculate remaining time
    end_time = contest.get_end_time()
    remaining_seconds = int((end_time - datetime.utcnow()).total_seconds())
    
    return render_template('contest_participate.html', 
                         contest=contest, 
                         problems=problems,
                         submissions=submission_map,
                         remaining_seconds=max(0, remaining_seconds))

@app.route('/contest/debug')
@login_required  
def contest_debug():
    """Debug route to test contest functionality"""
    with open('debug_contest.html', 'r') as f:
        return f.read()

@app.route('/contest/<int:contest_id>/problem/<int:problem_id>')
@login_required
def contest_problem(contest_id, problem_id):
    """Student route to view and solve a contest problem"""
    try:
        contest = Contest.query.get_or_404(contest_id)
        problem = ContestProblem.query.get_or_404(problem_id)
        user = User.query.get(session['user_id'])
        
        # Allow problem access if contest is live
        if not contest.is_live():
            flash('Contest is not currently active', 'error')
            return redirect(url_for('contests'))
        
        # Get sample test cases (visible to students)
        sample_test_cases = ContestTestCase.query.filter_by(problem_id=problem_id, is_sample=True).all()
        
        # Get user's latest submission for this problem
        latest_submission = ContestSubmission.query.filter_by(
            contest_id=contest_id, 
            problem_id=problem_id, 
            user_id=user.id
        ).order_by(ContestSubmission.submitted_at.desc()).first()
        
        # Calculate remaining time
        end_time = contest.get_end_time()
        remaining_seconds = int((end_time - datetime.utcnow()).total_seconds())
        
        app.logger.info(f"Rendering contest problem: {contest.title} - {problem.title}")
        app.logger.info(f"Sample test cases: {len(sample_test_cases)}")
        
        return render_template('contest_problem.html',
                             contest=contest,
                             problem=problem,
                             sample_test_cases=sample_test_cases,
                             latest_submission=latest_submission,
                             remaining_seconds=max(0, remaining_seconds))
                             
    except Exception as e:
        app.logger.error(f"Error in contest_problem route: {str(e)}")
        flash(f'Error loading contest problem: {str(e)}', 'error')
        return redirect(url_for('contests'))

@app.route('/contest/<int:contest_id>/problem/<int:problem_id>/run', methods=['POST'])
@login_required
def run_code(contest_id, problem_id):
    """Run user code with custom input or sample test cases"""
    contest = Contest.query.get_or_404(contest_id)
    problem = ContestProblem.query.get_or_404(problem_id)
    
    if not contest.is_live():
        return jsonify({'success': False, 'error': 'Contest is not currently active'})
    
    code = request.form['code']
    custom_input = request.form.get('custom_input', '').strip()
    language = request.form.get('language', 'python')
    
    if not code.strip():
        return jsonify({'success': False, 'error': 'Code cannot be empty'})
    
    try:
        executor = CodeExecutor()
        
        # If custom input is provided, run with custom input
        if custom_input:
            result = executor.execute_code(code, language, custom_input)
            return jsonify({
                'success': result['success'],
                'output': result.get('output', ''),
                'error': result.get('error', ''),
                'execution_time': result.get('execution_time', 0.0),
                'test_type': 'custom'
            })
        
        # If no custom input, run against sample test cases using function calls
        sample_test_cases = ContestTestCase.query.filter_by(problem_id=problem_id, is_sample=True).all()
        
        if not sample_test_cases:
            return jsonify({'success': False, 'error': 'No sample test cases available'})
        
        test_results = []
        all_passed = True
        
        for i, test_case in enumerate(sample_test_cases):
            # Create test code that calls the user's solution function
            test_code = code + "\n\n"
            
            # Parse input and create function call based on problem
            if problem.title == "Sum of Two Numbers":
                input_parts = test_case.input_data.strip().split()
                test_code += f"result = solution({input_parts[0]}, {input_parts[1]})\nprint(result)"
            elif problem.title == "Reverse a String":
                test_code += f"result = solution('{test_case.input_data.strip()}')\nprint(result)"
            elif problem.title == "Find Maximum":
                lines = test_case.input_data.strip().split('\n')
                n = int(lines[0])
                numbers = lines[1].split()
                test_code += f"result = solution({numbers})\nprint(result)"
            else:
                # Fallback to original input/output method
                result = executor.execute_code(code, language, test_case.input_data)
                if result['success']:
                    actual_output = result['output'].strip()
                    expected_output = test_case.expected_output.strip()
                    passed = actual_output == expected_output
                    test_results.append({
                        'test_number': i + 1,
                        'input': test_case.input_data,
                        'expected': expected_output,
                        'actual': actual_output,
                        'passed': passed,
                        'execution_time': result.get('execution_time', 0.0)
                    })
                    if not passed:
                        all_passed = False
                else:
                    test_results.append({
                        'test_number': i + 1,
                        'input': test_case.input_data,
                        'expected': test_case.expected_output,
                        'actual': '',
                        'passed': False,
                        'error': result.get('error', ''),
                        'execution_time': 0.0
                    })
                    all_passed = False
                continue
            
            # Execute the test code
            result = executor.execute_code(test_code, language, "")
            
            if result['success']:
                actual_output = result['output'].strip()
                expected_output = test_case.expected_output.strip()
                passed = actual_output == expected_output
                
                test_results.append({
                    'test_number': i + 1,
                    'input': test_case.input_data,
                    'expected': expected_output,
                    'actual': actual_output,
                    'passed': passed,
                    'execution_time': result.get('execution_time', 0.0)
                })
                
                if not passed:
                    all_passed = False
            else:
                test_results.append({
                    'test_number': i + 1,
                    'input': test_case.input_data,
                    'expected': test_case.expected_output,
                    'actual': '',
                    'passed': False,
                    'error': result.get('error', ''),
                    'execution_time': 0.0
                })
                all_passed = False
        
        return jsonify({
            'success': True,
            'test_results': test_results,
            'all_passed': all_passed,
            'total_tests': len(test_results),
            'passed_tests': sum(1 for r in test_results if r['passed']),
            'test_type': 'sample'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/contest/<int:contest_id>/submit/<int:problem_id>', methods=['POST'])
@login_required
def submit_solution(contest_id, problem_id):
    """Student route to submit solution"""
    contest = Contest.query.get_or_404(contest_id)
    problem = ContestProblem.query.get_or_404(problem_id)
    user = User.query.get(session['user_id'])
    
    # Allow submissions if contest is live
    if not contest.is_live():
        return jsonify({'success': False, 'error': 'Contest is not currently active'})
    
    code = request.form['code']
    language = request.form.get('language', 'python')
    
    if not code.strip():
        return jsonify({'success': False, 'error': 'Code cannot be empty'})
    
    # Create submission
    submission = ContestSubmission()
    submission.contest_id = contest_id
    submission.problem_id = problem_id
    submission.user_id = user.id
    submission.code = code
    submission.language = language
    
    db.session.add(submission)
    db.session.commit()
    
    # Execute code against test cases
    executor = CodeExecutor()
    test_cases = ContestTestCase.query.filter_by(problem_id=problem_id).all()
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test_case in test_cases:
        try:
            # Create test code that calls the user's solution function
            test_code = code + "\n\n"
            
            # Parse input and create function call based on problem
            if problem.title == "Sum of Two Numbers":
                input_parts = test_case.input_data.strip().split()
                test_code += f"result = solution({input_parts[0]}, {input_parts[1]})\nprint(result)"
            elif problem.title == "Reverse a String":
                test_code += f"result = solution('{test_case.input_data.strip()}')\nprint(result)"
            elif problem.title == "Find Maximum":
                lines = test_case.input_data.strip().split('\n')
                n = int(lines[0])
                numbers = lines[1].split()
                test_code += f"result = solution({numbers})\nprint(result)"
            else:
                # Fallback to original input/output method
                result = executor.execute_code(code, language, test_case.input_data)
                if result['success']:
                    actual_output = result['output'].strip()
                    expected_output = test_case.expected_output.strip()
                    
                    if actual_output == expected_output:
                        passed_tests += 1
                        test_result = ContestTestResult()
                        test_result.submission_id = submission.id
                        test_result.test_case_id = test_case.id
                        test_result.status = 'passed'
                        test_result.actual_output = actual_output
                        test_result.execution_time = result['execution_time']
                        db.session.add(test_result)
                    else:
                        test_result = ContestTestResult()
                        test_result.submission_id = submission.id
                        test_result.test_case_id = test_case.id
                        test_result.status = 'failed'
                        test_result.actual_output = actual_output
                        test_result.execution_time = result['execution_time']
                        db.session.add(test_result)
                else:
                    test_result = ContestTestResult()
                    test_result.submission_id = submission.id
                    test_result.test_case_id = test_case.id
                    test_result.status = 'error'
                    test_result.error_message = result['error']
                    db.session.add(test_result)
                continue
            
            # Execute the test code
            result = executor.execute_code(test_code, language, "")
            
            if result['success']:
                actual_output = result['output'].strip()
                expected_output = test_case.expected_output.strip()
                
                if actual_output == expected_output:
                    passed_tests += 1
                    test_result = ContestTestResult()
                    test_result.submission_id = submission.id
                    test_result.test_case_id = test_case.id
                    test_result.status = 'passed'
                    test_result.actual_output = actual_output
                    test_result.execution_time = result['execution_time']
                    db.session.add(test_result)
                else:
                    test_result = ContestTestResult()
                    test_result.submission_id = submission.id
                    test_result.test_case_id = test_case.id
                    test_result.status = 'failed'
                    test_result.actual_output = actual_output
                    test_result.execution_time = result['execution_time']
                    db.session.add(test_result)
            else:
                test_result = ContestTestResult()
                test_result.submission_id = submission.id
                test_result.test_case_id = test_case.id
                test_result.status = 'error'
                test_result.error_message = result['error']
                db.session.add(test_result)
        except Exception as e:
            test_result = ContestTestResult()
            test_result.submission_id = submission.id
            test_result.test_case_id = test_case.id
            test_result.status = 'error'
            test_result.error_message = str(e)
            db.session.add(test_result)
    
    # Calculate score and status
    if passed_tests == total_tests:
        submission.status = 'accepted'
        submission.score = problem.points
    elif passed_tests > 0:
        submission.status = 'partial'
        submission.score = int((passed_tests / total_tests) * problem.points)
    else:
        submission.status = 'wrong_answer'
        submission.score = 0
    
    # Update participant statistics
    participant = ContestParticipant.query.filter_by(contest_id=contest_id, user_id=user.id).first()
    if participant:
        participant.last_submission = datetime.utcnow()
        # Recalculate total score and problems solved
        user_submissions = ContestSubmission.query.filter_by(contest_id=contest_id, user_id=user.id).all()
        problem_scores = {}
        for sub in user_submissions:
            if sub.problem_id not in problem_scores or sub.score > problem_scores[sub.problem_id]:
                problem_scores[sub.problem_id] = sub.score
        
        participant.total_score = sum(problem_scores.values())
        participant.problems_solved = sum(1 for score in problem_scores.values() if score > 0)
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'status': submission.status,
        'score': submission.score,
        'message': f'{passed_tests}/{total_tests} test cases passed',
        'passed_tests': passed_tests,
        'total_tests': total_tests
    })



@app.route('/contest/<int:contest_id>/results')
@login_required
def contest_results(contest_id):
    """Show contest results and rankings"""
    contest = Contest.query.get_or_404(contest_id)
    
    if contest.is_live():
        flash('Contest is still ongoing', 'info')
        return redirect(url_for('contests'))
    
    # Get all participants with their scores
    participants = db.session.query(ContestParticipant, User).join(
        User, ContestParticipant.user_id == User.id
    ).filter(ContestParticipant.contest_id == contest_id).order_by(
        ContestParticipant.total_score.desc(),
        ContestParticipant.problems_solved.desc(),
        ContestParticipant.last_submission.asc()
    ).all()
    
    # Assign ranks
    for rank, (participant, user) in enumerate(participants, 1):
        participant.rank = rank
    
    db.session.commit()
    
    # Get current user's rank if they participated
    current_user_rank = None
    current_user = User.query.get(session['user_id'])
    if current_user.is_student():
        user_participant = ContestParticipant.query.filter_by(
            contest_id=contest_id, 
            user_id=current_user.id
        ).first()
        current_user_rank = user_participant.rank if user_participant else None
    
    return render_template('contest_results.html',
                         contest=contest,
                         participants=participants,
                         current_user_rank=current_user_rank,
                         user=current_user)

@app.route('/contest/<int:contest_id>/leaderboard')
@login_required
def contest_leaderboard(contest_id):
    """Live leaderboard for ongoing contest"""
    contest = Contest.query.get_or_404(contest_id)
    
    if not contest.is_live():
        return redirect(url_for('contest_results', contest_id=contest_id))
    
    # Get top 10 participants
    top_participants = db.session.query(ContestParticipant, User).join(
        User, ContestParticipant.user_id == User.id
    ).filter(ContestParticipant.contest_id == contest_id).order_by(
        ContestParticipant.total_score.desc(),
        ContestParticipant.problems_solved.desc(),
        ContestParticipant.last_submission.asc()
    ).limit(10).all()
    
    # Calculate remaining time
    end_time = contest.get_end_time()
    remaining_seconds = int((end_time - datetime.utcnow()).total_seconds())
    
    return render_template('contest_leaderboard.html',
                         contest=contest,
                         top_participants=top_participants,
                         remaining_seconds=max(0, remaining_seconds))

@app.route('/api/contest/<int:contest_id>/time_remaining')
@login_required
def contest_time_remaining(contest_id):
    """API endpoint to get remaining time for contest"""
    contest = Contest.query.get_or_404(contest_id)
    
    if not contest.is_live():
        return jsonify({'remaining_seconds': 0, 'status': 'ended'})
    
    end_time = contest.get_end_time()
    remaining_seconds = int((end_time - datetime.utcnow()).total_seconds())
    
    return jsonify({
        'remaining_seconds': max(0, remaining_seconds),
        'status': 'live' if remaining_seconds > 0 else 'ended'
    })

@app.route('/notifications')
@login_required
def notifications():
    """Display notifications for the current user"""
    user = User.query.get(session['user_id'])
    notifications = NotificationService.get_user_notifications(user.id, limit=50)
    unread_count = len([n for n in notifications if not n['is_read']])
    
    return render_template('notifications.html', 
                         notifications=notifications, 
                         unread_count=unread_count,
                         user=user)

@app.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_single_notification_read(notification_id):
    """Mark a specific notification as read"""
    success = NotificationService.mark_notification_read(notification_id, session['user_id'])
    return jsonify({'success': success})

@app.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_user_notifications_read():
    """Mark all notifications as read for current user"""
    success = NotificationService.mark_all_notifications_read(session['user_id'])
    return jsonify({'success': success})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def api_mark_all_notifications_read():
    """API endpoint to mark all notifications as read for current user"""
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['user_id']
        # Update all unread notifications for the user
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error marking all notifications as read: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/unread_count')
@login_required
def get_unread_notifications_count():
    """Get count of unread notifications for current user"""
    notifications = NotificationService.get_user_notifications(session['user_id'], unread_only=True)
    return jsonify({'count': len(notifications)})

@app.route('/check_contest_reminders')
def check_contest_reminders():
    """Background task route to check and send contest reminders"""
    try:
        NotificationService.check_and_send_contest_reminders()
        return jsonify({'success': True, 'message': 'Contest reminders checked'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
