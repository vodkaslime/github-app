'''
This is the module that handles Tabby indexing.
'''

import os
import subprocess
import re
import toml

class IndexingError(Exception):
    '''
    Raised when indexing has errors
    '''
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def make_structure(root: str):
    '''
    This is the function that given a root directory,
    returns its files structure.
    '''
    stack = [(root, "root", 0)]
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
    '''
    This is the function as an indexing task, which:
    1. create toml file
    2. calls local tabby command to start indexing
    3. print repo file structure after indexing succeeds
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

    root_path = os.path.expanduser("~/.tabby")
    file_path = os.path.join(root_path, "config.toml")
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(toml_config_str)

    # start indexing
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

    # print file structure
    arr = re.split(r'[:/]', url)
    repo_dir = "_".join([s for s in arr if s])
    repo_dir_path = os.path.join(root_path, "repositories", repo_dir)

    file_structure = make_structure(repo_dir_path)

    return file_structure
