# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from django.db.models import Count, Sum, Q
# from django.utils import timezone
# from datetime import datetime, timedelta
# from .models import Shop, Phone, Accessory, PhoneModel
# from .forms import PhoneForm
#
#
# @login_required
# def shop_list(request):
#     # Get all shops with related counts
#     shops = Shop.objects.annotate(
#         phone_count=Count('phones'),
#         accessory_count=Count('accessories'),
#     )
#
#     # Calculate additional stats for each shop
#     shops_data = []
#     for shop in shops:
#         total_products = shop.phone_count + shop.accessory_count
#         total_value = shop.phones.aggregate(
#             total=Sum('purchase_price')
#         )['total'] or 0
#
#         shops_data.append({
#             'id': shop.id,
#             'name': shop.name,
#             'phone_count': shop.phone_count,
#             'accessory_count': shop.accessory_count,
#             'total_products': total_products,
#             'total_value': total_value / 1000,  # Convert to K format
#             'created_at': shop.created_at,
#         })
#
#     # Overall statistics
#     total_shops = Shop.objects.count()
#     total_phones = Phone.objects.count()
#     total_accessories = Accessory.objects.count()
#     total_value = Phone.objects.aggregate(
#         total=Sum('purchase_price')
#     )['total'] or 0
#
#     # Today's additions
#     today = timezone.now().date()
#     phones_today = Phone.objects.filter(created_at__date=today).count()
#     accessories_today = Accessory.objects.filter(created_at__date=today).count()
#
#     # Phone model statistics - DINAMIK VERSIYA
#     all_phone_stats = PhoneModel.objects.annotate(
#         count=Count('phone')
#     ).order_by('-count')
#
#     # Eng ko'p sotilgan telefon modellarini olish (dinamik)
#     top_phone_models = []
#     for phone_model in all_phone_stats[:6]:  # Eng ko'p 6 ta modelni ko'rsatamiz
#         if phone_model.count > 0:  # Faqat mavjud telefonlarni ko'rsatish
#             percentage = (phone_model.count / total_phones * 100) if total_phones > 0 else 0
#             top_phone_models.append({
#                 'name': phone_model.model_name,
#                 'count': phone_model.count,
#                 'percentage': round(percentage, 1)
#             })
#
#     # Qolgan telefonlar uchun "Boshqalar" kategoriyasi
#     top_models_count = sum([model['count'] for model in top_phone_models])
#     other_count = total_phones - top_models_count
#     other_percentage = (other_count / total_phones * 100) if total_phones > 0 else 0
#
#     if other_count > 0:
#         top_phone_models.append({
#             'name': 'Boshqalar',
#             'count': other_count,
#             'percentage': round(other_percentage, 1)
#         })
#
#     # Available vs sold phones
#     available_phones = Phone.objects.filter(status=True).count()
#     sold_phones = Phone.objects.filter(status=False).count()
#
#     # Recent activities (this would come from a log table in real implementation)
#     recent_activities = []
#
#     # So'nggi qo'shilgan telefonlar
#     recent_phones = Phone.objects.select_related('phone_model', 'shop').order_by('-created_at')[:3]
#     for phone in recent_phones:
#         recent_activities.append({
#             'action': 'Yangi telefon qo\'shildi',
#             'description': f'{phone.phone_model.model_name} - IMEI: {phone.imei}',
#             'shop': phone.shop.name,
#             'created_at': phone.created_at
#         })
#
#     # So'nggi qo'shilgan aksessuarlar
#     recent_accessories = Accessory.objects.select_related('shop').order_by('-created_at')[:2]
#     for accessory in recent_accessories:
#         recent_activities.append({
#             'action': 'Yangi aksessuar qo\'shildi',
#             'description': f'{accessory.name} - {accessory.brand}',
#             'shop': accessory.shop.name,
#             'created_at': accessory.created_at
#         })
#
#     # Vaqt bo'yicha tartiblash
#     recent_activities.sort(key=lambda x: x['created_at'], reverse=True)
#     recent_activities = recent_activities[:5]  # Faqat so'nggi 5 ta
#
#     # Haftalik statistika
#     week_ago = timezone.now() - timedelta(days=7)
#     phones_this_week = Phone.objects.filter(created_at__gte=week_ago).count()
#     accessories_this_week = Accessory.objects.filter(created_at__gte=week_ago).count()
#
#     # Oylik statistika
#     month_ago = timezone.now() - timedelta(days=30)
#     phones_this_month = Phone.objects.filter(created_at__gte=month_ago).count()
#     accessories_this_month = Accessory.objects.filter(created_at__gte=month_ago).count()
#
#     # Eng faol do'kon
#     most_active_shop = None
#     if shops_data:
#         most_active_shop = max(shops_data, key=lambda x: x['total_products'])
#
#     # Holat bo'yicha statistika
#     condition_stats = {
#         'excellent': Phone.objects.filter(condition_percentage__gte=95).count(),
#         'good': Phone.objects.filter(condition_percentage__gte=80, condition_percentage__lt=95).count(),
#         'fair': Phone.objects.filter(condition_percentage__gte=60, condition_percentage__lt=80).count(),
#         'poor': Phone.objects.filter(condition_percentage__lt=60).count(),
#     }
#
#     context = {
#         'shops': shops_data,
#         'total_shops': total_shops,
#         'total_phones': total_phones,
#         'total_accessories': total_accessories,
#         'total_value': total_value / 1000,  # Convert to K format
#         'phones_today': phones_today,
#         'accessories_today': accessories_today,
#         'phones_this_week': phones_this_week,
#         'accessories_this_week': accessories_this_week,
#         'phones_this_month': phones_this_month,
#         'accessories_this_month': accessories_this_month,
#         'top_phone_models': top_phone_models,
#         'available_phones': available_phones,
#         'sold_phones': sold_phones,
#         'recent_activities': recent_activities,
#         'most_active_shop': most_active_shop,
#         'condition_stats': condition_stats,
#     }
#
#     return render(request, 'shop_list.html', context)
#
#
# @login_required
# def phone_list(request, shop_id):
#     shop = get_object_or_404(Shop, id=shop_id)
#     phones = Phone.objects.filter(shop=shop).select_related(
#         'phone_model', 'memory_size', 'source'
#     ).order_by('-created_at')
#
#     # Filter by search
#     search_query = request.GET.get('search', '')
#     if search_query:
#         phones = phones.filter(
#             Q(phone_model__model_name__icontains=search_query) |
#             Q(imei__icontains=search_query) |
#             Q(memory_size__size__icontains=search_query)
#         )
#
#     # Filter by status
#     status_filter = request.GET.get('status', '')
#     if status_filter == 'available':
#         phones = phones.filter(status=True)
#     elif status_filter == 'sold':
#         phones = phones.filter(status=False)
#
#     # Filter by model
#     model_filter = request.GET.get('model', '')
#     if model_filter:
#         phones = phones.filter(phone_model__id=model_filter)
#
#     # Filter by condition
#     condition_filter = request.GET.get('condition', '')
#     if condition_filter == 'excellent':
#         phones = phones.filter(condition_percentage__gte=95)
#     elif condition_filter == 'good':
#         phones = phones.filter(condition_percentage__gte=80, condition_percentage__lt=95)
#     elif condition_filter == 'fair':
#         phones = phones.filter(condition_percentage__gte=60, condition_percentage__lt=80)
#     elif condition_filter == 'poor':
#         phones = phones.filter(condition_percentage__lt=60)
#
#     # Get phone models for filter dropdown
#     phone_models = PhoneModel.objects.filter(
#         phone__shop=shop
#     ).distinct().order_by('model_name')
#
#     context = {
#         'shop': shop,
#         'phones': phones,
#         'phone_models': phone_models,
#         'total_phones': phones.count(),
#         'available_phones': phones.filter(status=True).count(),
#         'sold_phones': phones.filter(status=False).count(),
#         'total_value': phones.aggregate(total=Sum('purchase_price'))['total'] or 0,
#         'search_query': search_query,
#         'status_filter': status_filter,
#         'model_filter': model_filter,
#         'condition_filter': condition_filter,
#     }
#
#     return render(request, 'phone_list.html', context)
#
#
# @login_required
# def accessory_list(request, shop_id):
#     shop = get_object_or_404(Shop, id=shop_id)
#     accessories = Accessory.objects.filter(shop=shop).order_by('-created_at')
#
#     # Search functionality
#     search_query = request.GET.get('search', '')
#     if search_query:
#         accessories = accessories.filter(
#             Q(name__icontains=search_query) |
#             Q(brand__icontains=search_query)
#         )
#
#     context = {
#         'shop': shop,
#         'accessories': accessories,
#         'total_accessories': accessories.count(),
#         'search_query': search_query,
#     }
#
#     return render(request, 'accessory_list.html', context)
#
#
# @login_required
# def add_phone(request):
#     if request.method == 'POST':
#         form = PhoneForm(request.POST, request.FILES)
#         if form.is_valid():
#             phone = form.save(commit=False)
#             phone.created_by = request.user
#             phone.save()
#             return redirect('phone_list', shop_id=phone.shop.id)
#     else:
#         form = PhoneForm()
#
#     return render(request, 'add_phone.html', {'form': form})
#
#
# @login_required
# def edit_phone(request, phone_id):
#     phone = get_object_or_404(Phone, id=phone_id)
#     if request.method == 'POST':
#         form = PhoneForm(request.POST, request.FILES, instance=phone)
#         if form.is_valid():
#             form.save()
#             return redirect('phone_list', shop_id=phone.shop.id)
#     else:
#         form = PhoneForm(instance=phone)
#
#     return render(request, 'edit_phone.html', {'form': form, 'phone': phone})
#
#
# @login_required
# def delete_phone(request, phone_id):
#     phone = get_object_or_404(Phone, id=phone_id)
#     shop_id = phone.shop.id
#     phone.delete()
#     return redirect('phone_list', shop_id=shop_id)
#
#
# @login_required
# def toggle_phone_status(request, phone_id):
#     """Telefon holatini o'zgartirish (sotilgan/mavjud)"""
#     phone = get_object_or_404(Phone, id=phone_id)
#     phone.status = not phone.status
#     phone.save()
#     return redirect('phone_list', shop_id=phone.shop.id)