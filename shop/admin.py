from django.contrib import admin
from .models import User, Store, Product, Order, OrderItem, Favorite, Cart, Wallet, WalletTransaction ,DailyAuditLog
# 1. تخصيص عرض المنتجات (اختياري لكن مفيد جداً)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'quantity', 'brand')
    search_fields = ('name', 'brand')

# 2. تخصيص عرض المحفظة
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username',)

# 3. تخصيص عرض عمليات المحفظة
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'created_at')
    list_filter = ('transaction_type', 'created_at')

# تسجيل الموديلات في لوحة التحكم
admin.site.register(User)
admin.site.register(Store)
admin.site.register(Product, ProductAdmin) # تم ربطه بالتخصيص أعلاه
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Favorite)
admin.site.register(Cart)

# إضافة الجداول الجديدة التي سألت عنها
admin.site.register(Wallet, WalletAdmin)
admin.site.register(WalletTransaction, WalletTransactionAdmin)

@admin.register(DailyAuditLog)
class DailyAuditLogAdmin(admin.ModelAdmin):
    list_display = ('audit_date', 'method_used', 'total_orders_processed', 'total_sales_amount', 'execution_time', 'ram_consumption', 'status')
    list_filter = ('method_used', 'status', 'audit_date')
    readonly_fields = ('audit_date',)