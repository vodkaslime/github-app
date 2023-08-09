'''
This module is the FastAPI main app as backend of Github App,
which handles indexing jobs per repository pull requests.
'''

from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Header

from src.indexing import IndexingTask
from src.model import WebhookRequest
from src.task_manager import TaskManager
from src.validation import validate_signature

app = FastAPI()

pull_request_actions = ["opened", "closed", "reopened"]

# Create task manager
task_manager = TaskManager(100)
task_manager.start_consumer()

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

    # Submit the indexing job
    task_manager.submit(IndexingTask(request))

    return "ok"

@app.on_event("shutdown")
def shutdown_event():
    '''
    Handle clean ups when shutting down app.
    '''
    task_manager.submit(None)
