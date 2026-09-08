from sqlalchemy.orm import Session

from . import models, security


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, password: str):
    user = models.User(email=email, hashed_password=security.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def store_refresh_token(db: Session, user_id: int, token: str, expires_at):
    record = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_refresh_token(db: Session, token: str):
    return db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()


def revoke_refresh_token(db: Session, token_record: models.RefreshToken):
    token_record.revoked = True
    db.commit()
