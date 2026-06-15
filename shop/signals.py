from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wallet
from .models import User, Wallet  # استيراد المستخدم الخاص بمشروعك وليس الافتراضي
@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
        print(f"تم إنشاء محفظة تلقائياً للمستخدم: {instance.username}")