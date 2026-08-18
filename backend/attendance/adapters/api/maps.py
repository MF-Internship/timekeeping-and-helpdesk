from decimal import Decimal
from urllib.parse import urlencode


def attendance_maps_url(latitude: Decimal, longitude: Decimal) -> str:
    coordinates = f"{latitude},{longitude}"
    return f"https://www.google.com/maps?{urlencode({'q': coordinates})}"
