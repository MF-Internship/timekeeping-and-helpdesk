from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID


def test_ten_thousand_generated_request_ids_are_unique_uuid4() -> None:
    from core.correlation import bind_correlation, get_request_id, reset_correlation

    issued: set[str] = set()
    for _ in range(10_000):
        token = bind_correlation()
        issued.add(get_request_id())
        reset_correlation(token)
    assert len(issued) == 10_000
    assert all(UUID(value).version == 4 for value in issued)
    assert get_request_id() == ""


def test_competing_threads_do_not_leak_context() -> None:
    from core.correlation import bind_correlation, get_correlation, reset_correlation

    def worker() -> tuple[tuple[str, str], tuple[str, str]]:
        token = bind_correlation()
        try:
            observed = get_correlation()
        finally:
            reset_correlation(token)
        return observed, get_correlation()

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda _: worker(), range(200)))
    assert len({observed[0] for observed, _ in results}) == 200
    assert all(observed[0] == observed[1] for observed, _ in results)
    assert all(clean == ("", "") for _, clean in results)


def test_competing_async_tasks_restore_parent_and_cleanup() -> None:
    from core.correlation import bind_correlation, get_correlation, reset_correlation

    async def worker() -> tuple[str, str]:
        token = bind_correlation()
        try:
            await asyncio.sleep(0)
            return get_correlation()
        finally:
            reset_correlation(token)

    async def scenario() -> list[tuple[str, str]]:
        outer = bind_correlation("00000000-0000-4000-8000-000000000001")
        try:
            results = await asyncio.gather(*(worker() for _ in range(100)))
            assert get_correlation()[0].endswith("1")
            return results
        finally:
            reset_correlation(outer)

    results = asyncio.run(scenario())
    assert len({request_id for request_id, _ in results}) == 100
    assert all(request_id == correlation_id for request_id, correlation_id in results)
    assert get_correlation() == ("", "")
