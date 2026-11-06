"""
Data package containing authentic exam seed scripts and vocabulary assets.
"""
try:
    from app.data.seed_genuine_exams import seed_database
except ImportError:
    from backend.app.data.seed_genuine_exams import seed_database

__all__ = ["seed_database"]
