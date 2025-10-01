# inventory/urls.py - qo'shimcha URL lar
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Phone URLs
    path('phones/', views.phone_list, name='phone_list'),
    path('phones/create/', views.phone_create, name='phone_create'),
    path('phones/<int:pk>/edit/', views.phone_update, name='phone_update'),
    path('phones/<int:pk>/delete/', views.phone_delete, name='phone_delete'),
    path('phones/<int:pk>/', views.phone_detail, name='phone_detail'),

    # Accessory URLs
    path('accessories/', views.accessory_list, name='accessory_list'),
    path('accessories/create/', views.accessory_create, name='accessory_create'),
    path('accessories/<int:pk>/edit/', views.accessory_update, name='accessory_update'),
    path('accessories/<int:pk>/delete/', views.accessory_delete, name='accessory_delete'),
    path('accessories/search/', views.accessory_search, name='accessory_search'),

    # Yangi qo'shilgan URL lar
    path('accessories/<int:pk>/add-quantity/', views.accessory_add_quantity, name='accessory_add_quantity'),
    path('accessories/quick-add/', views.accessory_quick_add, name='accessory_quick_add'),
    path('accessories/<int:pk>/', views.accessory_detail, name='accessory_detail'),

    # Shop detail
    path('shop/<int:shop_id>/', views.shop_detail, name='shop_detail'),

    # API URLs
    path('search/', views.search, name='search'),
    path('search-seller/', views.search_external_seller_api, name='search_seller_api'),
    path('check-seller-phone/', views.check_external_seller_phone_api, name='check_seller_phone_api'),
    path('phone/<int:phone_id>/details/', views.phone_details_api, name='phone_details_api'),
    path('check-daily-seller-phone/', views.check_daily_seller_phone_api, name='check_daily_seller_phone_api'),
]