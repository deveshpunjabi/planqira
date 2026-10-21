import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Expose both app and handler for universal Vercel ASGI serverless discovery
handler = app
