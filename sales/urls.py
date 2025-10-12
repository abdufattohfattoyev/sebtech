# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.sales_dashboard, name='dashboard'),

    # API endpoints
    path('api/search-customer/', views.search_customer_api, name='search_customer_api'),
    path('api/search-phone-by-imei/', views.search_phone_by_imei_api, name='search_phone_by_imei_api'),
    path("api/search-phone-sale-by-imei/", views.search_phone_sale_by_imei_api, name="search_phone_sale_by_imei_api"),
    path('api/search-accessory-by-code/', views.search_accessory_by_code_api, name='search_accessory_by_code_api'),
    path('api/get-phone-sale/<int:pk>/', views.get_phone_sale_api, name='get_phone_sale_api'),

    # Phone Sales
    path('phone-sales/', views.phone_sale_list, name='phone_sale_list'),
    path('phone-sales/create/', views.phone_sale_create, name='phone_sale_create'),
    path('phone-sales/<int:pk>/', views.phone_sale_detail, name='phone_sale_detail'),
    path('phone-sales/<int:pk>/edit/', views.phone_sale_edit, name='phone_sale_edit'),
    path('phone-sales/<int:pk>/delete/', views.phone_sale_delete, name='phone_sale_delete'),

    # Phone Returns
    path('phone-returns/', views.phone_return_list, name='phone_return_list'),
    path('phone-returns/create/', views.phone_return_create, name='phone_return_create'),
    path('phone-returns/<int:pk>/', views.phone_return_detail, name='phone_return_detail'),
    path('phone-returns/<int:pk>/delete/', views.phone_return_delete, name='phone_return_delete'),
    path('phone-return/<int:pk>/edit/', views.phone_return_edit, name='phone_return_edit'),

    # Accessory Sales
    path('accessory-sales/', views.accessory_sale_list, name='accessory_sale_list'),
    path('accessory-sales/create/', views.accessory_sale_create, name='accessory_sale_create'),
    path('accessory-sales/<int:pk>/', views.accessory_sale_detail, name='accessory_sale_detail'),
    path('accessory-sales/<int:pk>/edit/', views.accessory_sale_edit, name='accessory_sale_edit'),
    path('accessory-sales/<int:pk>/delete/', views.accessory_sale_delete, name='accessory_sale_delete'),

    # Phone Exchange
    path('phone-exchange/', views.phone_exchange_list, name='phone_exchange_list'),
    path('phone-exchange/create/', views.phone_exchange_create, name='phone_exchange_create'),
    path('phone-exchange/<int:pk>/', views.phone_exchange_detail, name='phone_exchange_detail'),
    path('phone-exchange/<int:pk>/edit/', views.phone_exchange_edit, name='phone_exchange_edit'),
    path('phone-exchange/<int:pk>/delete/', views.phone_exchange_delete, name='phone_exchange_delete'),

    # Debts - TO'LDIRILGAN
    path('debts/', views.debt_list, name='debt_list'),
    path('debts/create/', views.debt_create, name='debt_create'),
    path('debts/<int:pk>/', views.debt_detail, name='debt_detail'),
    path('debts/<int:pk>/edit/', views.debt_edit, name='debt_edit'),
    path('debts/<int:pk>/delete/', views.debt_delete, name='debt_delete'),  # BU YO'Q EDI!
    path('debts/export/', views.debt_export_excel, name='debt_export_excel'),

    # Debt Payments
    path('debt-payments/', views.debt_payment_list, name='debt_payment_list'),
    path('debt-payments/create/<int:debt_id>/', views.debt_payment_create, name='debt_payment_create'),
    path('debt-payments/<int:pk>/', views.debt_payment_detail, name='debt_payment_detail'),
    path('debt-payments/<int:pk>/edit/', views.debt_payment_edit, name='debt_payment_edit'),
    path('debt-payments/<int:pk>/delete/', views.debt_payment_delete, name='debt_payment_delete'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
]