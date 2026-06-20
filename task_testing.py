import random
import uuid

from locust import HttpUser, task, between
import time
from itertools import cycle


product_id = 19
PRODUCT_NAME = "Nature Magazine test 4"


class AuthenticatedUser(HttpUser):  # to authenticate users
    abstract = True
    wait_time = between(1, 2)

    token = None

    def on_start(self):

        response = self.client.post(
            "/api/login/",
            json={
                "phone_number": "0959948811",
                "password": "0959948811"
            }
        )

        if response.status_code == 200:
            self.token = response.json()["Token"]
            print("Login successful")

        else:
            print("Login failed")
            print(response.text)

    def auth_headers(self):
        return {
            "Authorization": f"Bearer {self.token}"
        }


# to test 2 admins trying to update the same row at the same time, there must be 2 admins and the store and the product in the database
class UpdateRaceUser(AuthenticatedUser):

    @task
    def concurrent_quantity_update(self):

        headers = self.auth_headers()

        response = self.client.get(
            f"/api/products/{product_id}/",
            headers=headers
        )

        if response.status_code != 200:
            print("Failed to fetch product")
            return

        product_data = response.json()

        current_quantity = product_data["Product"]["quantity"]

        print(f"Current quantity: {current_quantity}")

        new_quantity = current_quantity + 1

        time.sleep(2)

        update_response = self.client.put(
            f"/api/products/{product_id}/update/",
            json={
                "quantity": new_quantity
            },
            headers=headers
        )

        print(
            f"UPDATE {current_quantity} -> {new_quantity} | "
            f"status={update_response.status_code}"
        )


# to test 2 admins trying to delete the same row at the same time, there must be 2 admins and the store and the product in the database
class DeleteRaceUser(AuthenticatedUser):

    @task
    def concurrent_delete_product(self):

        headers = self.auth_headers()

        response = self.client.get(
            f"/api/products/{product_id}/",
            headers=headers
        )

        if response.status_code != 200:
            print("Product already deleted")
            return

        print("Product exists before delete")

        time.sleep(2)

        delete_response = self.client.delete(
            f"/api/products/{product_id}/delete/",
            headers=headers
        )

        print(
            f"DELETE status={delete_response.status_code}"
        )


# to test an admin trying to delete a produt that is in a customer cart, there must be an admin, a customer with cart,store, product in the database
class CartDeleteRaceUser(AuthenticatedUser):

    @task
    def add_to_cart_during_delete(self):

        headers = self.auth_headers()

        response = self.client.get(
            f"/api/products/{product_id}/",
            headers=headers
        )

        if response.status_code != 200:
            print("Product not found")
            return

        product = response.json()["Product"]

        print(f"User sees product: {product['name']}")

        time.sleep(random.uniform(0.1, 0.5))

        cart_response = self.client.post(
            "/api/cart/store/",
            json={
                "name": product["name"],
                "quantity": 1
            },
            headers=headers
        )

        print(
            f"CART status={cart_response.status_code}"
        )


# test the admin tries to delete a product
class AdminDeleteUser(AuthenticatedUser):

    @task
    def delete_product(self):

        headers = self.auth_headers()

        time.sleep(random.uniform(0.1, 0.3))

        delete_response = self.client.delete(
            f"/api/products/{product_id}/delete/",
            headers=headers
        )

        print(
            f"ADMIN DELETE status={delete_response.status_code}"
        )


# two users try to create order with the last item left from the product (product quantity = 1 )
class OrderRaceUser(HttpUser):
    # there must me two authenticated users with these credentials in the database
    wait_time = between(0.1, 0.2)

    user_cycle = cycle([
        {
            "phone_number": "0959948811",
            "password": "0959948811"
        },
        {
            "phone_number": "0959948822",
            "password": "0959948822"
        }
    ])

    def on_start(self):

        creds = next(self.user_cycle)

        response = self.client.post(
            "/api/login/",
            json=creds
        )

        if response.status_code != 200:

            print("Login failed")
            print(response.text)
            return

        self.token = response.json()["Token"]

        print(f"Login success: {creds['phone_number']}")

        headers = self.auth_headers()

        # add product to cart
        cart_response = self.client.post(
            "/api/cart/store/",
            json={
                "name": PRODUCT_NAME,
                "quantity": 1
            },
            headers=headers
        )

        print(
            f"ADD TO CART status={cart_response.status_code}"
        )

    def auth_headers(self):

        return {
            "Authorization": f"Bearer {self.token}"
        }

    @task
    def create_order_race(self):

        headers = self.auth_headers()

        response = self.client.post(
            "/api/orders/create/",
            json={
                "location": "Test Location",
                "idempotency_key": str(uuid.uuid4())
            },
            headers=headers
        )

        print(
            f"CREATE ORDER "
            f"status={response.status_code} "
            f"response={response.text}"
        )

        # stop repeated order creation
        self.stop(True)

#


order_id = 37


# to test two payment requests at the same time (like pressing the "pay" button twice)
class WalletPaymentRaceUser(HttpUser):
    # there must be an order and a user with the credentials

    wait_time = between(0.1, 0.2)

    def on_start(self):

        response = self.client.post(
            "/api/login/",
            json={
                "phone_number": "0959948821",
                "password": "0959948821"
            }
        )

        if response.status_code != 200:

            print("Login failed")
            print(response.text)
            return

        self.token = response.json()["Token"]

        print("Login successful")

    def auth_headers(self):

        return {
            "Authorization": f"Bearer {self.token}"
        }

    @task
    def concurrent_payment(self):

        headers = self.auth_headers()

        response = self.client.post(
            f"/api/orders/{order_id}/pay/",
            headers=headers
        )

        print(
            f"PAY status={response.status_code} "
            f"response={response.text}"
        )

        self.stop(True)


# to test cancelling payment requests at the same time (like pressing the "cancel" button twice)
class CancelOrderRaceUser(HttpUser):
    # there must be an order and a user with the credentials

    wait_time = between(0.1, 0.2)

    def on_start(self):

        response = self.client.post(
            "/api/login/",
            json={
                "phone_number": "0959948815",
                "password": "0959948815"
            }
        )

        if response.status_code != 200:

            print("Login failed")
            print(response.text)
            return

        self.token = response.json()["Token"]

        print("Login successful")

    def auth_headers(self):

        return {
            "Authorization": f"Bearer {self.token}"
        }

    @task
    def concurrent_cancel_order(self):

        # Small delay to help synchronize both users
        time.sleep(0.5)

        headers = self.auth_headers()

        response = self.client.post(
            f"/api/orders/{order_id}/cancel/",
            headers=headers
        )

        print(
            f"CANCEL status={response.status_code} "
            f"response={response.text}"
        )

        # stop repeated looping
        self.stop(True)
