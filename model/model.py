from datetime import datetime
from pydantic import BaseModel, Field
from typing import List
from typing_extensions import Annotated


class LoginUser(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    name: Annotated[str, Field(min_length=3, max_length=50)]
    email: Annotated[str, Field(pattern=r'^\S+@\S+$')]
    password: Annotated[str, Field(min_length=6)]


# Agent Chat Request Model
class ChatRequest(BaseModel):
    # Accept either `user_input` (existing) or `message` (frontend) for flexibility.
    user_input: str


# Password Reset Request Model
class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str
