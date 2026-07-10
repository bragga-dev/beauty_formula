"""
User Repository — persistência de User.
"""
from typing import Optional
from beauty_formula.apps.accounts.models.user import User


def create_user(*, email: str, password: str, role: str,    
) -> User:
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
    )
    return user

def activate_user(user: User) -> User:
    if not user.is_active or user.is_trusty:
        user.is_active = True
        user.is_trusty = True
        user.save(update_fields=["is_active", "is_trusty"])
    return user

def deactivate_user(user: User) -> User:
    if user.is_active or user.is_trusty:
        user.is_active = False
        user.is_trusty = False
        user.save(update_fields=["is_active", "is_trusty"])
    return user