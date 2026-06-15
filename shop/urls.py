from django.urls import path
from . import views
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('me/', views.me, name='me'),
    path('personal-info/', views.personal_information, name='personal_info'),
    path('cart/', views.cart_index),
    path('cart/store/', views.cart_store),
    path('cart/delete/', views.cart_destroy),
    path('cart/increase/', views.increase_cart),
    path('cart/decrease/', views.decrease_cart),
    path('favorite/', views.get_product_favorite, name='favorite.list'),
    path('favorite/add/', views.add_product_favorite, name='favorite.add'),
    path('favorite/delete/', views.delete_product_favorite, name='favorite.delete'),


    # Endpoints for Store
    path('stores/', views.list_stores, name='list_stores'),
    path('stores/create/', views.create_store, name='create_store'),
    path('stores/<int:id>/', views.retrieve_store, name='retrieve_store'),
    path('stores/<int:id>/update/', views.update_store, name='update_store'),
    path('stores/<int:id>/delete/', views.delete_store, name='delete_store'),
    path('stores/products/', views.store_products, name='store_products'),
    path('stores/search/', views.search_store, name='search_store'),

    # Product endpoints
    path('products/', views.list_products, name='list_products'),
    path('products/create/', views.create_product, name='create_product'),
    path('products/<int:id>/', views.retrieve_product, name='retrieve_product'),
    path('products/<int:id>/update/', views.update_product, name='update_product'),
    path('products/<int:id>/delete/', views.delete_product, name='delete_product'),
    path('products/search/', views.search_product, name='search_product'),

    # Order endpoints
    path('orders/user/', views.list_user_orders, name='list_user_orders'),
    path('orders/details/', views.order_details, name='order_details'),
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/pending/list/', views.list_pending_orders, name='list_pending_orders'),
    path('orders/update/', views.update_order_status, name='update_order_status'),####
    path('orders/shipped/', views.update_order_shipped, name='update_order_shipped'),
    path('orders/delivered/', views.update_order_delivered, name='update_order_delivered'),
    path('orders/<int:order_id>/pay/', views.pay_order_by_wallet, name='pay_order'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
]
