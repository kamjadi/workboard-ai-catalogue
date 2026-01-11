from fastapi import APIRouter, HTTPException, Response, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import bcrypt
import re

from .. import crud

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE_NAME = "session_token"
SESSION_HOURS = 24


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password meets requirements: 8+ chars, 1 number, 1 special char."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'\d', password):
        return False, "Password must contain at least 1 number"
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        return False, "Password must contain at least 1 special character"
    return True, ""


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class BulkUserRequest(BaseModel):
    users: list[dict]  # List of {username, password, role}


# Helper to get current session from cookie
def get_current_session(request: Request) -> Optional[dict]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return crud.get_session(token)


def require_auth(request: Request) -> dict:
    """Dependency that requires authentication."""
    session = get_current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return session


def require_admin(request: Request) -> dict:
    """Dependency that requires admin role."""
    session = require_auth(request)
    if session.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return session


# Auth endpoints
@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """Authenticate user and create session."""
    user = crud.get_user_by_username(request.username)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Check if locked
    if crud.is_user_locked(user):
        raise HTTPException(status_code=423, detail="Account locked. Try again later.")

    # Check if active
    if not user.get('active'):
        raise HTTPException(status_code=401, detail="Account is disabled")

    # Verify password
    if not bcrypt.checkpw(request.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        crud.record_login_attempt(user['id'], success=False)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Success
    crud.record_login_attempt(user['id'], success=True)
    token = crud.create_session(user['id'], hours=SESSION_HOURS)

    response = JSONResponse(content={
        "success": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "must_change_password": bool(user.get('must_change_password'))
        }
    })

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,  # Only send over HTTPS
        samesite="strict",
        max_age=SESSION_HOURS * 3600
    )

    return response


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Log out and delete session."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        crud.delete_session(token)

    response = JSONResponse(content={"success": True})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/me")
async def get_current_user(session: dict = Depends(require_auth)):
    """Get current authenticated user info."""
    return {
        "id": session['user_id'],
        "username": session['username'],
        "role": session['role'],
        "must_change_password": bool(session.get('must_change_password'))
    }


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, session: dict = Depends(require_auth)):
    """Change current user's password."""
    user = crud.get_user_by_username(session['username'])

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not bcrypt.checkpw(request.current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Validate new password
    is_valid, error_msg = validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Hash new password
    new_hash = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Update password
    crud.update_user_password(user['id'], new_hash, must_change=False)

    return {"success": True, "message": "Password changed successfully"}


# User management endpoints (admin only)
@router.get("/users")
async def list_users(session: dict = Depends(require_admin)):
    """List all users (admin only)."""
    return crud.get_users()


@router.post("/users")
async def create_user(request: CreateUserRequest, session: dict = Depends(require_admin)):
    """Create a new user (admin only)."""
    # Check if username exists
    existing = crud.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Validate role
    if request.role not in ['admin', 'user']:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    # Note: No password validation for admin-created users (allows 'changeme' etc.)
    # Hash password
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create user (they must change password on first login)
    user = crud.create_user(request.username, password_hash, request.role, must_change_password=True)
    return user


@router.get("/users/{user_id}")
async def get_user(user_id: int, session: dict = Depends(require_admin)):
    """Get a user by ID (admin only)."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
async def update_user(user_id: int, request: UpdateUserRequest, session: dict = Depends(require_admin)):
    """Update a user (admin only)."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if updating username to one that exists
    if request.username:
        existing = crud.get_user_by_username(request.username)
        if existing and existing['id'] != user_id:
            raise HTTPException(status_code=400, detail="Username already exists")

    # Validate role
    if request.role and request.role not in ['admin', 'user']:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    # Don't allow demoting self from admin
    if session['user_id'] == user_id and request.role == 'user' and user['role'] == 'admin':
        raise HTTPException(status_code=400, detail="Cannot demote yourself from admin")

    # Don't allow deactivating self
    if session['user_id'] == user_id and request.active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    updated = crud.update_user(user_id, request.username, request.role, request.active)
    return updated


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, session: dict = Depends(require_admin)):
    """Delete a user (admin only)."""
    if session['user_id'] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    deleted = crud.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin user")

    # Also delete their sessions
    crud.delete_user_sessions(user_id)

    return {"success": True}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, request: ResetPasswordRequest, session: dict = Depends(require_admin)):
    """Reset a user's password (admin only)."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Note: No password validation for admin reset (allows 'changeme' etc.)
    # Hash new password
    password_hash = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Update password with must_change flag
    crud.update_user_password(user_id, password_hash, must_change=True)

    # Invalidate their sessions
    crud.delete_user_sessions(user_id)

    return {"success": True, "message": "Password reset successfully"}


@router.post("/users/{user_id}/unlock")
async def unlock_user_account(user_id: int, session: dict = Depends(require_admin)):
    """Unlock a user's account (admin only)."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    crud.unlock_user(user_id)
    return {"success": True, "message": "Account unlocked successfully"}


@router.post("/users/bulk")
async def create_users_bulk(request: BulkUserRequest, session: dict = Depends(require_admin)):
    """Create multiple users at once (admin only)."""
    results = []

    for user_data in request.users:
        username = user_data.get('username', '').strip()
        password = user_data.get('password', '').strip()
        role = user_data.get('role', 'user').strip()

        # Skip empty rows
        if not username:
            continue

        # Default password if not provided
        if not password:
            password = 'changeme'

        # Default role
        if role not in ['admin', 'user']:
            role = 'user'

        # Check if username exists
        existing = crud.get_user_by_username(username)
        if existing:
            results.append({
                'username': username,
                'success': False,
                'error': 'Username already exists'
            })
            continue

        try:
            # Hash password (no validation for admin bulk import)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Create user with must_change_password=True
            user = crud.create_user(username, password_hash, role, must_change_password=True)
            results.append({
                'username': username,
                'success': True,
                'id': user['id']
            })
        except Exception as e:
            results.append({
                'username': username,
                'success': False,
                'error': str(e)
            })

    success_count = sum(1 for r in results if r['success'])
    return {
        'success': True,
        'created': success_count,
        'total': len(results),
        'results': results
    }
