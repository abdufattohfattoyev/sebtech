from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone_number", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')