
# Centralized Redis cache helpers


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
    """Call this whenever a product is created, updated, or deleted."""
    cache.delete(key_product_detail(product_id))
    cache.delete(key_products_list())


def invalidate_stores():
    """Call this whenever a store is created, updated, or deleted."""
    cache.delete(key_stores_list())
