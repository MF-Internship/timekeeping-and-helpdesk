from django.urls import path

from notifications.adapters.api.views import (
    NotificationInboxView,
    NotificationReadView,
    NotificationTargetView,
    PushSubscriptionCollectionView,
    PushSubscriptionDetailView,
)

urlpatterns = [
    path("notifications/", NotificationInboxView.as_view(), name="notification-inbox"),
    path(
        "notifications/<str:public_id>/read",
        NotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/<str:public_id>/target",
        NotificationTargetView.as_view(),
        name="notification-target",
    ),
    path(
        "push-subscriptions/",
        PushSubscriptionCollectionView.as_view(),
        name="push-subscription-upsert",
    ),
    path(
        "push-subscriptions/<str:public_id>/",
        PushSubscriptionDetailView.as_view(),
        name="push-subscription-revoke",
    ),
]
