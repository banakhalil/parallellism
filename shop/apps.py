from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop' # استبدل باسم تطبيقك

    def ready(self):
        # هذه الدالة تعمل مرة واحدة عند تشغيل السيرفر
        import shop.signals  # استدعاء ملف الـ signals لربط "الجرس"


    