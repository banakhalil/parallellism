from shop.models import User, Store, Product, Cart, Order, OrderItem
import os
import random
from django.db import connection
from shop.models import Wallet
# ─────────────────────────────────────────
# Grab real image filenames from your folders
# ─────────────────────────────────────────


def get_images(folder_name):
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']
    try:
        files = [
            f for f in os.listdir(folder_name)
            if any(f.lower().endswith(ext) for ext in extensions)
        ]
        return files if files else []
    except FileNotFoundError:
        return []


store_imgs = get_images('stores')
product_imgs = get_images('products')

# ─────────────────────────────────────────
# Import your models (Django shell already has the context)
# ─────────────────────────────────────────

# ─────────────────────────────────────────
# STEP 1 — Wipe old test data (keeps superusers)
# ─────────────────────────────────────────
print("🧹 Clearing old data...")
# OrderItem.objects.all().delete()
with connection.cursor() as cursor:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("DELETE FROM shop_wallettransaction")
    cursor.execute("DELETE FROM shop_wallet")
    cursor.execute("DELETE FROM shop_orderitem")
    cursor.execute("DELETE FROM shop_order")
    cursor.execute("DELETE FROM shop_cart")
    cursor.execute("DELETE FROM shop_product_stores")
    cursor.execute("DELETE FROM shop_product")
    cursor.execute("DELETE FROM shop_store")
    cursor.execute("DELETE FROM shop_user WHERE is_superuser = 0")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
Order.objects.all().delete()
Cart.objects.all().delete()
Product.objects.all().delete()
Store.objects.all().delete()
with connection.cursor() as cursor:
    try:
        cursor.execute("DELETE FROM shop_wallet")
    except Exception:
        pass
User.objects.filter(is_superuser=False).delete()


# ─────────────────────────────────────────
# STEP 2 — Create 20 users
# Phone numbers: 09660000001 → 09660000020
# Password for all of them: password123
# ─────────────────────────────────────────
print("👤 Creating users...")
users = []
for i in range(1, 401):
    phone = f'0966000{i:04d}'          # e.g. 0966000001
    user = User.objects.create_user(
        phone_number=phone,
        password='password123',
        first_name=f'FirstName{i}',
        last_name=f'LastName{i}',
        email=f'user{i}@test.com',
    )
    users.append(user)

print(f"   ✅ {len(users)} users created")
print("Wallet check:", Wallet.objects.filter(balance=1000000).count())

# ─────────────────────────────────────────
# STEP 3 — Create 3 stores
# ─────────────────────────────────────────
print("🏪 Creating stores...")
store_data = [
    ('Tech World',    'Electronics, laptops and gadgets',      'Damascus'),
    ('Fashion Hub',   'Clothing, shoes and accessories',       'Aleppo'),
    ('Home & Living', 'Furniture, kitchen and home decor',     'Homs'),
]

stores = []
for i, (name, desc, loc) in enumerate(store_data):
    # pick an image from your /stores folder, or leave blank if none found
    img_path = f'stores/{store_imgs[i % len(store_imgs)]}' if store_imgs else ''
    store = Store.objects.create(
        name=name,
        description=desc,
        image=img_path,
        location=loc,
    )
    stores.append(store)

print(f"   ✅ {len(stores)} stores created")

# ─────────────────────────────────────────
# STEP 4 — Create 15 products
# ─────────────────────────────────────────
print("📦 Creating products...")
product_data = [
    ('Laptop Pro 15',       'High-performance laptop for professionals',
     'Dell',      700,  999.99),
    ('Wireless Mouse',      'Ergonomic silent wireless mouse',
     'Logitech',  700,  29.99),
    ('Mechanical Keyboard', 'RGB mechanical gaming keyboard',
     'Razer',      700,  89.99),
    ('Monitor 27"',         '4K UHD IPS display monitor',
     'Samsung',    700, 349.99),
    ('USB-C Hub',           '7-in-1 USB-C multiport adapter',
     'Anker',     700,  39.99),
    ('Classic T-Shirt',     '100% cotton casual fit',
     'Zara',      700,  15.99),
    ('Slim Jeans',          'Stretch denim slim fit jeans',
     "Levi's",    700,  49.99),
    ('Running Shoes',       'Lightweight breathable running shoes',
     'Nike',      700,  89.99),
    ('Leather Wallet',      'Genuine leather bifold wallet',
     'Fossil',    700,  34.99),
    ('Sunglasses',          'UV400 polarized sunglasses',
     'RayBan',    700,  59.99),
    ('Coffee Maker',        '12-cup programmable coffee maker',
     'Philips',    700,  79.99),
    ('Desk Lamp',           'LED adjustable brightness desk lamp',
     'Xiaomi',    700,  24.99),
    ('Throw Pillow',        'Soft decorative throw pillow set',
     'IKEA',      700,  19.99),
    ('Air Fryer',           '5L digital touchscreen air fryer',
     'Tefal',      700, 129.99),
    ('Yoga Mat',            'Non-slip eco-friendly yoga mat',
     'Gaiam',     700,  29.99),
]


with connection.cursor() as cursor:
    try:
        cursor.execute(
            "ALTER TABLE shop_product MODIFY COLUMN version INT NOT NULL DEFAULT 0")
    except Exception:
        try:
            cursor.execute(
                "ALTER TABLE shop_product ADD COLUMN version INT NOT NULL DEFAULT 0")
        except Exception:
            pass

products = []
for i, (name, desc, brand, qty, price) in enumerate(product_data):
    img_path = f'products/{product_imgs[i % len(product_imgs)]}' if product_imgs else ''
    p = Product(
        name=name,
        description=desc,
        brand=brand,
        quantity=qty,
        price=price,
        image=img_path,
    )
    p.save()
    # link each product to 1–2 random stores
    p.stores.set(random.sample(stores, k=random.randint(1, 2)))
    products.append(p)

print(f"   ✅ {len(products)} products created")

# ─────────────────────────────────────────
# STEP 5 — Add cart items for all 20 users
# Each user gets 3 random products in their cart
# (JMeter will simulate these users hitting the API)
# ─────────────────────────────────────────
print("🛒 Filling carts...")
for user in users:
    for product in random.sample(products, k=3):
        Cart.objects.get_or_create(
            user=user,
            product=product,
            defaults={
                'quantity': random.randint(1, 3),
                'price': product.price,
            }
        )

print(f"   ✅ Carts filled")

# ─────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────
print("\n" + "="*45)
print("✅  SEEDING COMPLETE")
print("="*45)
print(f"  Users    : {User.objects.filter(is_superuser=False).count()}")
print(f"  Stores   : {Store.objects.count()}")
print(f"  Products : {Product.objects.count()}")
print(f"  Carts    : {Cart.objects.count()}")
print("="*45)
print("  All user passwords : password123")
print("  Phone range        : 0966000001 → 0966000020")
print("="*45)
