from pydantic import BaseModel

class Owner(BaseModel):
    login: str

class Repository(BaseModel):
    owner: Owner
    name: str

class PullRequest(BaseModel):
    number: int

class WebhookRequest(BaseModel):
    repository: Repository | None
    action: str | None
    pull_request: PullRequest | None