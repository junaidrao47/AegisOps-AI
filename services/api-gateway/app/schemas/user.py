from pydantic import BaseModel


class UserBase(BaseModel):
    email: str
    role: str = "engineer"


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}
