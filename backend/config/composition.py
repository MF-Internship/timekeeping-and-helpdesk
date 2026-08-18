from functools import lru_cache

from audit.adapters.persistence.recording import DjangoAuditRecorder
from identity.adapters.persistence.unit_of_work import DjangoUnitOfWork
from identity.adapters.persistence.users import DjangoUserRepository
from identity.adapters.security.passwords import DjangoPasswordService
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.application.authentication import AuthenticationService
from identity.application.container import IdentityContainer
from identity.application.dependencies import IdentityDependencies
from identity.application.queries import UserQueryService
from identity.application.self_service import SelfService
from identity.application.user_admin import UserAdminService
from identity.domain.accounts import AccountSnapshot


@lru_cache(maxsize=1)
def identity_container() -> IdentityContainer:
    users = DjangoUserRepository()
    passwords = DjangoPasswordService()
    sessions = SimpleJWTSessionRepository()
    audit = DjangoAuditRecorder()
    dependencies = IdentityDependencies(
        users=users,
        passwords=passwords,
        sessions=sessions,
        unit_of_work_factory=DjangoUnitOfWork,
        audit=audit,
    )
    authentication = AuthenticationService(dependencies)
    self_service = SelfService(dependencies)
    queries = UserQueryService(users)
    user_admin = UserAdminService(dependencies)
    return IdentityContainer(
        users=users,
        passwords=passwords,
        sessions=sessions,
        unit_of_work_factory=DjangoUnitOfWork,
        audit=audit,
        authentication=authentication,
        self_service=self_service,
        queries=queries,
        user_admin=user_admin,
    )


def identity_target_lookup(raw_user_id: str) -> AccountSnapshot | None:
    try:
        user_id = int(raw_user_id)
    except ValueError:
        return None
    return identity_container().users.get(user_id)


def authorize_identity_logout(actor_id: int, raw_refresh: str) -> None:
    identity_container().authentication.authorize_logout(actor_id, raw_refresh)
