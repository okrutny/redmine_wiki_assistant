import hmac
import hashlib
import os
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SlackSignatureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print("🚨 Slack middleware active")
        if os.getenv("SKIP_SLACK_VERIFY", "").lower() == "true":
            print("SKIP_SLACK_VERIFY enabled — skipping signature check")
            return await call_next(request)

        slack_signature = request.headers.get("X-Slack-Signature")
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")

        if not slack_signature or not timestamp or not signing_secret:
            return JSONResponse({"detail": "Slack headers or secret missing"}, status_code=403)

        if abs(time.time() - int(timestamp)) > 60 * 5:
            return JSONResponse({"detail": "Request timestamp too old"}, status_code=403)

        body = await request.body()
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        computed_signature = "v0=" + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_signature, slack_signature):
            return JSONResponse({"detail": "Invalid Slack signature"}, status_code=403)

        return await call_next(request)
