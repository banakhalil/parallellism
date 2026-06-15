

import random
from locust import HttpUser, task, between, constant_throughput


class CacheTestUser(HttpUser):
    """
    Simulates a read-heavy browsing user.
    Mix: 50% list products, 30% single product, 20% list stores.
    These are exactly the 3 endpoints that get cached in Req 6.
    No auth needed — all are AllowAny.
    """
    wait_time = between(0.5, 1.5)

    # Product IDs to test  (15 products)
    PRODUCT_IDS = list(range(1, 16))
    # PRODUCT_IDS = [16, 17, 18]  #  IDs يتكرر كتير

    @task(5)
    def browse_all_products(self):
        """GET /api/products/ — highest traffic endpoint, benefits most from cache."""
        with self.client.get(
            "/api/products/",
            name="/api/products/ [LIST]",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(3)
    def view_single_product(self):
        """GET /api/products/<id>/ — per-product cache hit."""
        product_id = random.choice(self.PRODUCT_IDS)
        with self.client.get(
            f"/api/products/{product_id}/",
            name="/api/products/[id]/ [DETAIL]",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                resp.success()   # product may not exist, still a valid response
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(2)
    def browse_all_stores(self):
        """GET /api/stores/ — store list, cached for 10 min."""
        with self.client.get(
            "/api/stores/",
            name="/api/stores/ [LIST]",
            catch_response=True
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
