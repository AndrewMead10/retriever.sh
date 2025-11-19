from fastapi import APIRouter, Request, Response, HTTPException
from jose import jwt, JWTError
from ...config import settings
from ...middleware.auth import create_access_token, set_access_token_cookie, set_session_indicator_cookie, verify_token

router = APIRouter()


@router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token from cookie"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token or not verify_token(refresh_token):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
        token_type = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    new_access_token = create_access_token(user_id)
    set_access_token_cookie(response, new_access_token)
    set_session_indicator_cookie(response)
    
    return {"success": True}
