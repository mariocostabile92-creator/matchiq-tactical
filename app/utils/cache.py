"""
app/utils/cache.py

Gestione cache centralizzata MatchIQ Tactical
"""

import time


def cache_valid(cache_item, seconds=60):
    """
    Verifica se una cache è ancora valida.
    """

    if not cache_item:
        return False

    timestamp = cache_item.get("timestamp")

    if not timestamp:
        return False

    age = time.time() - timestamp

    return age < seconds


def build_cache_item(data):
    """
    Costruisce item cache standard.
    """

    return {
        "timestamp": time.time(),
        "data": data
    }


def get_cache_age(cache_item):
    """
    Età cache in secondi.
    """

    if not cache_item:
        return None

    timestamp = cache_item.get("timestamp")

    if not timestamp:
        return None

    return int(time.time() - timestamp)


def clear_expired_cache(cache_dict, seconds):
    """
    Pulisce cache scadute automaticamente.
    """

    expired = []

    for key, value in cache_dict.items():

        if not cache_valid(value, seconds):
            expired.append(key)

    for key in expired:
        del cache_dict[key]

    return len(expired)