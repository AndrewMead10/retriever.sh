from fastapi import APIRouter, Response
from ...middleware.auth import clear_auth_cookies

router = APIRouter()


@router.post("/auth/logout/onsubmit")
async def logout(response: Response):
    """Logout user by clearing cookies"""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
