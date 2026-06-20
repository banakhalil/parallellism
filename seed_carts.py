from shop.models import User, Product, Cart
import random

print("🧹 Clearing old carts...")
Cart.objects.all().delete()

users = list(User.objects.filter(is_superuser=False))
products = list(Product.objects.all())

print("🛒 Filling carts...")
for user in users:
    for product in random.sample(products, k=min(3, len(products))):
        Cart.objects.create(
            user=user,
            product=product,
            quantity=random.randint(1, 3),
            price=product.price
        )

print(f"✅ Done — {Cart.objects.count()} cart items created")
