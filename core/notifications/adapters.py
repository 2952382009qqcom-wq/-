"""Provider adapters. Providers are optional and failures stay in the outbox."""

import json
import os
from urllib import request


class PermanentDeliveryError(Exception):
    pass


class TemporaryDeliveryError(Exception):
    pass


class BasePushAdapter:
    def send(self, token, payload):
        raise NotImplementedError


class FCMAdapter(BasePushAdapter):
    """Minimal FCM HTTP v1 boundary; inject a provider in production.

    A raw key is deliberately never read from the repository. Until a provider URL
    and bearer token are configured, the outbox remains retryable.
    """
    def send(self, token, payload):
        endpoint = os.getenv("FCM_ENDPOINT", "").strip()
        bearer = os.getenv("FCM_BEARER_TOKEN", "").strip()
        if not endpoint or not bearer:
            raise TemporaryDeliveryError("FCM provider is not configured")
        body = json.dumps({"message": {"token": token, "notification": payload["notification"], "data": payload["data"]}}).encode()
        req = request.Request(endpoint, data=body, method="POST", headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=8) as response:
                return response.headers.get("x-message-id", "")
        except Exception as error:
            code = getattr(error, "code", 0)
            if code in {400, 404, 410}:
                raise PermanentDeliveryError("invalid_token") from error
            raise TemporaryDeliveryError("provider_unavailable") from error


class WebPushAdapter(BasePushAdapter):
    def send(self, token, payload):
        raise TemporaryDeliveryError("Web Push provider is not configured")


class APNsAdapter(BasePushAdapter):
    def send(self, token, payload):
        raise TemporaryDeliveryError("APNs provider is not configured")


ADAPTERS = {"android": FCMAdapter(), "web": WebPushAdapter(), "ios": APNsAdapter()}
