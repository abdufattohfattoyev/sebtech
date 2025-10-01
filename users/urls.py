from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('create/', views.user_create, name='user_create'),
    path('<int:pk>/', views.user_detail, name='user_detail'),
    path('<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('logout/', views.logout_view, name='logout'),
]