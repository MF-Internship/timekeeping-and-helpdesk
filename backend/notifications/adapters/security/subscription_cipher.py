from __future__ import annotations

import json
from dataclasses import asdict

from notifications.domain.subscriptions import SubscriptionMaterial


class SubscriptionCipherError(ValueError):
    pass


class FernetSubscriptionCipher:
    def __init__(self, keys: tuple[str, ...]) -> None:
        if not keys:
            raise SubscriptionCipherError("encryption key ring is empty")
        try:
            from cryptography.fernet import Fernet

            self._fernets = tuple(Fernet(key.encode("ascii")) for key in keys)
        except (ImportError, ValueError, UnicodeEncodeError) as error:
            raise SubscriptionCipherError("encryption key ring is invalid") from error

    def encrypt(self, material: SubscriptionMaterial) -> bytes:
        payload = json.dumps(asdict(material), separators=(",", ":"), sort_keys=True).encode()
        return self._fernets[0].encrypt(payload)

    def decrypt(self, ciphertext: bytes) -> SubscriptionMaterial:
        from cryptography.fernet import InvalidToken

        for fernet in self._fernets:
            try:
                payload = json.loads(fernet.decrypt(ciphertext))
                return SubscriptionMaterial(
                    endpoint=str(payload["endpoint"]),
                    p256dh=str(payload["p256dh"]),
                    auth=str(payload["auth"]),
                )
            except (InvalidToken, ValueError, KeyError, TypeError):
                continue
        raise SubscriptionCipherError("subscription material cannot be decrypted")
