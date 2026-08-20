from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Event

import pytest
from django.db import close_old_connections, transaction

from core.errors import IdentityAPIError
from identity.models import User
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import CreateTaskCommand
from tasks.models import Task, TaskAssignee
from tests.integration.api.identity.helpers import create_user
from tests.integration.postgres.tasks.helpers import commands, production_dependencies

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_mixed_ineligible_assignment_rolls_back_task_and_links() -> None:
    manager = create_user("pg-create-manager", "MANAGER")
    eligible = create_user("pg-create-eligible")
    inactive = create_user("pg-create-inactive", active=False)
    with pytest.raises(IdentityAPIError) as caught:
        commands().create(
            CreateTaskCommand(
                manager.pk,
                "Atomic",
                "",
                date.today(),
                assignee_ids=(eligible.pk, inactive.pk, inactive.pk + 9999),
            )
        )
    assert caught.value.error_code == "INACTIVE_ASSIGNEE"
    assert caught.value.details["assignee_ids"] == [inactive.pk, inactive.pk + 9999]
    assert not Task.objects.exists() and not TaskAssignee.objects.exists()


@pytest.mark.parametrize("change", ["deactivate", "role"])
def test_assign_and_account_change_serialize_without_invalid_new_link(  # noqa: PLR0915
    change: str,
) -> None:
    manager = create_user(f"pg-assign-{change}-manager", "MANAGER")
    target = create_user(f"pg-assign-{change}-target")
    barrier = Barrier(2)

    def assign() -> str:
        close_old_connections()
        barrier.wait()
        try:
            commands().create(
                CreateTaskCommand(
                    manager.pk,
                    "Race",
                    "",
                    date.today(),
                    assignee_ids=(target.pk,),
                )
            )
        except IdentityAPIError as error:
            outcome = error.error_code
        else:
            outcome = "CREATED"
        close_old_connections()
        return outcome

    def change_account() -> str:
        close_old_connections()
        barrier.wait()
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=target.pk)
            if change == "deactivate":
                locked.is_active = False
                locked.save(update_fields=["is_active"])
            else:
                locked.role = "LEADER"
                locked.save(update_fields=["role"])
        close_old_connections()
        return "CHANGED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = [
            future.result() for future in (pool.submit(assign), pool.submit(change_account))
        ]
    assert "CHANGED" in outcomes
    assert outcomes[0] in {"CREATED", "INACTIVE_ASSIGNEE"}
    if outcomes[0] == "CREATED":
        assert TaskAssignee.objects.filter(user=target).count() == 1
    else:
        assert not Task.objects.exists()


@pytest.mark.parametrize(
    ("change", "expected_error"),
    [("deactivate", "ACCOUNT_INACTIVE"), ("role", "PERMISSION_DENIED")],
)
def test_self_create_and_account_change_serialize_with_account_gate(  # noqa: PLR0915
    change: str,
    expected_error: str,
) -> None:
    actor = create_user(f"pg-self-{change}")
    barrier = Barrier(2)

    def self_create() -> str:
        close_old_connections()
        barrier.wait()
        try:
            commands().create(CreateTaskCommand(actor.pk, "Self", "", date.today()))
        except IdentityAPIError as error:
            result = error.error_code
        else:
            result = "CREATED"
        close_old_connections()
        return result

    def change_account() -> None:
        close_old_connections()
        barrier.wait()
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=actor.pk)
            if change == "deactivate":
                locked.is_active = False
                locked.save(update_fields=["is_active"])
            else:
                locked.role = "LEADER"
                locked.save(update_fields=["role"])
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        create_future = pool.submit(self_create)
        change_future = pool.submit(change_account)
        outcome = create_future.result()
        change_future.result()
    assert outcome in {"CREATED", expected_error}
    assert Task.objects.count() == (1 if outcome == "CREATED" else 0)


@pytest.mark.parametrize("create_mode", ["ASSIGN", "SELF"])
@pytest.mark.parametrize("change", ["deactivate", "role"])
@pytest.mark.parametrize("lock_order", ["assignment_first", "account_first"])
def test_create_vs_account_change_observes_both_lock_orders(  # noqa: C901, PLR0915
    create_mode: str,
    change: str,
    lock_order: str,
) -> None:
    actor_role = "MANAGER" if create_mode == "ASSIGN" else "HELPDESK"
    actor = create_user(f"pg-order-{create_mode}-{change}-{lock_order}-actor", actor_role)
    target = (
        create_user(f"pg-order-{create_mode}-{change}-{lock_order}-target")
        if create_mode == "ASSIGN"
        else actor
    )
    assignment_reached = Event()
    account_reached = Event()
    release = Event()
    production = production_dependencies()

    class CoordinatedDirectory:
        def lock_eligible(self, user_ids: tuple[int, ...]) -> object:
            return self._coordinate(lambda: production.assignees.lock_eligible(user_ids))

        def lock_and_reauthorize_self(self, actor_id: int) -> object:
            return self._coordinate(
                lambda: production.assignees.lock_and_reauthorize_self(actor_id)
            )

        @staticmethod
        def _coordinate(operation: object) -> object:
            if lock_order == "assignment_first":
                result = operation()  # type: ignore[operator]
                assignment_reached.set()
                assert release.wait(5)
                return result
            assignment_reached.set()
            return operation()  # type: ignore[operator]

    dependencies = TaskDependencies(
        production.authorization,
        CoordinatedDirectory(),  # type: ignore[arg-type]
        production.locations,
        production.repository,
        production.clock,
        production.audit,
        production.unit_of_work_factory,
    )

    def create() -> str:
        close_old_connections()
        assignee_ids = (target.pk,) if create_mode == "ASSIGN" else ()
        try:
            TaskCommandService(dependencies).create(
                CreateTaskCommand(
                    actor.pk,
                    "Ordered race",
                    "",
                    date.today(),
                    assignee_ids=assignee_ids,
                )
            )
        except IdentityAPIError as error:
            outcome = error.error_code
        else:
            outcome = "CREATED"
        close_old_connections()
        return outcome

    def change_account() -> None:
        close_old_connections()
        if lock_order == "assignment_first":
            account_reached.set()
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=target.pk)
            if lock_order == "account_first":
                account_reached.set()
                assert release.wait(5)
            if change == "deactivate":
                locked.is_active = False
                locked.save(update_fields=["is_active"])
            else:
                locked.role = "LEADER"
                locked.save(update_fields=["role"])
        close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(create if lock_order == "assignment_first" else change_account)
        assert (assignment_reached if lock_order == "assignment_first" else account_reached).wait(5)
        second = pool.submit(change_account if lock_order == "assignment_first" else create)
        assert (account_reached if lock_order == "assignment_first" else assignment_reached).wait(5)
        release.set()
        first_result = first.result()
        second_result = second.result()
    outcome = first_result if lock_order == "assignment_first" else second_result
    expected_error = (
        "INACTIVE_ASSIGNEE"
        if create_mode == "ASSIGN"
        else ("ACCOUNT_INACTIVE" if change == "deactivate" else "PERMISSION_DENIED")
    )
    assert outcome == ("CREATED" if lock_order == "assignment_first" else expected_error)
    assert Task.objects.count() == (1 if lock_order == "assignment_first" else 0)
