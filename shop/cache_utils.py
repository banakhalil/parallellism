
# Centralized Redis cache helpers


import time
import json
from django.core.cache import cache

#  TTL constants (seconds)
CACHE_TTL_PRODUCTS_LIST = 60 * 5   # 5 minutes
CACHE_TTL_PRODUCT_DETAIL = 60 * 5   # 5 minutes
CACHE_TTL_STORES_LIST = 60 * 10  # 10 minutes


def key_products_list():
    return "shop:products:all"


def key_product_detail(product_id):
    return f"shop:products:{product_id}"


def key_stores_list():
    return "shop:stores:all"

# Invalidation


def invalidate_product(product_id):
    cache.delete(key_product_detail(product_id))
    cache.delete(key_products_list())


def invalidate_stores():
    cache.delete(key_stores_list())


def get_data_with_lock(cache_key, db_callback, ttl):
    data = cache.get(cache_key)
    if data is not None:
        return data
    lock_key = f"lock:{cache_key}"
    with cache.lock(lock_key, timeout=10, blocking_timeout=5):
        data = cache.get(cache_key)
        if data is not None:
            return data
        print(f"Lock acquired for {cache_key}. Hitting Database...")
        data = db_callback()
        cache.set(cache_key, data, ttl)

        return data
