def invalid_nesting(value: int) -> int:
    if value:
        for item in range(value):
            if item:
                while value:
                    return item
    return 0
