'''
This module is for webhook signature validation.
'''

import os
import hmac
import hashlib

from dotenv import load_dotenv

load_dotenv()
webhook_secret = os.getenv("WEBHOOK_SECRET")

class ValidationError(Exception):
    '''
    Raised when validation has errors
    '''
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def validate_signature(signature_header: str, data: bytes):
    '''
    Given params:
    
    signature_header: str,
    data: bytes,
    
    raise ValidationError if validation fails.
    Otherwise return with nothing.
    '''
    sha_name, github_signature = signature_header.split('=')
    if sha_name != 'sha1':
        raise ValidationError("invalid signature header")

    local_signature = hmac.new(webhook_secret.encode('utf-8'), msg=data, digestmod=hashlib.sha1)

    if not hmac.compare_digest(local_signature.hexdigest(), github_signature):
        raise ValidationError("invalid signature")
