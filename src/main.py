'''
This module is the FastAPI main app as backend of Github App,
which handles indexing jobs per repository pull requests.
'''

import os
from typing import Annotated

from github import Github, GithubIntegration
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header

from src.model import WebhookRequest
from src.indexing import index
from src.validation import validate_signature

# Load environment variables in .env
load_dotenv()

app = FastAPI()
app_id = os.getenv("APP_ID")
private_key_path = os.getenv("PRIVATE_KEY_PATH")

pull_request_actions = ["opened", "closed", "reopened"]

# Read the bot certificate
with open(
    os.path.normpath(os.path.expanduser(private_key_path)),
    'r', encoding='utf-8'
) as cert_file:
    app_key = cert_file.read()

# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

@app.post("/")
async def bot(
    request: WebhookRequest,
    x_hub_signature: Annotated[str | None, Header()],
    request_raw_data: Request
):
    '''
    This is the entry function for handling Github Webhooks.
    '''
    # Get the event payload
    data = await request_raw_data.body()

    try:
        validate_signature(x_hub_signature, data)
    except Exception as error:
        print(error)
        raise HTTPException(status_code=403, detail="invalid signature") from error

    # Check if the event is a GitHub PR creation event
    if not request.action or request.action not in pull_request_actions or not request.pull_request:
        raise HTTPException(status_code=403, detail="request not supported")

    if not request.repository:
        raise HTTPException(status_code=403, detail="invalid request: repository needed")

    owner = request.repository.owner.login
    repo_name = request.repository.name

    token = git_integration.get_access_token(
        git_integration.get_repo_installation(owner, repo_name).id
    ).token
    url = f"https://oauth2:{token}@github.com/{owner}/{repo_name}"

    # Run the actual indexing job
    comment_msg = index(url)

    git_connection = Github(login_or_token=token)
    repo = git_connection.get_repo(f"{owner}/{repo_name}")
    issue = repo.get_issue(number=request.pull_request.number)

    # Create a comment with the random meme
    issue.create_comment(comment_msg)
    return "ok"
