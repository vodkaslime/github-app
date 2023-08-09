import os
import hmac
import hashlib
import subprocess
import re
from typing import Annotated

from github import Github, GithubIntegration
import toml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header

from .model import WebhookRequest

# Load environment variables in .env
load_dotenv()

app = FastAPI()
app_id = os.getenv("APP_ID")
webhook_secret = os.getenv("WEBHOOK_SECRET")
private_key_path = os.getenv("PRIVATE_KEY_PATH")

pull_request_actions = ["opened", "closed", "reopened"]

# Read the bot certificate
with open(
    os.path.normpath(os.path.expanduser(private_key_path)),
    'r'
) as cert_file:
    app_key = cert_file.read()

# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def make_structure(dir: str):
    stack = [(dir, "root", 0)]
    res = ""
    while stack:
        curr, print_name, ind = stack.pop()
        res += ' ' * ind + f"- {print_name}\n"
        new_ind = ind + 2
        if os.path.isdir(curr):
            for item in os.listdir(curr)[::-1]:
                item_path = os.path.join(curr, item)
                stack.append((item_path, item, new_ind))
    return res

def index(url: str):

    # make config.toml file
    toml_config = {
        "repositories":[
            {
                "git_url": url,
            }
        ],
        "experimental": {
            "enable_prompt_rewrite": False,
        }
    }

    toml_config_str = toml.dumps(toml_config)

    root_path = os.path.expanduser("~/.tabby")
    file_path = os.path.join(root_path, "config.toml")
    with open(file_path, 'w') as file:
        file.write(toml_config_str)

    # start indexing
    cmd = "docker run -it -v $HOME/.tabby:/data tabbyml/tabby scheduler --now"
    dev = True
    if dev:
        cmd = "docker run -it -e HTTP_PROXY=http://localhost:7890 -e HTTPS_PROXY=http://localhost:7890 --network host -v $HOME/.tabby:/data tabbyml/tabby scheduler --now"
    
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.stderr:
        print(p.stderr)
        raise Exception("error indexing")
    
    # print file structure
    arr = re.split(r'[:/]', url)
    dir = "_".join([s for s in arr if s])
    dir_path = os.path.join(root_path, "repositories", dir)

    file_structure = make_structure(dir_path)

    return file_structure

def validate_signature(signature_header: str, data: bytes):
    sha_name, github_signature = signature_header.split('=')
    if sha_name != 'sha1':
        raise Exception("invalid signature header")

    local_signature = hmac.new(webhook_secret.encode('utf-8'), msg=data, digestmod=hashlib.sha1)

    if not hmac.compare_digest(local_signature.hexdigest(), github_signature):
        raise Exception("invalid signature")

@app.post("/")
async def bot(
    request: WebhookRequest,
    x_hub_signature: Annotated[str | None, Header()],
    request_raw_data: Request
):
    # Get the event payload
    data = await request_raw_data.body()

    try:
        validate_signature(x_hub_signature, data)
    except Exception as error:
        print(error)
        raise HTTPException(status_code=403, detail="invalid signature")

    # Check if the event is a GitHub PR creation event
    if not request.action or request.action not in pull_request_actions or not request.pull_request:
        raise HTTPException(status_code=403, detail="request not supported")

    if not request.repository:
        raise HTTPException(status_code=403, detail="invalid request: repository needed")
    
    owner = request.repository.owner.login
    repo_name = request.repository.name

    token = git_integration.get_access_token(git_integration.get_repo_installation(owner, repo_name).id).token
    url = f"https://oauth2:{token}@github.com/{owner}/{repo_name}"

    # Run the actual indexing job
    comment_msg = index(url)

    git_connection = Github(login_or_token=token)
    repo = git_connection.get_repo(f"{owner}/{repo_name}")
    issue = repo.get_issue(number=request.pull_request.number)

    # Create a comment with the random meme
    issue.create_comment(comment_msg)
    return "ok"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)