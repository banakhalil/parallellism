from celery import shared_task
import time

@shared_task
def send_order_notification(order_id, user_email):
    """مهمة خلفية محاكية لإرسال بريد إلكتروني عند نجاح الطلب"""
    print(f"[Celery] Starting to send email notification for Order #{order_id} to {user_email}...")
    time.sleep(3)  # محاكاة وقت إرسال الإيميل
    print(f"[Celery] Email sent successfully to {user_email}!")
    return True