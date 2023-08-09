'''
This module is the data model for FastAPI
to parse the Github Webhook payloads.
'''

from pydantic import BaseModel

class Owner(BaseModel):
    '''
    Owner sub class of Repository.
    We are only interested in the login field of owner.
    '''
    login: str

class Repository(BaseModel):
    '''
    Repository sub class of WebhookRequest.
    We are interested in the owner of the repository
    and the name of the repository.
    '''
    owner: Owner
    name: str

class PullRequest(BaseModel):
    '''
    PullRequest sub class of WebhookRequest.
    We are only interested in the PR number.
    '''
    number: int

class WebhookRequest(BaseModel):
    '''
    WebhookRequest is the model representing webhook
    payload data from Github Webhook.
    '''
    repository: Repository | None
    action: str | None
    pull_request: PullRequest | None
