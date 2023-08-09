'''
This is the module that handles Tabby indexing.
'''

import os
import subprocess
import re
import toml
from dotenv import load_dotenv
from github import Github, GithubIntegration

from src.model import WebhookRequest

load_dotenv()
app_id = os.getenv("APP_ID")
private_key_path = os.getenv("PRIVATE_KEY_PATH")

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

root_path = os.path.expanduser("~/.tabby")

class IndexingError(Exception):
    '''
    Raised when indexing has errors
    '''
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class IndexingTask():
    '''
    This is the class representing a indexing request.
    '''
    def __init__(self, request: WebhookRequest):
        self.request = request

    def get_repo_structure(self, url: str) -> str:
        '''
        This is the function that given a url,
        returns its files structure.
        '''
        arr = re.split(r'[:/]', url)
        repo_dir = "_".join([s for s in arr if s])
        repo_dir_path = os.path.join(root_path, "repositories", repo_dir)

        stack = [(repo_dir_path, "root", 0)]
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

    def index(self, url):
        '''
        This is the function that:
        1. creates toml file
        2. calls local tabby command to start indexing
        3. prints repo file structure after indexing succeeds
        '''
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

        file_path = os.path.join(root_path, "config.toml")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(toml_config_str)

        # Start indexing
        cmd = "docker run -it -v $HOME/.tabby:/data tabbyml/tabby scheduler --now"
        if os.getenv("DEV_ENV"):
            cmd = "docker run -it \
                -e HTTP_PROXY=http://localhost:7890 \
                -e HTTPS_PROXY=http://localhost:7890 \
                --network host \
                -v $HOME/.tabby:/data \
                tabbyml/tabby scheduler --now"

        task = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if task.stderr:
            print(task.stderr)
            raise IndexingError("error indexing")
        return

    def run(self):
        '''
        Runs the tabby indexing task.
        '''
        request = self.request
        owner = request.repository.owner.login
        repo_name = request.repository.name

        token = git_integration.get_access_token(
            git_integration.get_repo_installation(owner, repo_name).id
        ).token
        url = f"https://oauth2:{token}@github.com/{owner}/{repo_name}"

        # Run the indexing command
        self.index(url)

        # Get file structure
        comment_msg = self.get_repo_structure(url)

        git_connection = Github(login_or_token=token)
        repo = git_connection.get_repo(f"{owner}/{repo_name}")
        issue = repo.get_issue(number=request.pull_request.number)

        # Create a comment with the random meme
        issue.create_comment(comment_msg)
