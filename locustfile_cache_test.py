

import random
from locust import HttpUser, task, between, constant_throughput
import uuid


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


# test for the admin


# PRODUCT_ID = 1


# class ProductReader(HttpUser):
#     """
#     Heavy read traffic.
#     All users hit the SAME product to force contention
#     on a single cache key and a single cache lock.
#     """

#     weight = 99

#     # ~10 requests/sec per user
#     wait_time = constant_throughput(10)

#     @task
#     def get_product(self):
#         with self.client.get(
#             f"/api/products/{PRODUCT_ID}/",
#             name="GET Product Detail",
#             catch_response=True
#         ) as response:

#             if response.status_code == 200:
#                 response.success()
#             else:
#                 response.failure(f"Unexpected status: {response.status_code}")


# class AdminUpdater(HttpUser):
#     """
#     Periodically updates the product.

#     Flow:
#         1. Read current product version
#         2. Update product
#         3. Cache gets invalidated
#         4. Readers flood GET endpoint
#         5. One request rebuilds cache
#     """

#     weight = 1

#     # update every few seconds
#     wait_time = between(5, 10)

#     @task
#     def update_product(self):

#         # Step 1: Get latest version
#         response = self.client.get(
#             f"/api/products/{PRODUCT_ID}/",
#             name="Admin GET Product"
#         )

#         if response.status_code != 200:
#             return

#         try:
#             data = response.json()
#             version = data["Product"]["version"]
#         except Exception:
#             return

#         # Step 2: Update product
#         payload = {
#             "expected_version": version,

#             # Small random price change
#             "price": round(random.uniform(50, 500), 2)
#         }

#         with self.client.put(
#             f"/api/products/{PRODUCT_ID}/update/",
#             json=payload,
#             name="Admin Update Product",
#             catch_response=True
#         ) as update_response:
#             print("STATUS:", update_response.status_code)
#             print("BODY:", update_response.text)

#             if update_response.status_code in (200, 409):
#                 # 409 can happen if another update sneaks in
#                 update_response.success()
#             else:
#                 update_response.failure(
#                     f"Unexpected status: {update_response.status_code}"
                # )
