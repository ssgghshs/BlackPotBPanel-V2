from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from app.user import schemas, service
from middleware.auth import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/create", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    try:
        return await service.create_user(db, user, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")


@router.get("/captcha", response_model=schemas.CaptchaResponse)
async def get_captcha():
    return await service.get_captcha()


@router.post("/login", response_model=schemas.TokenWithDefaultPasswordCheck)
async def login(request: Request, form_data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    return await service.login(request, form_data, db)


@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user=Depends(get_current_active_user)):
    return current_user


@router.post("/me/update", response_model=schemas.UserResponse)
async def update_current_user(
    user_update: schemas.UserUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await service.update_current_user(db, user_update, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user information")


@router.get("/{user_id}/detail", response_model=schemas.UserResponse)
async def get_user(
    user_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.get_user(db, user_id, current_user)


@router.get("/list", response_model=list[schemas.UserResponse])
async def get_users(
    skip: int = 0, limit: int = 100,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.get_users(db, skip, limit, current_user)


@router.post("/{user_id}/update", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.update_user(db, user_id, user_update, current_user)


@router.post("/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        await service.delete_user(db, user_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete user")


@router.post("/me/password", response_model=schemas.UserResponse)
async def change_password(
    password_change: schemas.PasswordChange,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.change_password(db, password_change, current_user)


@router.post("/logout")
async def logout(
    request: Request,
    current_user=Depends(get_current_active_user)
):
    return await service.logout(request, current_user)
