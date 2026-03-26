"""
Authentication service for user login and session management.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserSession:
    """Current user session information."""

    user_id: int
    username: str
    role: str
    full_name: Optional[str] = None
    login_time: Optional[datetime] = None


class AuthService:
    """
    Authentication service for user management.

    Provides password hashing, verification, and session management.
    """

    def __init__(self, db_manager):
        """
        Initialize authentication service.

        Args:
            db_manager: DatabaseManager instance for user operations.
        """
        self._db = db_manager
        self._current_session: Optional[UserSession] = None

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash a password with salt.

        Args:
            password: Plain text password.
            salt: Optional salt (generated if not provided).

        Returns:
            Tuple of (hashed_password, salt).
        """
        if salt is None:
            salt = secrets.token_hex(16)

        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against stored hash.

        Args:
            password: Plain text password to verify.
            hashed_password: Stored password hash.
            salt: Salt used for hashing.

        Returns:
            True if password matches.
        """
        new_hash, _ = AuthService.hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed_password)

    def login(self, username: str, password: str) -> Optional[UserSession]:
        """
        Authenticate user and create session.

        Args:
            username: Username.
            password: Plain text password.

        Returns:
            UserSession if authentication successful, None otherwise.
        """
        user = self._db.get_user_by_username(username)
        if user is None:
            return None

        if not user.is_active:
            return None

        stored_hash = user.password_hash
        if ":" in stored_hash:
            salt, hashed = stored_hash.split(":", 1)
        else:
            salt = ""
            hashed = stored_hash

        if not self.verify_password(password, hashed, salt):
            return None

        self._current_session = UserSession(
            user_id=user.id,
            username=user.username,
            role=user.role,
            full_name=user.full_name,
            login_time=datetime.now(),
        )

        self._db.log_operation(
            user_id=user.id,
            operation="login",
            target_type="session",
        )

        return self._current_session

    def logout(self) -> None:
        """End current session."""
        if self._current_session:
            self._db.log_operation(
                user_id=self._current_session.user_id,
                operation="logout",
                target_type="session",
            )
        self._current_session = None

    def get_current_session(self) -> Optional[UserSession]:
        """Get current user session."""
        return self._current_session

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._current_session is not None

    def is_admin(self) -> bool:
        """Check if current user is admin."""
        if self._current_session is None:
            return False
        return self._current_session.role == "admin"

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "engineer",
    ) -> Optional[int]:
        """
        Create a new user with hashed password.

        Args:
            username: Username.
            password: Plain text password.
            email: Email address.
            full_name: Full name.
            role: User role.

        Returns:
            User ID if created, None if failed.
        """
        hashed, salt = self.hash_password(password)
        stored_hash = f"{salt}:{hashed}"

        try:
            user = self._db.create_user(
                username=username,
                password_hash=stored_hash,
                email=email,
                full_name=full_name,
                role=role,
            )
            return user.id
        except Exception:
            return None

    def change_password(self, user_id: int, new_password: str) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID.
            new_password: New plain text password.

        Returns:
            True if successful.
        """
        hashed, salt = self.hash_password(new_password)
        stored_hash = f"{salt}:{hashed}"

        with self._db.session() as session:
            from src.database.models import User

            user = session.get(User, user_id)
            if user:
                user.password_hash = stored_hash
                return True
        return False
