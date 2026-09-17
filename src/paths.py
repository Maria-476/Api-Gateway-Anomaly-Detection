import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_path(*parts):
    return os.path.join(PROJECT_ROOT, *parts)