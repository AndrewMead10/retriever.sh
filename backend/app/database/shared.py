from .models import UserUsage, User
from . import get_db_session




def get_user_by_id(user_id: int) -> User | None:
    """Get user by ID"""
    with get_db_session() as db:
        return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(email: str) -> User | None:
    """Get user by email"""
    with get_db_session() as db:
        return db.query(User).filter(User.email == email).first()


def create_user(email: str, hashed_password: str) -> User:
    """Create a new user without a plan (plans require payment)"""
    with get_db_session() as db:
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.flush()

        usage = UserUsage(user_id=user.id)
        db.add(usage)

        db.commit()
        db.refresh(user)
        return user
