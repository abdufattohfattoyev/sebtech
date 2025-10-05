# reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Asosiy hisobotlar
    path('', views.daily_report, name='daily'),
    path('daily/', views.daily_report, name='daily_report'),
    path('monthly/', views.monthly_report, name='monthly'),
    path('yearly/', views.yearly_report, name='yearly'),

    # Taqqoslash
    path('comparison/', views.comparison_report, name='comparison'),

    # Sotuvchi hisobotlari
    path('seller/<int:seller_id>/', views.seller_detail_page, name='seller_detail_page'),
    path('seller/<int:seller_id>/modal/', views.seller_detail_modal, name='seller_detail_modal'),
    path('seller/<int:seller_id>/salary/', views.seller_salary_report, name='seller_salary'),

    # API endpoints
    path('api/phone-sales/', views.phone_sales_api, name='phone_sales_api'),
    path('api/accessory-sales/', views.accessory_sales_api, name='accessory_sales_api'),
    path('api/exchange-sales/', views.exchange_sales_api, name='exchange_sales_api'),
    path('api/yearly-profit/', views.yearly_profit_detail, name='yearly_profit_detail'),

    # YANGI: Cash Flow API
    path('api/cashflow/', views.cashflow_api, name='cashflow_api'),
    path('api/cashflow/details/', views.cashflow_details_api, name='cashflow_details_api'),
    path('api/phone-sales/', views.phone_sales_api, name='phone_sales_api'),
    path('api/accessory-sales/', views.accessory_sales_api, name='accessory_sales_api'),
    path('api/exchange-sales/', views.exchange_sales_api, name='exchange_sales_api'),
    path('api/yearly-profit/', views.yearly_profit_detail, name='yearly_profit_detail'),
]