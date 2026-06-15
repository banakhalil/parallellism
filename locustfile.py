import time
import random
import uuid  
from locust import HttpUser, task, between
# the test flow here is 
# 1- register new user
# 2- add a product to cart
# 3- create order from cart
class ShopUser(HttpUser):
    # Simulates a user waiting between 1 and 3 seconds between tasks
    wait_time = between(1, 3)
    
    def on_start(self):
        """
        Runs automatically when a simulated user "wakes up".
        Generates and registers a unique user account .
        """
        # generate a random unique phone number 
        random_suffix = "".join([str(random.randint(0, 9)) for _ in range(7)])
        unique_phone = f"095{random_suffix}"
        
        # build unique registration data r each test user
        signup_data = {
            "username": f"user_{uuid.uuid4().hex[:6]}",
            "phone_number": unique_phone,
            "password": "judy"
        }
        
        # hit registration endpoint
        response = self.client.post("/api/register/", json=signup_data)
        
        if response.status_code == 201:
            token = response.json().get("Token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            print(f"Failed to register unique user ({unique_phone}): {response.text}")

    @task
    def place_order_flow(self):
        """
        Simulates the user adding an item to their cart, then checking out.
        Each user has their own cart, eliminating MySQL lock contention!
        """
        # Step 1: put something in the cart
        cart_payload = {
            "name": "mobile cover", 
            "quantity": 1
        }
        self.client.post("/api/cart/store/", json=cart_payload)
        # Step 2: create an order from the cart
        # generate a unique idempotency key for this order to prevent duplicate processing 
        unique_idempotency_key = str(uuid.uuid4())
        order_payload = {
            "pay_status": True,
            "location": "Damascus, baghdad street",
            "idempotency_key": unique_idempotency_key
        }
        custom_headers = {
            "Idempotency-Key": unique_idempotency_key
        }
        self.client.post("/api/orders/create/", json=order_payload, headers=custom_headers)