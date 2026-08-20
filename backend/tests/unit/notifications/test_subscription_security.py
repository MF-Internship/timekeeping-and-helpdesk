import base64

import pytest
from cryptography.fernet import Fernet

from notifications.adapters.security.endpoint_policy import (
    ExactEndpointPolicy,
    SubscriptionValidationError,
    endpoint_hash,
    validate_browser_key,
)
from notifications.adapters.security.subscription_cipher import (
    FernetSubscriptionCipher,
    SubscriptionMaterial,
)


def test_origin_policy_is_exact_https_and_hash_is_stable() -> None:
    policy = ExactEndpointPolicy(("https://push.example.test",))
    endpoint = policy.validate("https://push.example.test/send/opaque")
    assert endpoint_hash(endpoint) == endpoint_hash(endpoint)
    assert len(endpoint_hash(endpoint)) == 64
    with pytest.raises(SubscriptionValidationError):
        policy.validate("https://push.example.test.evil/send/opaque")
    with pytest.raises(SubscriptionValidationError):
        policy.validate("http://push.example.test/send/opaque")


def test_key_ring_encrypts_and_old_key_can_decrypt_after_rotation() -> None:
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    material = SubscriptionMaterial(
        "https://push.example.test/send/opaque",
        base64.urlsafe_b64encode(b"p256dh").decode().rstrip("="),
        base64.urlsafe_b64encode(b"auth").decode().rstrip("="),
    )
    ciphertext = FernetSubscriptionCipher((old_key,)).encrypt(material)
    assert material.endpoint.encode() not in ciphertext
    assert FernetSubscriptionCipher((new_key, old_key)).decrypt(ciphertext) == material
    assert validate_browser_key(material.auth) == material.auth
