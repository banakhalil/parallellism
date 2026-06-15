from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager,User

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        # جعل الـ username يطابق الهاتف تلقائياً لضمان الفرادة
        extra_fields.setdefault('username', phone_number)
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    
    location = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=50, default='user')
    image = models.ImageField(upload_to='users/', blank=True, null=True)
    
    email = models.EmailField(unique=True, blank=True, null=True)
    x_and_y = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = [] # تركناها فارغة لأن التسجيل بالهاتف فقط

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

# 2. Store Model
class Store(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='stores/')
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# 3. Product Model
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    quantity = models.IntegerField()
    price = models.FloatField() # يقابل double
    image = models.ImageField(upload_to='products/')
    version = models.IntegerField(default=0)  # Optimistic locking token incremented on every successful update.
    # علاقة Many-to-Many مع المتجر
    stores = models.ManyToManyField(Store, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# 4. Favorite Model (One-to-Many مع المستخدم والمنتج)
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

# 5. Cart Model
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='carts')
    quantity = models.IntegerField()
    price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# 6. Order Model
class Order(models.Model):
    STATE_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    idempotency_key = models.CharField(max_length=128, null=True, blank=True, db_index=True)  # to prevent duplicate orders on retries/double-submit (create_order method).
    cost = models.FloatField()
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='pending')
    location = models.CharField(max_length=255, blank=True, null=True)
    pay_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'idempotency_key'],
                name='unique_order_user_idempotency_key',
            )
        ]

# 7. Order Item Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

# 8 . wallet

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance}"
    
# 9 .Transaction

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'إيداع/شحن'),
        ('withdraw', 'سحب/دفع'),
        ('refund', 'استرداد'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True) # لربط العملية بطلب معين
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.wallet.user.username}"    


class DailyAuditLog(models.Model):
    audit_date = models.DateTimeField(auto_now_add=True, verbose_name="Audit Date & Time")
    method_used = models.CharField(max_length=50, verbose_name="Processing Method")
    total_orders_processed = models.IntegerField(verbose_name="Total Orders Processed")
    total_sales_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Sales Amount")
    execution_time = models.FloatField(verbose_name="Execution Time (Seconds)")
    ram_consumption = models.FloatField(verbose_name="RAM Consumption (MB)")
    status = models.CharField(max_length=20, default="Success", verbose_name="Audit Status")

    class Meta:
        verbose_name = "Daily Audit Log"
        verbose_name_plural = "Daily Audit Logs"
        ordering = ['-audit_date']

    def __str__(self):
        return f"Audit {self.method_used} - {self.audit_date.strftime('%Y-%m-%d %H:%M')}"    
