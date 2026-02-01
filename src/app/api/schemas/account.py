from pydantic import BaseModel


class AccountCreate(BaseModel):
    name: str


class AccountOut(BaseModel):
    name: str
    transaction_count: int = 0
