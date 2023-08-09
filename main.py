import os
import hmac
import hashlib
import subprocess
import re

from flask import Flask, request
from github import Github, GithubIntegration
import toml
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app_id = os.getenv("APP_ID")
webhook_secret = os.getenv("WEBHOOK_SECRET")
private_key_path = os.getenv("PRIVATE_KEY_PATH")


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

def make_structure(dir):
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

def index(url):

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

def validate_signature(signature_header, data):
    sha_name, github_signature = signature_header.split('=')
    if sha_name != 'sha1':
        raise Exception("invalid signature header")
    local_signature = hmac.new(webhook_secret.encode('utf-8'), msg=data, digestmod=hashlib.sha1)

    if not hmac.compare_digest(local_signature.hexdigest(), github_signature):
        raise Exception("invalid signature")

@app.route("/", methods=['POST'])
def bot():
    # Get the event payload
    payload = request.json

    headers = request.headers
    signature_header = headers.get('X-Hub-Signature')
    data = request.get_data()

    try:
        validate_signature(signature_header, data)
    except Exception as error:
        print(error)
        return "invalid signature"

    # Check if the event is a GitHub PR creation event
    if (not all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened'):
        return "ok"

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    token = git_integration.get_access_token(git_integration.get_repo_installation(owner, repo_name).id).token

    print(token)
    url = f"https://oauth2:{token}@github.com/{owner}/{repo_name}"

    comment_msg = index(url)

    git_connection = Github(
        login_or_token=token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    issue = repo.get_issue(number=payload['pull_request']['number'])

    # Create a comment with the random meme
    issue.create_comment(comment_msg)
    return "ok"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000)