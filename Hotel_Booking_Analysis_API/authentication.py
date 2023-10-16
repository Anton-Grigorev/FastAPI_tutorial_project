from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status

# ! LOGIN and PASSWORD to receive data
security = HTTPBasic()
user_db = {"Anton": "pass123456"}


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    user = user_db.get(credentials.username)
    if user is None or user != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user
