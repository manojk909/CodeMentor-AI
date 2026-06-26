from app import app
from app.services.notification_scheduler import start_notification_scheduler

# Start background notification scheduler
start_notification_scheduler(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
