import sys
import os

# Add your project directory to the Python path
mysite_path = '/home/yourusername/mysite'
if mysite_path not in sys.path:
    sys.path.append(mysite_path)

# Import your Flask app from the app package
from app import app as application

if __name__ == "__main__":
    application.run()
