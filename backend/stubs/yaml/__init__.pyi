from typing import IO, Any

class YAMLError(Exception): ...

def safe_load(stream: IO[str] | str) -> Any: ...
def safe_dump(
    data: object,
    *,
    allow_unicode: bool = ...,
    sort_keys: bool = ...,
    default_flow_style: bool = ...,
) -> str: ...
