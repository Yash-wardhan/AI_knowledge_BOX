import sys
import os

# Make `src` importable so `from src.services.xxx import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
