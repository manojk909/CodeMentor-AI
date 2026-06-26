import threading
import time
import logging
from datetime import datetime, timedelta
from app.services.notification_service import NotificationService

class NotificationScheduler:
    """Background scheduler for sending periodic notifications"""
    
    def __init__(self, app=None):
        self.running = False
        self.thread = None
        self.app = app
        logging.basicConfig(level=logging.INFO)
    
    def start(self):
        """Start the background scheduler"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logging.info("Notification scheduler started")
    
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logging.info("Notification scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                if self.app:
                    with self.app.app_context():
                        # Check for contest reminders every 5 minutes
                        NotificationService.check_and_send_contest_reminders()
                        logging.info("Contest reminder check completed")
                else:
                    logging.warning("No Flask app context available for scheduler")
            except Exception as e:
                logging.error(f"Error in notification scheduler: {e}")
            finally:
                try:
                    from app import db
                    db.session.remove()
                except Exception as ex:
                    logging.error(f"Error removing db session in scheduler: {ex}")
            
            # Sleep for 5 minutes before next check
            for _ in range(300):  # 5 minutes = 300 seconds
                if not self.running:
                    break
                time.sleep(1)

# Global scheduler instance
scheduler = None

def start_notification_scheduler(app=None):
    """Start the global notification scheduler"""
    global scheduler
    if scheduler is None:
        scheduler = NotificationScheduler(app)
    scheduler.start()

def stop_notification_scheduler():
    """Stop the global notification scheduler"""
    global scheduler
    if scheduler:
        scheduler.stop()