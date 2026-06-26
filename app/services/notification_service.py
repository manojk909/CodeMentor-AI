from datetime import datetime, timedelta
from app import db
from app.models import Notification, Contest, User, ForumPost, StudyGroup, StudyGroupMember
import logging

class NotificationService:
    """Service for managing notifications across the platform"""
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type='info', 
                          category='general', contest_id=None, forum_post_id=None, 
                          study_group_id=None):
        """Create a new notification for a user"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                category=category,
                contest_id=contest_id,
                forum_post_id=forum_post_id,
                study_group_id=study_group_id
            )
            db.session.add(notification)
            db.session.commit()
            logging.info(f"Notification created for user {user_id}: {title}")
            return notification
        except Exception as e:
            logging.error(f"Error creating notification: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def notify_contest_created(contest):
        """Send notifications when a new contest is created"""
        try:
            # Notify all students about the new contest
            students = User.query.filter_by(role='student').all()
            
            title = f"🏆 New Contest: {contest.title}"
            message = (f"A new coding contest '{contest.title}' has been scheduled!\n"
                      f"📅 Start Date: {contest.start_date.strftime('%Y-%m-%d %H:%M UTC')}\n"
                      f"⏰ Duration: {contest.duration_minutes} minutes\n"
                      f"📝 Description: {contest.description[:100]}...")
            
            for student in students:
                NotificationService.create_notification(
                    user_id=student.id,
                    title=title,
                    message=message,
                    notification_type='info',
                    category='contest',
                    contest_id=contest.id
                )
            
            logging.info(f"Contest creation notifications sent for contest {contest.id}")
            
        except Exception as e:
            logging.error(f"Error sending contest creation notifications: {e}")
    
    @staticmethod
    def notify_contest_reminder(contest):
        """Send 24-hour reminder notifications for upcoming contests"""
        try:
            # Check if contest starts in approximately 24 hours (23-25 hours to handle timing issues)
            time_until_start = contest.start_date - datetime.utcnow()
            hours_until_start = time_until_start.total_seconds() / 3600
            
            if 23 <= hours_until_start <= 25:
                students = User.query.filter_by(role='student').all()
                
                title = f"⏰ Contest Reminder: {contest.title}"
                message = (f"Don't forget! The contest '{contest.title}' starts in 24 hours.\n"
                          f"📅 Start Time: {contest.start_date.strftime('%Y-%m-%d %H:%M UTC')}\n"
                          f"⏰ Duration: {contest.duration_minutes} minutes\n"
                          f"🎯 Be prepared and ready to compete!")
                
                for student in students:
                    # Check if reminder already sent to avoid duplicates
                    existing_reminder = Notification.query.filter_by(
                        user_id=student.id,
                        contest_id=contest.id,
                        category='contest',
                        title=title
                    ).first()
                    
                    if not existing_reminder:
                        NotificationService.create_notification(
                            user_id=student.id,
                            title=title,
                            message=message,
                            notification_type='warning',
                            category='contest',
                            contest_id=contest.id
                        )
                
                logging.info(f"24-hour reminder notifications sent for contest {contest.id}")
                
        except Exception as e:
            logging.error(f"Error sending contest reminder notifications: {e}")
    
    @staticmethod
    def notify_contest_starting(contest):
        """Send notifications when contest is about to start (5 minutes before)"""
        try:
            time_until_start = contest.start_date - datetime.utcnow()
            minutes_until_start = time_until_start.total_seconds() / 60
            
            if 4 <= minutes_until_start <= 6:  # 4-6 minutes before start
                students = User.query.filter_by(role='student').all()
                
                title = f"🚨 Contest Starting Soon: {contest.title}"
                message = (f"The contest '{contest.title}' is starting in 5 minutes!\n"
                          f"⏰ Start Time: {contest.start_date.strftime('%H:%M UTC')}\n"
                          f"🏃‍♂️ Get ready to join the competition!")
                
                for student in students:
                    NotificationService.create_notification(
                        user_id=student.id,
                        title=title,
                        message=message,
                        notification_type='success',
                        category='contest',
                        contest_id=contest.id
                    )
                
                logging.info(f"Starting soon notifications sent for contest {contest.id}")
                
        except Exception as e:
            logging.error(f"Error sending contest starting notifications: {e}")
    
    @staticmethod
    def notify_forum_question_posted(forum_post):
        """Send notifications when a new question is posted in the doubt forum"""
        try:
            # Notify all users except the author about new forum questions
            users = User.query.filter(User.id != forum_post.author_id).all()
            
            title = f"❓ New Question in Doubt Forum"
            message = (f"A new question has been posted in the doubt forum:\n"
                      f"📝 Title: {forum_post.title}\n"
                      f"👤 Asked by: {forum_post.author.username}\n"
                      f"🏷️ Tags: {forum_post.tags or 'General'}\n"
                      f"💭 Help solve this doubt by providing your answer!")
            
            for user in users:
                NotificationService.create_notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type='info',
                    category='forum',
                    forum_post_id=forum_post.id
                )
            
            logging.info(f"Forum question notifications sent for post {forum_post.id}")
            
        except Exception as e:
            logging.error(f"Error sending forum question notifications: {e}")
    
    @staticmethod
    def notify_study_group_question(forum_post, study_group):
        """Send notifications when a new question is posted in a study group"""
        try:
            # Get all study group members except the author
            group_members = StudyGroupMember.query.filter(
                StudyGroupMember.group_id == study_group.id,
                StudyGroupMember.user_id != forum_post.author_id
            ).all()
            
            title = f"💬 New Question in Study Group: {study_group.name}"
            message = (f"A new question has been posted in your study group:\n"
                      f"📝 Title: {forum_post.title}\n"
                      f"👤 Asked by: {forum_post.author.username}\n"
                      f"🏷️ Tags: {forum_post.tags or 'General'}\n"
                      f"💭 Help your group member by providing an answer!")
            
            for member in group_members:
                NotificationService.create_notification(
                    user_id=member.user_id,
                    title=title,
                    message=message,
                    notification_type='info',
                    category='study_group',
                    forum_post_id=forum_post.id,
                    study_group_id=study_group.id
                )
            
            logging.info(f"Study group question notifications sent for post {forum_post.id} in group {study_group.id}")
            
        except Exception as e:
            logging.error(f"Error sending study group question notifications: {e}")
    
    @staticmethod
    def notify_study_group_message(message_content, study_group, sender):
        """Send notifications when a new message is posted in study group chat"""
        try:
            # Get all study group members except the sender
            group_members = StudyGroupMember.query.filter(
                StudyGroupMember.group_id == study_group.id,
                StudyGroupMember.user_id != sender.id
            ).all()
            
            title = f"💬 New Message in Study Group: {study_group.name}"
            message = (f"New message from {sender.username}:\n"
                      f"📝 {message_content[:100]}{'...' if len(message_content) > 100 else ''}\n"
                      f"💬 Join the conversation in your study group!")
            
            for member in group_members:
                NotificationService.create_notification(
                    user_id=member.user_id,
                    title=title,
                    message=message,
                    notification_type='info',
                    category='study_group',
                    study_group_id=study_group.id
                )
            
            logging.info(f"Study group message notifications sent for group {study_group.id}")
            
        except Exception as e:
            logging.error(f"Error sending study group message notifications: {e}")
    
    @staticmethod
    def notify_forum_answer_posted(forum_post, answer_author):
        """Send notification to question author when someone answers their question"""
        try:
            if forum_post.author_id != answer_author.id:  # Don't notify if author answers their own question
                title = f"✅ Your Question Got an Answer!"
                message = (f"Someone answered your question in the doubt forum:\n"
                          f"📝 Question: {forum_post.title}\n"
                          f"👤 Answered by: {answer_author.username}\n"
                          f"🎉 Check out the answer and mark it as helpful if it solved your doubt!")
                
                NotificationService.create_notification(
                    user_id=forum_post.author_id,
                    title=title,
                    message=message,
                    notification_type='success',
                    category='forum',
                    forum_post_id=forum_post.id
                )
                
                logging.info(f"Forum answer notification sent for post {forum_post.id}")
                
        except Exception as e:
            logging.error(f"Error sending forum answer notification: {e}")
    

    @staticmethod
    def check_and_send_contest_reminders():
        """Check for upcoming contests and send appropriate notifications"""
        try:
            upcoming_contests = Contest.query.filter(
                Contest.start_date > datetime.utcnow(),
                Contest.is_active == True
            ).all()
            
            for contest in upcoming_contests:
                # Send 24-hour reminders
                NotificationService.notify_contest_reminder(contest)
                # Send 5-minute warnings
                NotificationService.notify_contest_starting(contest)
                
        except Exception as e:
            logging.error(f"Error checking contest reminders: {e}")
    
    @staticmethod
    def get_user_notifications(user_id, limit=20, unread_only=False):
        """Get notifications for a user with proper formatting"""
        try:
            query = Notification.query.filter_by(user_id=user_id)
            
            if unread_only:
                query = query.filter_by(is_read=False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            
            # Format notifications with proper icons and categories
            formatted_notifications = []
            for notification in notifications:
                icon = NotificationService._get_notification_icon(notification.category, notification.type)
                formatted_notifications.append({
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.type,
                    'category': notification.category,
                    'icon': icon,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at,
                    'time_ago': NotificationService._time_ago(notification.created_at)
                })
            
            return formatted_notifications
            
        except Exception as e:
            logging.error(f"Error getting user notifications: {e}")
            return []
    
    @staticmethod
    def mark_notification_read(notification_id, user_id):
        """Mark a notification as read"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id, 
                user_id=user_id
            ).first()
            
            if notification:
                notification.is_read = True
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error marking notification as read: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def mark_all_notifications_read(user_id):
        """Mark all notifications as read for a user"""
        try:
            Notification.query.filter_by(user_id=user_id, is_read=False).update({
                'is_read': True
            })
            db.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error marking all notifications as read: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _get_notification_icon(category, notification_type):
        """Get appropriate icon for notification based on category and type"""
        icons = {
            'contest': {
                'info': '🏆',
                'warning': '⏰',
                'success': '🚀',
                'error': '❌'
            },
            'forum': {
                'info': '❓',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            },
            'study_group': {
                'info': '👥',
                'success': '💡',
                'warning': '⚠️',
                'error': '❌'
            },
            'general': {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            }
        }
        
        return icons.get(category, icons['general']).get(notification_type, 'ℹ️')
    
    @staticmethod
    def _time_ago(date_time):
        """Calculate human-readable time difference"""
        now = datetime.utcnow()
        diff = now - date_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"