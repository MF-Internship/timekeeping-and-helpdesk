from identity.models import User
from identity.ports.notification_facts import AccountNotificationEligibility


class DjangoAccountNotificationFacts:
    def get_eligibility(self, user_id: int) -> AccountNotificationEligibility | None:
        row = User.objects.filter(pk=user_id).values("id", "is_active").first()
        if row is None:
            return None
        return AccountNotificationEligibility(int(row["id"]), bool(row["is_active"]))
