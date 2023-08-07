import os
import hmac
import hashlib

from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)
app_id = '371364'
# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('private-key.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()

# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def count_files(dir):
    files = lines = 0

    # dfs
    stack = [dir]
    while stack:
        path = stack.pop()
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if file_path == os.path.join(dir, ".git"):
                continue
            if os.path.isfile(file_path):
                files += 1
                print(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines += len(f.readlines())
            elif os.path.isdir(file_path):
                stack.append(file_path)
    return files, lines

def validate_signature(signature_header, data):
    sha_name, github_signature = signature_header.split('=')
    if sha_name != 'sha1':
        raise Exception("invalid signature header")
    local_signature = hmac.new("somekey2".encode('utf-8'), msg=data, digestmod=hashlib.sha1)

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
    dir = f"/tmp/{owner}/{repo_name}"

    if not os.path.exists(dir):
        os.system(f"git clone {url} {dir}")

    files, lines = count_files(dir)
    comment_msg = f"the repo has {files} files and {lines} lines of code"

    git_connection = Github(
        login_or_token=token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    issue = repo.get_issue(number=payload['pull_request']['number'])

    # Create a comment with the random meme
    issue.create_comment(comment_msg)
    return "ok"


if __name__ == "__main__":
    app.run(debug=True, port=3000)