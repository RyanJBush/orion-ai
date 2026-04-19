from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    role: str = "worker"


class Agent(BaseModel):
    id: int
    name: str
    role: str
    model: str

    class Config:
        from_attributes = True
