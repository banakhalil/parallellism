# orders/tasks.py
from celery import shared_task
import time

@shared_task
def send_order_notification(order_id, user_email):
    """
    Simulates sending a notification (Email/Push).
    """
    print(f"Starting background notification for Order #{order_id} ")
    
    # Simulate a delay (like connecting to an email server)
    time.sleep(5) 
    
    print(f"Notification sent successfully to {user_email}!")
    return f"Notification sent for order {order_id}"