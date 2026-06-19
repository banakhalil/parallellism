from django.db import transaction, OperationalError
import os
import time
import re

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated

from core.tasks import send_order_notification

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.shortcuts import render, get_object_or_404
from django.db import OperationalError


from .tasks import send_order_notification
from concurrent.futures import as_completed
from shop.thread_pool import get_pool

from decimal import Decimal

from .models import Cart, Product, Favorite, Store, Order, OrderItem, WalletTransaction, Wallet
from .serializers import CartSerializer, UserSerializer, StoreSerializer, StoreWithProductsSerializer, ProductSerializer, OrderSerializer, OrderItemSerializer, FavoriteSerializer
import logging
from django.core.cache import cache
from shop.cache_utils import (
    key_products_list, key_product_detail, key_stores_list,
    CACHE_TTL_PRODUCTS_LIST, CACHE_TTL_PRODUCT_DETAIL, CACHE_TTL_STORES_LIST,
    invalidate_product, invalidate_stores,
)

class IsAdminUserRole(permissions.BasePermission):
    """صلاحية تسمح فقط للمستخدمين الذين يحملون دور admin بالوصول"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
# Auth
auth_logger =logging.getLogger('service.auth')
# 1. Register
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save(role='customer')
        refresh = RefreshToken.for_user(user)
        auth_logger.info(f'Registeration successful | UserID: {user.id}|' \
        'Username:{user.username}')
        return Response({
            "Response Message": "Signed Up Successfully",
            "User": serializer.data,
            "Token": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    auth_logger.warning(f"Registeration validation failed|'\
                        Errors:{serializer.errors}")
    return Response({"Errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# 2. Login


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    phone_number = request.data.get('phone_number')
    password = request.data.get('password')
    user = authenticate(username=phone_number, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
        serializer = UserSerializer(user)
        auth_logger.info(f"User login successful| UserID: {user.id} | Phone: {phone_number}")
        return Response({
            "Response Message": f"{user.first_name} Signed In Successfully",
            "User": serializer.data,
            "Token": str(refresh.access_token)
        })
    auth_logger.warning(f"Failed login attempt | user with phone: {phone_number}")
    
    return Response({"Response Message": "Wrong Password Or Phone Number"}, status=status.HTTP_400_BAD_REQUEST)

# 3. Personal Information (Update Profile)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def personal_information(request):
    user = request.user
    data = request.data.copy()
    if 'role' in data:
        data.pop('role')
    serializer = UserSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        auth_logger.info(f"User profile details updated | UserID: {user.id} ")
        return Response({
            "Message": "Updated successfully",
            "User": serializer.data
        })
    auth_logger.warning(f" user profile details update failed | UserID: {user.id}|'\
                        Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 4. Profile Data (Me)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    auth_logger.info(f" Profile self-data fetched | UserID: {request.user.id}")
    serializer = UserSerializer(request.user)
    return Response({
        "Response Message": "Profile Data Received Successfully",
        "User": serializer.data
    })

# views.py


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def list_stores(request):
#     """Display a listing of the stores"""
#     stores = Store.objects.all()
#     serializer = StoreSerializer(
#         stores, many=True, context={'request': request})

#     return Response({
#         "message": "Stores retrieved successfully",
#         "stores": serializer.data
#     }, status=status.HTTP_200_OK)

shops_logger=logging.getLogger('service.shops')
# بعد الكاش
@api_view(['GET'])
@permission_classes([AllowAny])
def list_stores(request):
    #  try Redis cache first
    cache_key = key_stores_list()
    cached = cache.get(cache_key)
    if cached is not None:
        cached["cache"] = "HIT"
        shops_logger.info(f" Stores dataset listed |Cache: HIT")
        return Response(cached, status=status.HTTP_200_OK)
    # جيب من الداتابيز اذا ريديس فاضية
    stores = Store.objects.all()
    serializer = StoreSerializer(
        stores, many=True, context={'request': request})
    data = {
        "message": "Stores retrieved successfully",
        "stores": serializer.data,
        "cache": "MISS",   # remove this field if you don't want it visible
    }
    cache.set(cache_key, data, CACHE_TTL_STORES_LIST)
    shops_logger.info("Stores dataset listed | Cache: MISS ")
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def store_products(request):
    """ Get products for a specific store by name."""
    store_name = request.query_params.get('name')

    if not store_name:
        shops_logger.warning("store_products requested without providing store's parameter: name ")
        return Response({
            "message": "Store name is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    store = get_object_or_404(Store, name=store_name)
    serializer = StoreWithProductsSerializer(
        store, context={'request': request})
    shops_logger.info(f"Retrieved products for store | StorID: {store.id}| StoreName: {store.name}")
    return Response({
        "message": f"Store {store_name} products retrieved successfully",
        "products": serializer.data['products']
    },)


@api_view(['POST'])
@permission_classes([IsAdminUserRole])
def create_store(request):
    """Store a newly created store in storage."""
    required_fields = ['name', 'description', 'image', 'location']
    for field in required_fields:
        if field not in request.data:
            shops_logger.warning(f" Store creation failed | Missing required field: {field}")
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {field: [f"{field} is required"]}
            }, status=status.HTTP_400_BAD_REQUEST)

    if 'image' not in request.FILES:
        shops_logger.warning("Store creation failed| Image is required")
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"image": ["Image file is required"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    image_file = request.FILES['image']
    allowed_extensions = ['jpeg', 'jpg', 'png', 'gif', 'svg']
    file_extension = image_file.name.split('.')[-1].lower()

    if file_extension not in allowed_extensions:
        shops_logger.warning(f" Store creation failed| Image extension .{file_extension} is unacceptable")
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"image": ["Image must be jpeg, png, jpg, gif, or svg"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    location = request.data.get('location', '')
    shops_logger.warning(f"Store creation failed| Location regex validation mismatch: {location}")
    if not re.match(r'^[a-zA-Z0-9\s,.-]{1,100}$', location):
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"location": ["Location format is invalid"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    store_data = {
        'name': request.data['name'],
        'description': request.data['description'],
        'location': location
    }

    try:
        timestamp = int(time.time())
        original_filename = image_file.name
        filename = f"{timestamp}_{original_filename}"
        file_path = default_storage.save(
            f'stores/{filename}', ContentFile(image_file.read()))

        store = Store.objects.create(
            name=store_data['name'],
            description=store_data['description'],
            location=store_data['location'],
            image=file_path
        )
        shops_logger.info(f" Store added successfully| StorId: {store.id} | StoreName: {store.name}")
        return Response({
            "message": "Store added successfully",
            "Store": StoreSerializer(store, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        shops_logger.error(f"Exception throw during store creation transaction | Error: {str(e)}")
        return Response({
            "Response Message": "Error creating store",
            "Errors": {"error": [str(e)]}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def retrieve_store(request, id):
    """Display the specified store."""
    store = get_object_or_404(Store, id=id)
    serializer = StoreSerializer(store, context={'request': request})
    shops_logger.info(f" Individual store fetched | StoreID: {id} | Name: {store.name}")
    return Response({
        "Response Message": "Store retrieved successfully",
        "Store": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUserRole])
def update_store(request, id):
    """Update the specified store in storage."""
    store = get_object_or_404(Store, id=id)
    location = request.data.get('location')
    if location:
        if not re.match(r'^[a-zA-Z0-9\s,.-]{1,100}$', location):
            shops_logger.warning(f" Store layout modification failed | Location regex mismatch: '{location}'")
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"location": ["Location format is invalid"]}
            }, status=status.HTTP_400_BAD_REQUEST)

    if 'image' in request.FILES:
        image_file = request.FILES['image']
        allowed_extensions = ['jpeg', 'jpg', 'png', 'gif', 'svg']
        file_extension = image_file.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            shops_logger.warning(f"Store file update rejected | Unsupported image extension: .{file_extension}")
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"image": ["Image must be jpeg, png, jpg, gif, or svg"]}
            }, status=status.HTTP_400_BAD_REQUEST)

        if store.image:
            try:
                if os.path.isfile(store.image.path):
                    os.remove(store.image.path)
            except Exception as ex:
                shops_logger.warning(f"Unable to delete media media image at {store.image.path} | Error: {str(ex)}  ")

        timestamp = int(time.time())
        original_filename = image_file.name
        filename = f"{timestamp}_{original_filename}"
        file_path = default_storage.save(
            f'stores/{filename}', ContentFile(image_file.read()))
        store.image = file_path

    if 'name' in request.data:
        store.name = request.data['name']
    if 'description' in request.data:
        store.description = request.data['description']
    if 'location' in request.data:
        store.location = request.data['location']

    store.save()
    shops_logger.info(f" Store configuration parameters altered successfully | StoreID: {store.id}")
    return Response({
        "Response Message": "Store updated successfully",
        "Store": StoreSerializer(store, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAdminUserRole])
def delete_store(request, id):
    """Remove the specified store from storage."""
    store = get_object_or_404(Store, id=id)
    store.delete()
    shops_logger.info(f" Store removed successfully from database | StoreID: {id} | Name: {store.name}")
    return Response({
        "Message : ": "Deleted Successfully"
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_store(request):
    """Search for a store by name."""
    store_name = request.query_params.get('name')

    if not store_name:
        shops_logger.warning("Search Store hitted with Empty quety ")
        return Response({
            "Message : ": "Store name is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    store = Store.objects.filter(name=store_name).first()
    if not store:
        shops_logger.info(f"Store search executed with zero results returned | Query: {store_name}")
        return Response({
            "Message : ": "Store Not Found"
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = StoreSerializer(store, context={'request': request})
    shops_logger.info(f"Store search execution hit | Query: {store_name}")
    return Response({
        "Message : ": "Store Retrieved Successfully",
        "Store : ": serializer.data
    }, status=status.HTTP_200_OK)


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def list_products(request):
#     """Display a listing of the products,index() method."""
#     products = Product.objects.all()
#     serializer = ProductSerializer(
#         products, many=True, context={'request': request})

#     return Response({
#         "message": "Products retrieved successfully",
#         "products": serializer.data
#     }, status=status.HTTP_200_OK)

# بعد الكاش
@api_view(['GET'])
@permission_classes([AllowAny])
def list_products(request):
    # REQUIREMENT 6: try Redis cache first
    cache_key = key_products_list()
    cached = cache.get(cache_key)
    if cached is not None:
        cached["cache"] = "HIT"
        shops_logger.info("Products inventory catalog listed | Cache: HIT")
        return Response(cached, status=status.HTTP_200_OK)

    products = Product.objects.all()
    serializer = ProductSerializer(
        products, many=True, context={'request': request})
    data = {
        "message": "Products retrieved successfully",
        "products": serializer.data,
        "cache": "MISS",
    }
    cache.set(cache_key, data, CACHE_TTL_PRODUCTS_LIST)
    shops_logger.info("Products inventory catalog listed | Cache: MISS")
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([IsAdminUserRole])
def create_product(request):
    """Store a newly created product in storage, store() method."""
    required_fields = ['name', 'description', 'quantity',
                       'price', 'image', 'brand', 'store_name']
    for field in required_fields:
        if field not in request.data:
            shops_logger.warning(f" product createion aborted | Missing required input variable: {field}")
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {field: [f"{field} is required"]}
            }, status=status.HTTP_400_BAD_REQUEST)

    if 'image' not in request.FILES:
        shops_logger.warning(f"Product creation aborted | Image elements missing")
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"image": ["Image file is required"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    image_file = request.FILES['image']
    allowed_extensions = ['jpeg', 'jpg', 'png', 'gif', 'svg']
    file_extension = image_file.name.split('.')[-1].lower()

    if file_extension not in allowed_extensions:
        shops_logger.warning(f"Product creation aborted | Extension is unacceptable .{file_extension}")
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"image": ["Image must be jpeg, png, jpg, gif, or svg"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        quantity = int(request.data['quantity'])
        if quantity < 1:
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"quantity": ["Quantity must be at least 1"]}
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"quantity": ["Quantity must be an integer"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        price = float(request.data['price'])
        if price < 0:
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"price": ["Price must be at least 0"]}
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"price": ["Price must be a number"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    store_name = request.data.get('store_name')
    store = get_object_or_404(Store, name=store_name)

    try:
        timestamp = int(time.time())
        original_filename = image_file.name
        filename = f"{timestamp}_{original_filename}"
        file_path = default_storage.save(
            f'products/{filename}', ContentFile(image_file.read()))

        product = Product.objects.create(
            name=request.data['name'],
            description=request.data['description'],
            brand=request.data['brand'],
            quantity=quantity,
            price=price,
            image=file_path
        )

        store.products.add(product)
        shops_logger.info(f"Product mapped and saved | ProductID: {product.id}'\
                          ProductName: {product.name} | AssignedToStore : {store_name}")
        return Response({
            "Response Message": "Product added successfully",
            "Product": ProductSerializer(product, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        shops_logger.error(f"Error creating product | Error: {str(e)}")
        return Response({
            "Response Message": "Error creating product",
            "Errors": {"error": [str(e)]}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def retrieve_product(request, id):
#     """Display the specified product,show() method."""
#     product = get_object_or_404(Product, id=id)
#     serializer = ProductSerializer(product, context={'request': request})

#     return Response({
#         "Response Message": "Product retrieved successfully",
#         "Product": serializer.data
#     }, status=status.HTTP_200_OK)

# بعد الكاش
@api_view(['GET'])
@permission_classes([AllowAny])
def retrieve_product(request, id):
    # REQUIREMENT 6: try Redis cache first
    cache_key = key_product_detail(id)
    cached = cache.get(cache_key)
    if cached is not None:
        cached["cache"] = "HIT"
        shops_logger.info(f"Product layout record detailed | ProductID: {id} | Cache: HIT")
        return Response(cached, status=status.HTTP_200_OK)

    product = get_object_or_404(Product, id=id)
    serializer = ProductSerializer(product, context={'request': request})
    data = {
        "Response Message": "Product retrieved successfully",
        "Product": serializer.data,
        "cache": "MISS",
    }
    cache.set(cache_key, data, CACHE_TTL_PRODUCT_DETAIL)
    shops_logger.info(f"Product layout record detailed | ProductID: {id} | Cache: MISS")
    return Response(data, status=status.HTTP_200_OK)

# After handling the race conditions#######################


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUserRole])
def update_product(request, id):
    """Update the specified product in storage with retry logic for deadlocks."""
    product = get_object_or_404(Product, id=id)

    expected_version_raw = request.data.get('expected_version')
    if expected_version_raw is None:
        shops_logger.warning(f"Update Product failed | Missing version verification tracking token for ProductID: {id}")
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"expected_version": ["expected_version is required for optimistic locking"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        expected_version = int(expected_version_raw)
        if expected_version < 0:
            raise ValueError
    except (ValueError, TypeError):
        return Response({
            "Response Message": "Invalid Information",
            "Errors": {"expected_version": ["expected_version must be a non-negative integer"]}
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check quantity
    if 'quantity' in request.data:
        try:
            quantity = int(request.data['quantity'])
            if quantity < 1:
                return Response({
                    "Response Message": "Invalid Information",
                    "Errors": {"quantity": ["Quantity must be at least 1"]}
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"quantity": ["Quantity must be an integer"]}
            }, status=status.HTTP_400_BAD_REQUEST)

    # Check price
    if 'price' in request.data:
        try:
            price = float(request.data['price'])
            if price < 0:
                return Response({
                    "Response Message": "Invalid Information",
                    "Errors": {"price": ["Price must be at least 0"]}
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"price": ["Price must be a number"]}
            }, status=status.HTTP_400_BAD_REQUEST)

    updates = {}
    old_image_path = None

    if 'image' in request.FILES:
        image_file = request.FILES['image']
        allowed_extensions = ['jpeg', 'jpg', 'png', 'gif', 'svg']
        file_extension = image_file.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            return Response({
                "Response Message": "Invalid Information",
                "Errors": {"image": ["Image must be jpeg, png, jpg, gif, or svg"]}
            }, status=status.HTTP_400_BAD_REQUEST)

        if product.image:
            old_image_path = product.image.path

        timestamp = int(time.time())
        original_filename = image_file.name
        filename = f"{timestamp}_{original_filename}"
        # Save file once. If DB transaction fails/retries, we don't want to upload again.
        file_path = default_storage.save(
            f'products/{filename}', ContentFile(image_file.read()))
        updates['image'] = file_path

    # Populate other updates
    if 'name' in request.data:
        updates['name'] = request.data['name']
    if 'description' in request.data:
        updates['description'] = request.data['description']
    if 'brand' in request.data:
        updates['brand'] = request.data['brand']
    if 'quantity' in request.data:
        updates['quantity'] = int(request.data['quantity'])
    if 'price' in request.data:
        updates['price'] = float(request.data['price'])

    max_retries = 10
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Optimistic Locking: Update only if version matches
                updated_rows = Product.objects.filter(id=id, version=expected_version).update(
                    **updates,
                    version=F('version') + 1
                )

                if updated_rows == 0:
                    # This means the version changed (Optimistic Lock failure)
                    latest_product = Product.objects.filter(id=id).first()
                    if latest_product is None:
                        shops_logger.warning(f"Product update target missing on state validation | ProductID: {id}")
                        return Response({
                            "Response Message": "Product not found"
                        }, status=status.HTTP_404_NOT_FOUND)
                    shops_logger.warning(f"Optimistic Lock Version Mismatch Conflict | ProductID: {id} | Expected: {expected_version} | Database possesses newer version token.")
                    return Response({
                        "Response Message": "Product was modified by another request. Please refresh and retry.",
                        "Product": ProductSerializer(latest_product, context={'request': request}).data
                    }, status=status.HTTP_409_CONFLICT)

        except OperationalError as e:
            # Handle Database Deadlocks
            if '1213' in str(e) and attempt < max_retries - 1:
                shops_logger.warning(f"Database Deadlock event 1213 encountered during product mutation | ProductID: {id} | Attempt: {attempt + 1}/{max_retries}. Yielding thread briefly...")
                time.sleep(0.05 * (attempt + 1))
                continue
            shops_logger.error(f"Pessimistic transaction failure. Max retries exhausted on resource deadlock exception cycle | ProductID: {id} | Error: {str(e)}")
            return Response({
                "message": "System is busy, please try again."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        break

    if old_image_path:
        try:
            if os.path.isfile(old_image_path):
                os.remove(old_image_path)
        except Exception as ex:
            shops_logger.warning(f"Failed cleaning storage image file variant: {old_image_path} | Error: {str(ex)}")

    # Fetch the final updated product to return in response
    product = Product.objects.get(id=id)
    shops_logger.info(f"Product update transaction completed successfully | ProductID: {id} | New Version Token: {product.version}")
    return Response({
        "Response Message": "Product updated successfully",
        "Product": ProductSerializer(product, context={'request': request}).data
    }, status=status.HTTP_200_OK)


# Before handling the race condition

# @api_view(['PUT', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def update_product(request, id):
#     """Update the specified product in storage,update() method."""
#     product = get_object_or_404(Product, id=id)
#
#     if 'quantity' in request.data:
#         try:
#             quantity = int(request.data['quantity'])
#             if quantity < 1:
#                 return Response({
#                     "Response Message": "Invalid Information",
#                     "Errors": {"quantity": ["Quantity must be at least 1"]}
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except (ValueError, TypeError):
#             return Response({
#                 "Response Message": "Invalid Information",
#                 "Errors": {"quantity": ["Quantity must be an integer"]}
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#     if 'price' in request.data:
#         try:
#             price = float(request.data['price'])
#             if price < 0:
#                 return Response({
#                     "Response Message": "Invalid Information",
#                     "Errors": {"price": ["Price must be at least 0"]}
#                 }, status=status.HTTP_400_BAD_REQUEST)
#         except (ValueError, TypeError):
#             return Response({
#                 "Response Message": "Invalid Information",
#                 "Errors": {"price": ["Price must be a number"]}
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#     if 'image' in request.FILES:
#         image_file = request.FILES['image']
#         allowed_extensions = ['jpeg', 'jpg', 'png', 'gif', 'svg']
#         file_extension = image_file.name.split('.')[-1].lower()
#
#         if file_extension not in allowed_extensions:
#             return Response({
#                 "Response Message": "Invalid Information",
#                 "Errors": {"image": ["Image must be jpeg, png, jpg, gif, or svg"]}
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         if product.image:
#             try:
#                 if os.path.isfile(product.image.path):
#                     os.remove(product.image.path)
#             except:
#                 pass
#
#         timestamp = int(time.time())
#         original_filename = image_file.name
#         filename = f"{timestamp}_{original_filename}"
#         file_path = default_storage.save(f'products/{filename}', ContentFile(image_file.read()))
#         product.image = file_path
#
#     if 'name' in request.data:
#         product.name = request.data['name']
#     if 'description' in request.data:
#         product.description = request.data['description']
#     if 'brand' in request.data:
#         product.brand = request.data['brand']
#     if 'quantity' in request.data:
#         product.quantity = int(request.data['quantity'])
#     if 'price' in request.data:
#         product.price = float(request.data['price'])
#
#     product.save()
#
#     return Response({
#         "Response Message": "Product updated successfully",
#         "Product": ProductSerializer(product, context={'request': request}).data
#     }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_product(request):
    """Search for a product by name, search() method."""
    product_name = request.query_params.get('name')

    if not product_name:
        shops_logger.warning("Empty validation string evaluated inside search_product endpoint parameter parsing lookup")
        return Response({
            "Message : ": "Product name is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    product = Product.objects.filter(name=product_name).first()

    if not product:
        shops_logger.info(f"Product search completed returning empty record response | Query string evaluation: '{product_name}'")
        return Response({
            "Message : ": "Product Not Found"
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = ProductSerializer(product, context={'request': request})
    shops_logger.info(f"Product search successfully returned matching database record object reference | Query: '{product_name}' | ProductID: {product.id}")
    return Response({
        "Message : ": "Product Retrieved Successfully",
        "Product : ": serializer.data
    }, status=status.HTTP_200_OK)


# After handling the race conditions

@api_view(['DELETE'])
@permission_classes([IsAdminUserRole])
def delete_product(request, id):
    """Remove the specified product from storage, destroy() method with retry logic."""

    max_retries = 10
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # lock currently related rows
                cart_rows = Cart.objects.select_for_update().filter(product_id=id).order_by('pk')
                favorite_rows = Favorite.objects.select_for_update().filter(
                    product_id=id).order_by('pk')
                store_links = Product.stores.through.objects.select_for_update().filter(
                    product_id=id).order_by('pk')

                # lock the product row
                product = Product.objects.select_for_update().filter(id=id).first()
                if not product:
                    shops_logger.warning(f"Product deletion target dropped before lock instantiation | ProductID: {id}")
                    return Response({
                        "message": "Product not found"
                    }, status=status.HTTP_404_NOT_FOUND)

                image_path = None
                if product.image:
                    try:
                        image_path = product.image.path
                    except Exception:
                        image_path = None

                # re-scan related rows after product lock so rows created just before the lock are also cleaned
                cart_rows = Cart.objects.select_for_update().filter(product_id=id).order_by('pk')
                favorite_rows = Favorite.objects.select_for_update().filter(
                    product_id=id).order_by('pk')
                store_links = Product.stores.through.objects.select_for_update().filter(
                    product_id=id).order_by('pk')

                # block deletion if product is already tied to active orders
                active_order_item_exists = OrderItem.objects.filter(
                    product_id=id,
                    order__state__in=['pending',
                                      'processed', 'shipped', 'delivered']
                ).exists()
                if active_order_item_exists:
                    shops_logger.warning(f"Product deletion rejected due to relational foreign constraint integrity block | ProductID: {id} | Found active related orders.")
                    return Response({
                        "message": "Cannot delete product because it is referenced by active orders."
                    }, status=status.HTTP_409_CONFLICT)

                removed_from_carts = cart_rows.count()
                removed_from_favorites = favorite_rows.count()
                removed_from_stores = store_links.count()

                store_links.delete()
                cart_rows.delete()
                favorite_rows.delete()

                product_name = product.name
                product.delete()

        except OperationalError as e:
            # If it's a deadlock and we haven't exhausted retries, sleep and try again
            if '1213' in str(e) and attempt < max_retries - 1:
                shops_logger.warning(f"Database deadlock encounter 1213 tracking row release on product deletion transaction | ProductID: {id} | Attempt: {attempt + 1}/{max_retries}")
                time.sleep(0.05 * (attempt + 1))
                continue
            shops_logger.error(f"Resource deadlock transaction exception loops broken during critical deletion run phase | ProductID: {id} | Error: {str(e)}")
            return Response({
                "message": "System is busy, please try again."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        break

    if image_path:
        try:
            if os.path.isfile(image_path):
                os.remove(image_path)
        except Exception as ex:
            shops_logger.warning(f"Unclean removal tracking of static disk image on file deletion chain reference: {image_path} | Error: {str(ex)}")
    shops_logger.info(f"Product records scrubbed completely across all related dependencies | ProductID: {id} | Name: '{product_name}' | Cleaned Carts Count: {removed_from_carts} | Cleaned Favorites: {removed_from_favorites}")
    return Response({
        "Message : ": "Deleted Successfully",
        "Product": product_name,
        "removed_from_carts": removed_from_carts,
        "removed_from_favorites": removed_from_favorites,
        "removed_from_stores": removed_from_stores
    }, status=status.HTTP_200_OK)

# Before the race conditions handling

# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_product(request, id):
#     """Remove the specified product from storage, destroy() method."""
#     product = get_object_or_404(Product, id=id)
#     product.delete()
#
#     return Response({
#         "Message : ": "Deleted Successfully"
#     }, status=status.HTTP_200_OK)


# =========================
# Get All Cart Items
# =========================

cart_logger=logging.getLogger('service.cart')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_index(request):
    cart_logger.info(f"User reading shopping cart dataset matrix contents | UserID: {request.user.id}")

    carts = Cart.objects.filter(
        user=request.user
    ).select_related('product')

    serializer = CartSerializer(
        carts,
        many=True,
        context={'request': request}
    )

    return Response({
        "Cart": serializer.data,
        "Message": "Retrieved Successfully"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_store(request):
    name = request.data.get('name')
    quantity_to_add = int(request.data.get('quantity', 1))

    try:
        product = Product.objects.get(name=name)
    except Product.DoesNotExist:
        cart_logger.warning(f"Failed cart insertion pipeline | Target product entity matching name not found: '{name}' | UserID: {request.user.id}")
        return Response({'message': 'Product not found'}, status=404)

    cart_item = Cart.objects.filter(user=request.user, product=product).first()

    current_in_cart = cart_item.quantity if cart_item else 0
    total_requested_quantity = current_in_cart + quantity_to_add

    if total_requested_quantity > product.quantity:
        cart_logger.warning(
            f"Cart modification blocked: Insufficient inventory stock | UserID: {request.user.id} | "
            f"ProductID: {product.id} | Requested: {total_requested_quantity} | Available: {product.quantity}"
        )
        return Response({
            'message': f'Sorry, only {product.quantity} items available in stock. You already have {current_in_cart} in cart.',
            'available_stock': product.quantity
        }, status=status.HTTP_400_BAD_REQUEST)

    if cart_item:
        cart_item.quantity = total_requested_quantity
        cart_item.price += product.price * quantity_to_add
        cart_item.save()
        cart_logger.info(f"Cart line item updated | UserID: {request.user.id} | ProductID: {product.id} | Added: {quantity_to_add} | Total: {total_requested_quantity}")
    else:
        Cart.objects.create(
            user=request.user,
            product=product,
            quantity=quantity_to_add,
            price=product.price * quantity_to_add
        )
    cart_logger.info(f"New cart line item created | UserID: {request.user.id} | ProductID: {product.id} | Quantity: {quantity_to_add}")
    return Response({'message': 'Product added to cart successfully'})


# =========================
# Delete Cart Item
# =========================

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cart_destroy(request):

    product_id = request.data.get('product_id')

    cart = Cart.objects.filter(
        user=request.user,
        product_id=product_id
    ).first()

    if not cart:
        cart_logger.warning(f"Cart line item deletion failed | Product record entry missing inside database context | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "Cart item not found"
        }, status=404)

    cart.delete()
    cart_logger.info(f"Cart line item completely destroyed | UserID: {request.user.id} | ProductID: {product_id}")
    return Response({
        "message": "Cart item deleted successfully"
    })


################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def increase_cart(request):

    product_id = request.data.get('product_id')

    cart = Cart.objects.filter(
        user=request.user,
        product_id=product_id
    ).first()

    if not cart:
        cart_logger.warning(f"Failed to increment cart quantity | Record item not found | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "Cart item not found"
        }, status=404)

    # التحقق من الكمية المتوفرة
    if cart.quantity >= cart.product.quantity:
        cart_logger.warning(f"Cart quantity increment denied: Stock ceiling capacity reached | UserID: {request.user.id} | ProductID: {product_id} | Available Stock: {cart.product.quantity}")
        return Response({
            "message": f"Sorry, only {cart.product.quantity} items available",
            "available_quantity": cart.product.quantity
        }, status=status.HTTP_400_BAD_REQUEST)

    # زيادة الكمية
    cart.quantity += 1
    cart.price += cart.product.price
    cart.save()
    cart_logger.info(f"Cart line item volume incremented | UserID: {request.user.id} | ProductID: {product_id} | New Qty: {cart.quantity}")
    return Response({
        "message": "Quantity increased",
        "cart": CartSerializer(cart).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decrease_cart(request):

    product_id = request.data.get('product_id')

    cart = Cart.objects.filter(
        user=request.user,
        product_id=product_id
    ).first()

    if not cart:
        cart_logger.warning(f"Failed to decrement cart quantity | Record item not found | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "Cart item not found"
        }, status=404)

    if cart.quantity > 1:
        cart.quantity -= 1
        cart.price -= cart.product.price
        cart.save()
        cart_logger.info(f"Cart line item volume decremented | UserID: {request.user.id} | ProductID: {product_id} | New Qty: {cart.quantity}")
    else:
        cart.delete()
        cart_logger.info(f"Cart line item removed via decrement operation | UserID: {request.user.id} | ProductID: {product_id}")
    return Response({
        "message": "Quantity decreased"
    })

favorite_logger=logging.getLogger('service.favorite')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_product_favorite(request):
    product_id = request.data.get('product_id')
    if not product_id:
        favorite_logger.warning(f"Failed adding item to wishlist | Target product not found | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "product_id is required"
        }, status=400)
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({
            "message": "Product not found"
        }, status=404)
    favorite_exists = Favorite.objects.filter(
        user=request.user,
        product=product
    ).exists()
    if favorite_exists:
        favorite_logger.info(f"Ignored add_product_favorite request | Unique relational constraint mapping already exists | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "Already in favorites"
        }, status=400)
    Favorite.objects.create(
        user=request.user,
        product=product
    )
    favorite_logger.info(f"Product successfully pinned to user profile wishlist index | UserID: {request.user.id} | ProductID: {product_id}")
    return Response({
        "message": "Product added to favorites",
        "status": True
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_favorite(request):
    favorite_logger.info(f"User reading profile favorites records index list | UserID: {request.user.id}")
    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related('product')
    serializer = FavoriteSerializer(
        favorites,
        many=True,
        context={'request': request}
    )
    return Response({
        'data': serializer.data,
        'message': 'success message',
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product_favorite(request):
    product_id = request.data.get('product_id')
    favorite = Favorite.objects.filter(
        user=request.user,
        product_id=product_id
    ).first()
    if not favorite:
        favorite_logger.warning(f"Failed removing item from wishlist | Unique profile relationship map not found | UserID: {request.user.id} | ProductID: {product_id}")
        return Response({
            "message": "Favorite product not found",
            "status": False
        }, status=404)

    favorite.delete()
    favorite_logger.info(f"Product unpinned from user profile wishlist layout map index | UserID: {request.user.id} | ProductID: {product_id}")
    return Response({
        "message": "Favorite product deleted successfully",
        "status": True
    })

order_logger=logging.getLogger('service.order')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_orders(request):
    """Lis the user's orders. index1() method."""
    order_logger.info(f"User loading order history records layout map index | UserID: {request.user.id}")
    user = request.user
    orders = Order.objects.filter(user=user)
    serializer = OrderSerializer(
        orders, many=True, context={'request': request})

    return Response({
        "Message": "Orders Retrieved Successfully",
        "Order": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_details(request):
    """ Showing the order details with items and product images, details() method."""
    order_id = request.query_params.get('order_id')
    if not order_id:
        return Response({
            "Message : ": "Order ID is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()
    serializer = OrderItemSerializer(
        order_items, many=True, context={'request': request})
    order_logger.info(f"Order metadata components inspection loaded | UserID: {request.user.id} | OrderID: {order_id}")
    return Response({
        "Items": serializer.data,
        "Message : ": "Retrieved Successfully"
    }, status=status.HTTP_200_OK)


# BANA 2ND REQUIREMENT - used in original sequential approach
# def process_cart_item(cart_item, order):
#     product = cart_item.product
#     if cart_item.quantity > product.quantity:
#         raise ValueError(
#             f"Sorry, only {product.quantity} left for {product.name}")
#     product.quantity -= cart_item.quantity
#     product.save()
#     OrderItem.objects.create(
#         order=order,
#         product=product,
#         quantity=cart_item.quantity,
#         price=cart_item.price
#     )

# BANA 2ND REQUIREMENT - parallel OrderItem creation (stock already handled in transaction)
# SYNC POINT: each thread gets its own DB connection (thread-safe)
def create_order_item(cart_item, order, product_by_id):
    product = product_by_id[cart_item.product_id]
    line_total = float(product.price) * cart_item.quantity
    # SYNC POINT: Django ORM handles thread-safe DB writes per connection
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=cart_item.quantity,
        price=line_total
    )
    return line_total


# Before handing the race conditions and data integrity

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_order(request):
#     """Creating a new order from the user's cart. create() method."""
#     user = request.user
#     cart_items = Cart.objects.filter(user=user)
#     if not cart_items.exists():
#         return Response({
#             "message": "Cannot create an order with an empty cart."
#         }, status=status.HTTP_400_BAD_REQUEST)
#     total_cost = sum(item.price for item in cart_items)
#     order_data = {
#         'user': user,
#         'cost': total_cost,
#         'state': 'pending',
#         'pay_status': False,
#         'location': request.data.get('location', '')
#     }
#     order = Order.objects.create(**order_data)
#     for cart_item in cart_items:
#         product = cart_item.product
#         if cart_item.quantity > product.quantity:
#             return Response({
#                 "message": f"Sorry, only {product.quantity} left for {product.name}"
#             }, status=status.HTTP_400_BAD_REQUEST)
#         print(f"User {request.user.phone_number} passed validation")
#         time.sleep(3)
#         print(f"User {request.user.phone_number} updating quantity")
#         product.quantity -= cart_item.quantity
#         product.save()
#         OrderItem.objects.create(
#             order=order,
#             product=product,
#             quantity=cart_item.quantity,
#             price=cart_item.price
#     )
#
#     cart_items.delete()
#
#     return Response({
#         "Message": "Order Created Successfully",
#         "Order": OrderSerializer(order, context={'request': request}).data
#     }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """Creating a new order from the user's cart securely with race condition prevention."""
    user = request.user
    idempotency_key = request.headers.get(
        'Idempotency-Key') or request.data.get('idempotency_key')
    if not idempotency_key:
        order_logger.warning(f"Checkout transaction request rejected: Missing Idempotency Verification Token | UserID: {user.id}")
        return Response({
            "message": "Idempotency key is required (send Idempotency-Key header or idempotency_key field)."
        }, status=status.HTTP_400_BAD_REQUEST)

    # bana old
#     total_cost = sum(item.price for item in cart_items)
#     order_data = {
#         'user': user,
#         'cost': total_cost,
#         'state': 'pending',
#         'pay_status': request.data.get('pay_status', False),
#         'location': request.data.get('location', '')
#     }
#     order = Order.objects.create(**order_data)

#     # BANA COMMENTED THIS
#     # for cart_item in cart_items:

#     #     product = cart_item.product
#     #     if cart_item.quantity > product.quantity:
#     #         return Response({
#     #             "message": f"Sorry, only {product.quantity} left for {product.name}"
#     #         }, status=status.HTTP_400_BAD_REQUEST)
#     #     product.quantity -= cart_item.quantity
#     #     product.save()
#     #     OrderItem.objects.create(
#     #         order=order,
#     #         product=product,
#     #         quantity=cart_item.quantity,
#     #         price=cart_item.price
#     #     )

#     # BANA ADDED
#     pool = get_pool()
#     futures = {pool.submit(process_cart_item, item, order)
#                            : item for item in cart_items}

#     errors = []
#     for future in as_completed(futures):
#         try:
#             future.result()
#         except ValueError as e:
#             errors.append(str(e))

#     if errors:
#         order.delete()
#         return Response({"message": errors[0]}, status=status.HTTP_400_BAD_REQUEST)

#     # JUDY
#     # send_order_notification.delay(order.id, user.email)

#  # Simulate async operation
#     # cart_items.delete()
#     cart_items_qs.delete()

    # batool added
    # execute checkout as one atomic unit

    max_retries = 10
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # if this key already created an order for this user, return that order instead of duplicating.
                existing_order = Order.objects.select_for_update().filter(
                    user=user,
                    idempotency_key=idempotency_key
                ).first()
                if existing_order:
                    order_logger.info(f"Idempotency token cache layer match found | Order processing bypass executed | UserID: {user.id} | OrderID: {existing_order.id} | Key: {idempotency_key}")
                    return Response({
                        "Message": "Order already created for this idempotency key",
                        "Order": OrderSerializer(existing_order, context={'request': request}).data
                    }, status=status.HTTP_200_OK)

                # lock this user's cart
                cart_items = list(
                    Cart.objects.select_for_update().select_related(
                        'product').filter(user=user).order_by('id')
                )
                if not cart_items:
                    order_logger.warning(f"Checkout transaction request rejected: Shopping cart completely empty | UserID: {user.id}")
                    return Response({
                        "message": "Cannot create an order with an empty cart."
                    }, status=status.HTTP_400_BAD_REQUEST)

                # aggregate the requested quantity per product to validate and deduct stock
                requested_quantity_by_product = {}
                for cart_item in cart_items:
                    requested_quantity_by_product[cart_item.product_id] = (
                        requested_quantity_by_product.get(
                            cart_item.product_id, 0) + cart_item.quantity
                    )

                product_ids = sorted(requested_quantity_by_product.keys())
                products = list(Product.objects.select_for_update().filter(
                    id__in=product_ids).order_by('id'))
                product_by_id = {product.id: product for product in products}
                if len(product_by_id) != len(product_ids):
                    order_logger.error(f"Checkout transaction pipeline failed | Relational product mapping length inconsistency | UserID: {user.id}")
                    return Response({
                        "message": "One or more products are no longer available."
                    }, status=status.HTTP_404_NOT_FOUND)

                #  validate stock
                for product_id in product_ids:
                    product = product_by_id[product_id]
                    requested_quantity = requested_quantity_by_product[product_id]
                    if requested_quantity > product.quantity:
                        order_logger.warning(f"Checkout transactional bounds exceeded: Product layout stock drop | UserID: {user.id} | ProductID: {product_id} | Requested: {requested_quantity} | Available: {product.quantity}")
                        return Response({
                            "message": f"Sorry, only {product.quantity} left for {product.name}"
                        }, status=status.HTTP_409_CONFLICT)

                # create the order
                order = Order.objects.create(
                    user=user,
                    idempotency_key=idempotency_key,
                    cost=0,
                    state='pending',
                    pay_status=False,
                    location=request.data.get('location', '')
                )

                # deduct stock
                for product_id in product_ids:
                    requested_quantity = requested_quantity_by_product[product_id]
                    updated_rows = Product.objects.filter(
                        id=product_id,
                        quantity__gte=requested_quantity
                    ).update(quantity=F('quantity') - requested_quantity)
                    product.refresh_from_db()
                    print("NEW QUANTITY =", product.quantity)
                    if updated_rows == 0:
                        product = Product.objects.get(id=product_id)
                        order_logger.error(f"Concurrency lock update collision while modifying quantities | UserID: {user.id} | ProductID: {product_id}")
                        return Response({
                            "message": f"Sorry, only {product.quantity} left for {product.name}"
                        }, status=status.HTTP_409_CONFLICT)
                    product_by_id[product_id].refresh_from_db()

                Cart.objects.filter(
                    id__in=[item.id for item in cart_items]).delete()

                # build order items and recompute total cost from locked product prices
                # total_cost = 0.0
                # for cart_item in cart_items:
                #     product = product_by_id[cart_item.product_id]
                #     line_total = float(product.price) * cart_item.quantity
                #     total_cost += line_total
                #     OrderItem.objects.create(
                #         order=order,
                #         product=product,
                #         quantity=cart_item.quantity,
                #         price=line_total
                #     )

                # # persist final total and clear cart rows in the same transaction.
                # order.cost = total_cost
                # order.save(update_fields=['cost'])
                # Cart.objects.filter(id__in=[item.id for item in cart_items]).delete()
            break
        except OperationalError as e:
            if '1213' in str(e) and attempt < max_retries - 1:
                order_logger.warning(f"Resource contention deadlock 1213 identified inside checkout block framework | UserID: {user.id} | Attempt: {attempt + 1}/{max_retries}. Pausing execution...")
                time.sleep(0.05 * (attempt + 1))
                continue
            order_logger.error(f"Critical exception crash cycle inside order creation engine framework sequence logic | UserID: {user.id} | Error: {str(e)}")
            return Response({
                "message": "System is busy, please try again."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # BANA: ThreadPoolExecutor for parallel OrderItem creation (outside transaction)
    # SYNC POINT: submit all order items to fixed thread pool in parallel
    pool = get_pool()
    futures = {pool.submit(create_order_item, item, order,
                           product_by_id): item for item in cart_items}

    total_cost = 0.0
    errors = []
    # SYNC POINT: as_completed() collects results thread-safely
    for future in as_completed(futures):
        try:
            total_cost += future.result()
        except Exception as e:
            errors.append(str(e))

    if errors:
        order.delete()
        order_logger.error(f"ThreadPool runtime compilation exceptions encountered. Rolled back order entry | UserID: {user.id} | Exception Context: {errors[0]}")
        return Response({"message": errors[0]}, status=status.HTTP_400_BAD_REQUEST)

    order.cost = total_cost
    order.save(update_fields=['cost'])

    # JUDY
    # with asynchronous queue (here is Celery), we can send the notification without blocking the main thread
    send_order_notification.delay(order.id, user.email)
    # without celery, this will block the main thread
    # time.sleep(5)
    order_logger.info(f"Order created successfully | UserID: {user.id} | OrderID: {order.id} | Final Invoice Cost: {total_cost} | Background notification worker triggered")
    return Response({
        "Message": "Order Created Successfully",
        "Order": OrderSerializer(order, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUserRole])  # منع الزبائن من حذف المنتجات
def list_pending_orders(request):
    """listing of pending orders (alternative endpoint),show() method"""
    order_logger.info(f"Admin indexing system reading master pending orders queue layout maps | AdminUserID: {request.user.id}")
    orders = Order.objects.filter(state='pending')
    serializer = OrderSerializer(
        orders, many=True, context={'request': request})

    return Response(serializer.data, status=status.HTTP_200_OK)
####################


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUserRole])
def update_order_status(request):
    """Update order status,update() method."""
    
    order_logger.info(f"Admin executed general status tracking updates | AdminUserID: {request.user.id}")
    return Response({
        "Message : ": "The order is being delivered"
    }, status=status.HTTP_200_OK)


# Before handling the race conditions
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def cancel_order(request, order_id):
#     order = get_object_or_404(Order, id=order_id, user=request.user)
#     if order.state in ['shipped', 'delivered', 'canceled']:
#         return Response(
#             {"error": "Cannot cancel the order with this state"},
#             status=400
#         )
#
#     try:
#         try:
#             wallet = request.user.wallet
#         except:
#             return Response(
#                 {"error": "No wallet assigned to this account"},
#                 status=404
#             )
#
#         if order.pay_status:
#             refund_amount = Decimal(str(order.cost))
#             print(f"{request.user.phone_number} passed cancel validation")
#             print(f"{request.user.phone_number} refunding wallet")
#             wallet.balance += refund_amount
#             wallet.save()
#
#             WalletTransaction.objects.create(
#                 wallet=wallet,
#                 order=order,
#                 amount=refund_amount,
#                 transaction_type='refund',
#                 description=f"refund the order {order.id}"
#             )
#
#         order_items = order.items.all()
#         for item in order_items:
#             product = item.product
#             product.quantity += item.quantity
#             product.save()
#
#         order.state = 'canceled'
#         order.pay_status = False
#         order.save()
#
#         return Response({
#             "message": "The order has been canceled and the amount has been refunded to your wallet"
#         })
#
#     except Exception as e:
#         return Response({"error": f"error occurred: {str(e)}"}, status=500)


# after the race condition handling


# Ensure your standard imports (Response, status, F, Order, Product, Wallet, etc.) are present

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order with race condition prevention and retry logic."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Lock the order row
                order = Order.objects.select_for_update().filter(
                    id=order_id, user=request.user).first()
                if not order:
                    order_logger.warning(f"Order cancellation abort: Target resource record missing from user file index structures | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

                if order.state == 'canceled':
                    order_logger.info(f"Bypassed cancel operation: Order entry status flag already marks item as canceled | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"message": "Order already canceled"}, status=status.HTTP_200_OK)

                if order.state in ['shipped', 'delivered']:
                    order_logger.warning(f"Order cancellation denied: Shipping fulfillment pipeline has progressed too far | UserID: {request.user.id} | OrderID: {order_id} | Status: '{order.state}'")
                    return Response(
                        {"error": f"Cannot cancel order in state '{order.state}'"},
                        status=status.HTTP_409_CONFLICT
                    )

                # Lock the order items and related products
                order_items = list(
                    OrderItem.objects.select_for_update()
                    .select_related('product')
                    .filter(order=order)
                )
                if not order_items:
                    order_logger.warning(f"Order cancellation aborted: Zero bound transaction items found attached to entity structure context | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"error": "Order has no items to cancel"}, status=status.HTTP_400_BAD_REQUEST)

                restore_qty_by_product = {}
                for item in order_items:
                    restore_qty_by_product[item.product_id] = (
                        restore_qty_by_product.get(
                            item.product_id, 0) + item.quantity
                    )

                product_ids = sorted(restore_qty_by_product.keys())
                # Lock the involved product rows
                products = list(
                    Product.objects.select_for_update().filter(id__in=product_ids))

                if len(products) != len(product_ids):
                    order_logger.error(f"Order cancellation failed: Mapped internal product IDs mismatched or deleted | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"error": "One or more products no longer exist"}, status=status.HTTP_404_NOT_FOUND)

                product_by_id = {p.id: p for p in products}

                # Refund wallet only if the order was paid
                if order.pay_status:
                    print(
                        f"Processing refund for order #{order.id}, pay_status={order.pay_status}")
                    wallet = Wallet.objects.select_for_update().filter(user=request.user).first()
                    if not wallet:
                        order_logger.error(f"ledger processing error during refund execution loop: User wallet reference allocation missing | UserID: {request.user.id} | OrderID: {order_id}")
                        return Response({"error": "No wallet linked to this account"}, status=status.HTTP_404_NOT_FOUND)

                    existing_refund = WalletTransaction.objects.filter(
                        wallet=wallet,
                        order=order,
                        transaction_type='refund'
                    ).first()

                    if existing_refund:
                     order_logger.warning(f"Duplicate refund processing skipped: Ledger record matching key parameters exists | UserID: {request.user.id} | OrderID: {order_id} | RefundTransactionID: {existing_refund.id}")
                    else:
                        refund_amount = Decimal(str(order.cost))
                        print(
                            f"Refunding {refund_amount} to wallet for order #{order.id}")
                        wallet.balance += refund_amount
                        wallet.save(update_fields=['balance'])
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            order=order,
                            amount=refund_amount,
                            transaction_type='refund',
                            description=f"Refund for canceled order #{order.id}"
                        )
                        order_logger.info(f"Financial ledger credit adjustment posted inside active wallet index layout matrix balances | UserID: {request.user.id} | OrderID: {order_id} | Total Returned: {refund_amount}")
                else:
                        order_logger.info(f"Skipping financial refund routines: Target invoice flags mark order settlement balance as unpaid | OrderID: {order.id}")
                # Restore product quantities
                for product_id, qty in restore_qty_by_product.items():
                    Product.objects.filter(id=product_id).update(
                        quantity=F('quantity') + qty)
                # Update order state
                order.state = 'canceled'
                order.pay_status = False
                order.save(update_fields=['state', 'pay_status'])
        except OperationalError as e:
            if '1213' in str(e) and attempt < max_retries - 1:
                order_logger.warning(f"Deadlock 1213 tracking encountered on order cancellation execution thread | UserID: {request.user.id} | OrderID: {order_id} | Attempt: {attempt + 1}/{max_retries}")
                time.sleep(0.05 * (attempt + 1))
                continue
            order_logger.error(f"Critical error loop broken: Max processing retries broken during cancellation run phases | UserID: {request.user.id} | OrderID: {order_id} | Error: {str(e)}")
            return Response({
                "message": "System is busy, please try again."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        break
    order_logger.info(f"Order has been safely cancelled and stock profiles have successfully returned to catalog files | UserID: {request.user.id} | OrderID: {order_id}")
    return Response({"message": "Order canceled successfully"})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUserRole])  # منع الزبائن من حذف المنتجات
def update_order_shipped(request):
    """Update order state to 'shipped'"""
    order_id = request.data.get('order_id')
    if not order_id:
        
        return Response({
            "Message": "Order ID is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    order = get_object_or_404(Order, id=order_id)
    order.state = 'shipped'
    order.save()
    order_logger.info(f"Admin flagged order status index parameter tracking configuration as SHIPPED | AdminUserID: {request.user.id} | OrderID: {order_id}")
    return Response({
        "Message": "Orders Shipped Successfully",
        "Order": OrderSerializer(order, context={'request': request}).data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUserRole])  # منع الزبائن من حذف المنتجات
def update_order_delivered(request):
    """Update order state to 'delivered'"""
    order_id = request.data.get('order_id')
    if not order_id:
        return Response({
            "Message": "Order ID is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    order = get_object_or_404(Order, id=order_id)
    order.state = 'delivered'
    order.save()
    order_logger.info(f"Admin flagged order status index parameter tracking configuration as DELIVERED | AdminUserID: {request.user.id} | OrderID: {order_id}")
    return Response({
        "Message": "Orders Delivered Successfully",
        "Order": OrderSerializer(order, context={'request': request}).data
    }, status=status.HTTP_200_OK)


# Ensure other imports (Response, status, Wallet, WalletTransaction, etc.) are present

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_order_by_wallet(request, order_id):
    """Pay for an order using wallet balance with retry logic."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # 1. Lock the Order row first to ensure we have the latest state and prevent double payment
                order = Order.objects.select_for_update().filter(
                    id=order_id, user=request.user).first()
                if not order:
                    order_logger.warning(f"Wallet billing failed: Order entry missing from database context | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
                if order.pay_status:
                    order_logger.info(f"Wallet settlement routine safely bypassed: Invoicing marks entity as already processed | UserID: {request.user.id} | OrderID: {order_id}")
                    return Response({"error": "Already paid"}, status=status.HTTP_400_BAD_REQUEST)
                # 2. Lock the Wallet row
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                print(f"{request.user.phone_number} locked wallet")

                if wallet.balance < order.cost:
                    order_logger.warning(f"Wallet billing transaction rejected: Insufficient credit value margins | UserID: {request.user.id} | OrderID: {order_id} | InvoiceCost: {order.cost} | Balance: {wallet.balance}")
                    return Response({"error": "Balance not enough"}, status=status.HTTP_400_BAD_REQUEST)

                # 3. Deduct balance
                wallet.balance -= Decimal(str(order.cost))
                wallet.save()

                # 4. Update Order status
                order.pay_status = True
                order.state = 'processed'
                order.save()

                # 5. Record the transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    amount=order.cost,
                    transaction_type='withdraw',
                    description=f"Order with id {order.id} was paid successfully"
                )

        except OperationalError as e:
            # Handle Deadlocks (Error code 1213 is common for MySQL)
            if '1213' in str(e) and attempt < max_retries - 1:
                order_logger.warning(f"Database deadlock 1213 identified inside wallet settlement pipeline loop | UserID: {request.user.id} | OrderID: {order_id} | Attempt: {attempt + 1}/{max_retries}")
                time.sleep(0.05 * (attempt + 1))
                continue
            order_logger.error(f"Pessimistic concurrency exception loop broken: Max execution attempts broken | UserID: {request.user.id} | OrderID: {order_id} | Error: {str(e)}")
            return Response({
                "message": "System is busy, please try again."
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        break
    order_logger.info(f"Financial transaction payment settled securely through active wallet channels | UserID: {request.user.id} | OrderID: {order_id} | Debited Amount value: {order.cost}")
    return Response({"message": "Paid successfully"})
