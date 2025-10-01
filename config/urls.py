# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_users(request):
    """Asosiy sahifadan users dashboardga yo'naltirish"""
    return redirect('users:dashboard')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Django auth URLs
    path('users/', include('users.urls')),  # Users app
    path('', redirect_to_users, name='home'),  # Root URL -> users dashboard
    path('shops/', include('shops.urls')),  # Shops app
    path('inventory/', include('inventory.urls')),  # Inventory app
    path('services/', include('services.urls')),  #services app
    path('sales/', include('sales.urls')),
    path('reports/', include('reports.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)