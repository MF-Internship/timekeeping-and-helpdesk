from notifications.models import Notification, PushDelivery, PushSubscription


def test_notification_models_expose_required_database_guards() -> None:
    notification_constraints = {item.name for item in Notification._meta.constraints}
    assert {
        "notification_event_type_valid",
        "notification_target_type_valid",
        "notification_target_id_positive",
        "notification_dedupe_nonblank",
        "notification_title_nonblank",
        "notification_read_time_valid",
    } <= notification_constraints
    assert Notification._meta.get_field("recipient").remote_field.on_delete.__name__ == "PROTECT"
    assert (
        PushSubscription._meta.get_field("encrypted_subscription").get_internal_type()
        == "BinaryField"
    )
    assert any(
        item.name == "push_subscription_active_endpoint_uniq"
        for item in PushSubscription._meta.constraints
    )
    assert any(
        item.name == "push_delivery_notification_subscription_uniq"
        for item in PushDelivery._meta.constraints
    )
