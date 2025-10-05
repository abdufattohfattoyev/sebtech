from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, F, DecimalField, Q
from decimal import Decimal
from django_filters import rest_framework as filters

from .forms import PhoneForm, AccessoryForm, AccessoryAddQuantityForm, SupplierForm
from .models import Phone, Accessory, AccessoryPurchaseHistory, ExternalSeller, DailySeller, PhoneModel, Supplier
from shops.models import Shop


def can_edit_inventory(user):
    """Faqat boss va finance tahrirlash huquqiga ega"""
    if not hasattr(user, 'userprofile'):
        return False
    return user.userprofile.role in ['boss', 'finance']


def get_redirect_url(request):
    """URL yo'naltirish manzilini aniqlash"""
    if "phone" in request.path:
        return "inventory:phone_list"
    elif "supplier" in request.path:
        return 'inventory:supplier_list'
    else:
        return "inventory:accessory_list"


def boss_or_finance_required(view_func):
    """Faqat boss yoki finance ruxsat beruvchi dekorator"""
    def wrapper(request, *args, **kwargs):
        if not can_edit_inventory(request.user):
            messages.error(
                request,
                "Sizda bu amalni bajarish huquqi yo'q. "
                "Faqat rahbar va moliyachi tahrirlashi mumkin."
            )
            return redirect(get_redirect_url(request))
        return view_func(request, *args, **kwargs)
    return wrapper


class PhoneFilter(filters.FilterSet):
    imei = filters.CharFilter(field_name='imei', lookup_expr='exact')
    status = filters.ChoiceFilter(field_name='status', choices=Phone.STATUS_CHOICES)

    class Meta:
        model = Phone
        fields = ['imei', 'status']


class AccessoryFilter(filters.FilterSet):
    code = filters.CharFilter(field_name='code', lookup_expr='exact')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Accessory
        fields = ['code', 'name']

@login_required
def dashboard(request):
    """Dashboard - faqat do'kondagi, ustadagi va qaytarilgan telefonlar"""
    shops = Shop.objects.prefetch_related('phones', 'accessories')
    status_filter = request.GET.get('status', '')

    if not shops.exists():
        messages.error(request, "Hozircha tizimda do'kon mavjud emas.")
        return redirect('shop:dashboard')

    total_phone_value = Decimal('0.00')
    total_accessory_value = Decimal('0.00')
    total_phone_count = 0
    total_accessory_count = 0
    shop_stats = []

    for shop in shops:
        phones = shop.phones.filter(status__in=['shop', 'master', 'returned'])

        if status_filter:
            phones = phones.filter(status=status_filter)

        phone_count = phones.count()
        phone_cost_sum = phones.aggregate(
            total=Sum('cost_price', output_field=DecimalField(max_digits=15, decimal_places=2))
        )['total'] or Decimal('0.00')

        accessories = shop.accessories.all()
        accessory_count = accessories.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        accessory_cost_sum = accessories.aggregate(
            total=Sum(F('purchase_price') * F('quantity'), output_field=DecimalField(max_digits=15, decimal_places=2))
        )['total'] or Decimal('0.00')

        total_phone_count += phone_count
        total_accessory_count += accessory_count
        total_phone_value += phone_cost_sum
        total_accessory_value += accessory_cost_sum

        shop_stats.append({
            'shop': shop,
            'phone_count': phone_count,
            'accessory_count': accessory_count,
            'phone_cost_value': phone_cost_sum,
            'accessory_cost_value': accessory_cost_sum,
            'total_value': phone_cost_sum + accessory_cost_sum,
        })

    all_phones = Phone.objects.filter(shop__in=shops)
    phones_in_shop = all_phones.filter(status='shop').count()
    phones_sold = all_phones.filter(status='sold').count()
    phones_in_repair = all_phones.filter(status='master').count()
    phones_returned = all_phones.filter(status='returned').count()
    phones_exchanged = all_phones.filter(status='exchanged_in').count()

    context = {
        'shops': shops,
        'shop_stats': shop_stats,
        'total_phones': total_phone_count,
        'total_accessories': total_accessory_count,
        'total_phone_value': total_phone_value,
        'total_accessory_value': total_accessory_value,
        'total_shops': shops.count(),
        'status_filter': status_filter,
        'status_choices': Phone.STATUS_CHOICES,
        'phones_in_shop': phones_in_shop,
        'phones_sold': phones_sold,
        'phones_in_repair': phones_in_repair,
        'phones_returned': phones_returned,
        'phones_exchanged': phones_exchanged,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def phone_list(request):
    """Telefonlar ro'yxati"""
    imei_query = request.GET.get('imei', '').strip()
    model_query = request.GET.get('model', '').strip()
    status_filter = request.GET.get('status', '').strip()
    shop_id = request.GET.get('shop_id', '').strip()
    page_number = request.GET.get('page', 1)

    phones = Phone.objects.all().select_related('shop', 'phone_model', 'memory_size')

    if imei_query:
        phones = phones.filter(imei__icontains=imei_query)
    if model_query:
        phones = phones.filter(phone_model__id=model_query)
    if status_filter:
        phones = phones.filter(status=status_filter)
    if shop_id:
        phones = phones.filter(shop_id=shop_id)

    paginator = Paginator(phones, 12)
    page_obj = paginator.get_page(page_number)

    stats = {
        'total_phones': phones.count(),
        'displayed': len(page_obj),
        'phones_in_shop': phones.filter(status='shop').count(),
        'phones_sold': phones.filter(status='sold').count(),
    }

    phone_models = PhoneModel.objects.all().order_by('model_name')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        phones_data = [{
            'id': phone.id,
            'phone_model': str(phone.phone_model),
            'memory_size': str(phone.memory_size),
            'shop_name': phone.shop.name,
            'imei': phone.imei,
            'condition_percentage': phone.condition_percentage,
            'cost_price': float(phone.cost_price),
            'sale_price': float(phone.sale_price) if phone.sale_price else None,
            'status': phone.status,
            'status_display': phone.get_status_display(),
            'image': phone.image.url if phone.image else None,
        } for phone in page_obj]

        response = JsonResponse({
            'phones': phones_data,
            'stats': stats,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
        })
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    context = {
        'phones': page_obj,
        'phone_models': phone_models,
        'shops': Shop.objects.all(),
        'status_choices': Phone.STATUS_CHOICES,
        'imei_query': imei_query,
        'model_query': model_query,
        'status_filter': status_filter,
        'selected_shop': Shop.objects.filter(id=shop_id).first() if shop_id else None,
        'phones_in_shop': stats['phones_in_shop'],
        'phones_sold': stats['phones_sold'],
    }

    response = render(request, 'inventory/phone_list.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
@boss_or_finance_required
def phone_create(request):
    """Yangi telefon qo'shish"""
    if request.method == 'POST':
        form = PhoneForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                phone = form.save(commit=False)
                phone.created_by = request.user
                phone.save()
                messages.success(request, "Telefon muvaffaqiyatli qo'shildi!")
                return redirect('inventory:phone_list')
            except Exception as e:
                messages.error(request, f"Telefon saqlashda xatolik: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"Xatolik: {error}")
                    else:
                        field_label = form[field].label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = PhoneForm(user=request.user)

    return render(request, 'inventory/phone_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
@boss_or_finance_required
def phone_update(request, pk):
    """Telefonni tahrirlash"""
    phone = get_object_or_404(Phone, pk=pk)

    if request.method == 'POST':
        form = PhoneForm(request.POST, request.FILES, instance=phone, user=request.user)
        if form.is_valid():
            try:
                phone = form.save(commit=True)
                messages.success(request, "Telefon ma'lumotlari yangilandi!")
                return redirect('inventory:phone_list')
            except Exception as e:
                messages.error(request, f"Yangilashda xatolik: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"Xatolik: {error}")
                    else:
                        field_label = form[field].label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = PhoneForm(instance=phone, user=request.user)

    return render(request, 'inventory/phone_form.html', {
        'form': form,
        'phone': phone,
        'is_edit': True,
    })


@login_required
@boss_or_finance_required
def phone_delete(request, pk):
    """Telefonni o'chirish"""
    phone = get_object_or_404(Phone, pk=pk)

    if request.method == 'POST':
        try:
            phone.delete()
            messages.success(request, "Telefon muvaffaqiyatli o'chirildi!")
        except Exception as e:
            messages.error(request, f"O'chirishda xatolik: {str(e)}")
        return redirect('inventory:phone_list')

    return render(request, 'inventory/phone_confirm_delete.html', {'phone': phone})

@login_required
def accessory_list(request):
    """Aksessuarlar ro'yxati"""
    shops = Shop.objects.all()
    shop_id = request.GET.get('shop_id', '')
    code_query = request.GET.get('code', '').strip()
    name_query = request.GET.get('name', '').strip()
    stock_filter = request.GET.get('stock_level', '')

    accessories = Accessory.objects.select_related('supplier', 'created_by', 'shop')

    if shop_id:
        try:
            selected_shop = get_object_or_404(Shop, id=shop_id)
            accessories = accessories.filter(shop=selected_shop)
        except Shop.DoesNotExist:
            selected_shop = None
    else:
        selected_shop = None

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return accessory_search(request)

    if code_query:
        accessories = accessories.filter(code__icontains=code_query)
    if name_query:
        accessories = accessories.filter(name__icontains=name_query)

    stock_filters = {
        'low': Q(quantity__lt=5),
        'medium': Q(quantity__gte=5, quantity__lte=10),
        'high': Q(quantity__gt=10)
    }
    if stock_filter in stock_filters:
        accessories = accessories.filter(stock_filters[stock_filter])

    accessories = accessories.order_by('-created_at')

    total_accessory_cost = accessories.aggregate(
        total=Sum(F('purchase_price') * F('quantity'), output_field=DecimalField(max_digits=15, decimal_places=2))
    )['total'] or Decimal('0.00')

    for accessory in accessories:
        accessory.total_cost = accessory.purchase_price * accessory.quantity

    paginator = Paginator(accessories, 12)
    page_number = request.GET.get('page', 1)
    accessories_paginated = paginator.get_page(page_number)

    context = {
        'accessories': accessories_paginated,
        'shops': shops,
        'selected_shop': selected_shop,
        'code_query': code_query,
        'name_query': name_query,
        'stock_filter': stock_filter,
        'total_accessory_cost': total_accessory_cost,
    }
    return render(request, 'inventory/accessory_list.html', context)


@login_required
@boss_or_finance_required
def accessory_create(request):
    """Yangi aksessuar qo'shish"""
    if request.method == 'POST':
        form = AccessoryForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                accessory = form.save(commit=True)

                if hasattr(form, '_existing_accessory'):
                    quantity = form.cleaned_data.get('quantity', 0)
                    messages.success(request, f"✅ Mavjud aksessuar ustiga {quantity} dona qo'shildi!")
                else:
                    messages.success(request, f"✅ Yangi aksessuar '{accessory.name}' muvaffaqiyatli qo'shildi!")

                return redirect('inventory:accessory_list')

            except Exception as e:
                messages.error(request, f"❌ Aksessuar saqlashda xatolik: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_label = form.fields.get(field, field).label or field
                        messages.error(request, f"❌ {field_label}: {error}")
    else:
        form = AccessoryForm(user=request.user)

    return render(request, 'inventory/accessory_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
@boss_or_finance_required
def accessory_update(request, pk):
    """Aksessuarni tahrirlash"""
    accessory = get_object_or_404(Accessory, pk=pk)

    if request.method == 'POST':
        form = AccessoryForm(request.POST, request.FILES, instance=accessory, user=request.user)
        if form.is_valid():
            try:
                form.save(commit=True)
                messages.success(request, f"✅ '{accessory.name}' ma'lumotlari yangilandi!")
                return redirect('inventory:accessory_list')

            except Exception as e:
                messages.error(request, f"❌ Yangilashda xatolik: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_label = form.fields.get(field, field).label or field
                        messages.error(request, f"❌ {field_label}: {error}")
    else:
        form = AccessoryForm(instance=accessory, user=request.user)

    return render(request, 'inventory/accessory_form.html', {
        'form': form,
        'accessory': accessory,
        'is_edit': True,
    })


@login_required
@boss_or_finance_required
def accessory_delete(request, pk):
    """Aksessuarni o'chirish"""
    accessory = get_object_or_404(Accessory, pk=pk)

    if request.method == 'POST':
        try:
            name = accessory.name
            accessory.delete()
            messages.success(request, f"✅ '{name}' muvaffaqiyatli o'chirildi!")
        except Exception as e:
            messages.error(request, f"❌ O'chirishda xatolik: {str(e)}")
        return redirect('inventory:accessory_list')

    return render(request, 'inventory/accessory_confirm_delete.html', {'accessory': accessory})


@login_required
@boss_or_finance_required
def accessory_add_quantity(request, pk):
    """Mavjud aksessuar ustiga soni qo'shish"""
    accessory = get_object_or_404(Accessory, pk=pk)

    if request.method == 'POST':
        form = AccessoryAddQuantityForm(request.POST)
        if form.is_valid():
            try:
                quantity = form.cleaned_data['quantity']
                accessory = form.save(accessory=accessory, user=request.user, commit=True)
                messages.success(request, f"✅ '{accessory.name}' ga {quantity} dona qo'shildi!")
                return redirect('inventory:accessory_list')

            except Exception as e:
                messages.error(request, f"❌ Xatolik: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_label = form.fields.get(field, field).label or field
                        messages.error(request, f"❌ {field_label}: {error}")
    else:
        form = AccessoryAddQuantityForm()

    return render(request, 'inventory/accessory_add_quantity.html', {
        'accessory': accessory,
        'form': form
    })


@login_required
def accessory_quick_add(request):
    """Kod orqali tez qo'shish"""
    if request.method == 'POST':
        shop_id = request.POST.get('shop')
        code = request.POST.get('code', '').strip().zfill(4)
        quantity = request.POST.get('quantity', 0)
        purchase_price = request.POST.get('purchase_price')

        try:
            shop = Shop.objects.get(id=shop_id, owner=request.user)
            accessory = Accessory.objects.get(shop=shop, code=code)
            quantity = int(quantity)
            purchase_price = Decimal(purchase_price) if purchase_price else None

            if not purchase_price:
                return JsonResponse({'success': False, 'message': "Tannarx kiritilishi kerak!"})

            if quantity <= 0:
                return JsonResponse({'success': False, 'message': "Soni 0 dan katta bo'lishi kerak!"})

            AccessoryPurchaseHistory.objects.create(
                accessory=accessory,
                quantity=quantity,
                purchase_price=purchase_price,
                created_by=request.user
            )
            accessory.save()

            return JsonResponse({
                'success': True,
                'message': f"{accessory.name} ga {quantity} dona qo'shildi!",
                'new_quantity': accessory.quantity
            })

        except Shop.DoesNotExist:
            return JsonResponse({'success': False, 'message': "Do'kon topilmadi!"})
        except Accessory.DoesNotExist:
            return JsonResponse({'success': False, 'message': f"Kod {code} topilmadi!"})
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': "Noto'g'ri ma'lumot kiritildi!"})

    shops = Shop.objects.filter(owner=request.user)
    return render(request, 'inventory/accessory_quick_add.html', {'shops': shops})


@login_required
def accessory_detail(request, pk):
    """Aksessuar tafsilotlari"""
    accessory = get_object_or_404(Accessory, pk=pk, shop__owner=request.user)
    return render(request, 'inventory/accessory_detail.html', {'accessory': accessory})

@login_required
def shop_detail(request, shop_id):
    """Do'kon tafsilotlari"""
    shop = get_object_or_404(Shop, id=shop_id)

    phones = Phone.objects.filter(
        shop=shop,
        status__in=['shop', 'master', 'returned']
    ).select_related(
        'phone_model', 'memory_size', 'supplier', 'external_seller', 'created_by'
    ).order_by('-created_at')

    accessories = Accessory.objects.filter(shop=shop).select_related(
        'supplier', 'created_by'
    ).order_by('-created_at')

    phone_cost_value = phones.aggregate(
        total=Sum('cost_price', output_field=DecimalField(max_digits=15, decimal_places=2))
    )['total'] or Decimal('0.00')

    accessory_count = accessories.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
    accessory_cost_value = accessories.aggregate(
        total=Sum(F('purchase_price') * F('quantity'), output_field=DecimalField(max_digits=15, decimal_places=2))
    )['total'] or Decimal('0.00')

    context = {
        'shop': shop,
        'phones': phones,
        'accessories': accessories,
        'phone_count': phones.count(),
        'accessory_count': accessory_count,
        'phone_cost_value': phone_cost_value,
        'accessory_cost_value': accessory_cost_value,
        'total_value': phone_cost_value + accessory_cost_value,
    }
    return render(request, 'inventory/shop_detail.html', context)


@login_required
def accessory_search(request):
    """Aksessuarlar AJAX qidirish"""
    code_query = request.GET.get('code', '').strip()
    name_query = request.GET.get('name', '').strip()
    shop_id = request.GET.get('shop_id', '')
    stock_level = request.GET.get('stock_level', '')
    page = request.GET.get('page', 1)

    accessories = Accessory.objects.select_related('supplier', 'created_by', 'shop')

    if code_query:
        accessories = accessories.filter(code__icontains=code_query)
    if name_query:
        accessories = accessories.filter(name__icontains=name_query)
    if shop_id:
        try:
            accessories = accessories.filter(shop_id=int(shop_id))
        except (ValueError, TypeError):
            pass

    stock_filters = {
        'low': Q(quantity__lt=5),
        'medium': Q(quantity__gte=5, quantity__lte=10),
        'high': Q(quantity__gt=10)
    }
    if stock_level in stock_filters:
        accessories = accessories.filter(stock_filters[stock_level])

    accessories = accessories.order_by('-created_at')

    total_accessory_cost = accessories.aggregate(
        total=Sum(F('purchase_price') * F('quantity'), output_field=DecimalField(max_digits=15, decimal_places=2))
    )['total'] or Decimal('0.00')

    paginator = Paginator(accessories, 12)

    try:
        accessories_page = paginator.page(page)
    except Exception:
        accessories_page = paginator.page(1)

    results = {
        'accessories': [{
            'id': acc.id,
            'name': acc.name,
            'code': acc.code,
            'image': acc.image.url if acc.image else None,
            'purchase_price': float(acc.purchase_price),
            'sale_price': float(acc.sale_price),
            'quantity': acc.quantity,
            'total_cost': float(acc.purchase_price * acc.quantity),
            'shop_name': acc.shop.name,
            'supplier_name': acc.supplier.name if acc.supplier else None,
            'created_at': acc.created_at.strftime('%d.%m.%Y') if acc.created_at else '',
            'can_edit': request.user == acc.shop.owner,
        } for acc in accessories_page],
        'has_next': accessories_page.has_next(),
        'has_previous': accessories_page.has_previous(),
        'current_page': accessories_page.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'total_accessory_cost': float(total_accessory_cost),
    }

    return JsonResponse(results)


@login_required
def search(request):
    """Telefonlar AJAX qidirish"""
    imei_query = request.GET.get('imei', '').strip()
    status_filter = request.GET.get('status', '')
    shop_id = request.GET.get('shop_id', '')
    model_query = request.GET.get('model', '').strip()
    page = request.GET.get('page', 1)

    phones = Phone.objects.select_related('phone_model', 'memory_size', 'shop', 'created_by')

    if imei_query:
        phones = phones.filter(imei__icontains=imei_query)
    if status_filter:
        phones = phones.filter(status=status_filter)
    if shop_id:
        try:
            phones = phones.filter(shop_id=int(shop_id))
        except (ValueError, TypeError):
            pass
    if model_query:
        phones = phones.filter(phone_model__model_name__icontains=model_query)

    phones = phones.order_by('-created_at')
    paginator = Paginator(phones, 10)

    try:
        phones_page = paginator.page(page)
    except Exception:
        phones_page = paginator.page(1)

    results = {
        'phones': [{
            'id': phone.id,
            'phone_model': str(phone.phone_model),
            'memory_size': str(phone.memory_size),
            'imei': phone.imei or 'N/A',
            'status': phone.status,
            'status_display': phone.get_status_display(),
            'shop_name': phone.shop.name,
            'cost_price': float(phone.cost_price),
            'sale_price': float(phone.sale_price) if phone.sale_price else None,
            'condition_percentage': phone.condition_percentage,
            'created_at': phone.created_at.isoformat() if phone.created_at else '',
            'created_by': phone.created_by.username if phone.created_by else None,
            'image': phone.image.url if phone.image else None,
            'can_edit': request.user == phone.shop.owner,
        } for phone in phones_page],
        'has_next': phones_page.has_next(),
        'has_previous': phones_page.has_previous(),
        'current_page': phones_page.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
    }

    return JsonResponse(results)


@require_GET
@login_required
def phone_details_api(request, phone_id):
    """Telefon tafsilotlari API"""
    try:
        phone = get_object_or_404(Phone, id=phone_id, shop__owner=request.user)
        data = {
            'success': True,
            'phone': {
                'model': str(phone.phone_model),
                'memory': str(phone.memory_size),
                'imei': phone.imei or 'N/A',
                'condition': phone.condition_percentage,
                'cost_price': str(phone.cost_price),
                'repair_cost': str(phone.repair_cost),
            }
        }
        return JsonResponse(data)
    except Phone.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Telefon topilmadi'}, status=404)


@login_required
@boss_or_finance_required
def phone_detail(request, pk):
    """Telefon tafsilotlari"""
    phone = get_object_or_404(Phone, pk=pk)

    phone_sale = None
    phone_return = None
    phone_exchange_new = None
    phone_exchange_old = None
    customer_debts = []

    try:
        from sales.models import PhoneSale, PhoneReturn, PhoneExchange, Debt

        phone_sale = PhoneSale.objects.select_related('customer', 'salesman').filter(phone=phone).first()

        if phone_sale:
            phone_return = PhoneReturn.objects.select_related('created_by').filter(phone_sale=phone_sale).first()

            if phone_sale.debt_amount > 0:
                customer_debts = Debt.objects.filter(
                    customer=phone_sale.customer,
                    status='active'
                ).select_related('creditor')

        phone_exchange_new = PhoneExchange.objects.select_related(
            'old_phone_model', 'old_phone_memory', 'salesman', 'customer'
        ).filter(new_phone=phone).first()

        phone_exchange_old = PhoneExchange.objects.select_related(
            'new_phone', 'salesman', 'customer'
        ).filter(created_old_phone=phone).first()

    except ImportError:
        pass

    timeline = [{
        'date': phone.created_at,
        'event': 'Telefon qo\'shildi',
        'description': f'{phone.get_source_type_display()} orqali qo\'shildi',
        'user': phone.created_by,
        'type': 'created'
    }]

    if phone_sale:
        timeline.append({
            'date': phone_sale.sale_date,
            'event': 'Sotildi',
            'description': f'{phone_sale.customer.name} ga {phone_sale.sale_price}$ ga sotildi',
            'user': getattr(phone_sale, 'salesman', phone_sale.customer),
            'type': 'sold'
        })

    if phone_return:
        timeline.append({
            'date': getattr(phone_return, 'return_date', None),
            'event': 'Qaytarildi',
            'description': f'{phone_return.return_amount}$ qaytarildi',
            'user': phone_return.created_by,
            'type': 'returned'
        })

    timeline.sort(key=lambda x: x['date'] if x['date'] else phone.created_at)

    financial_summary = {
        'total_cost': phone.cost_price,
        'purchase_price': phone.purchase_price,
        'imei_cost': phone.imei_cost,
        'repair_cost': phone.repair_cost,
        'sale_price': getattr(phone_sale, 'sale_price', phone.sale_price) if phone_sale else phone.sale_price,
        'profit': Decimal('0.00'),
        'return_amount': getattr(phone_return, 'return_amount', Decimal('0.00')) if phone_return else Decimal('0.00'),
        'final_profit': Decimal('0.00')
    }

    if financial_summary['sale_price']:
        financial_summary['profit'] = financial_summary['sale_price'] - financial_summary['total_cost']
        financial_summary['final_profit'] = financial_summary['profit'] - financial_summary['return_amount']

    context = {
        'phone': phone,
        'phone_sale': phone_sale,
        'phone_return': phone_return,
        'phone_exchange_new': phone_exchange_new,
        'phone_exchange_old': phone_exchange_old,
        'customer_debts': customer_debts,
        'timeline': timeline,
        'financial_summary': financial_summary,
        'can_edit': request.user == phone.shop.owner,
    }

    return render(request, 'inventory/phone_detail.html', context)


@login_required
def search_external_seller_api(request):
    """Tashqi sotuvchilarni qidirish API"""
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse([], safe=False)

    sellers = ExternalSeller.objects.filter(
        Q(phone_number__icontains=query) | Q(name__icontains=query)
    ).order_by('name')[:10]

    data = [{
        "id": seller.id,
        "name": seller.name,
        "phone_number": seller.phone_number,
        "display_text": f"{seller.name} - {seller.phone_number}",
        "created_at": seller.created_at.strftime('%d.%m.%Y') if seller.created_at else ""
    } for seller in sellers]

    return JsonResponse(data, safe=False)


@login_required
def check_external_seller_phone_api(request):
    """Tashqi sotuvchi telefon raqami tekshirish API"""
    phone = request.GET.get("phone", "").strip()

    if len(phone) < 7:
        return JsonResponse({'exists': False, 'message': ''})

    try:
        seller = ExternalSeller.objects.get(phone_number=phone)
        return JsonResponse({
            'exists': True,
            'seller': {
                'id': seller.id,
                'name': seller.name,
                'phone_number': seller.phone_number,
                'created_at': seller.created_at.strftime('%d.%m.%Y') if seller.created_at else ''
            },
            'message': f'Bu telefon raqam allaqachon mavjud: {seller.name}'
        })
    except ExternalSeller.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'message': 'Telefon raqam mavjud emas. Yangi tashqi sotuvchi yaratiladi.'
        })


@login_required
def check_daily_seller_phone_api(request):
    """Kunlik sotuvchi telefon raqami tekshirish API"""
    phone = request.GET.get("phone", "").strip()

    if len(phone) < 7:
        return JsonResponse({'exists': False, 'message': ''})

    try:
        seller = DailySeller.objects.get(phone_number=phone)
        return JsonResponse({
            'exists': True,
            'seller': {
                'id': seller.id,
                'name': seller.name,
                'phone_number': seller.phone_number,
                'created_at': seller.created_at.strftime('%d.%m.%Y') if seller.created_at else ''
            },
            'message': f'Bu telefon raqam allaqachon mavjud: {seller.name}'
        })
    except DailySeller.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'message': 'Telefon raqam mavjud emas. Yangi kunlik sotuvchi yaratiladi.'
        })

@login_required
def supplier_list(request):
    """Taminotchilar ro'yxati"""
    suppliers = Supplier.objects.all().order_by('-created_at')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_suppliers': suppliers.count(),
    }

    return render(request, 'inventory/supplier_list.html', context)


@login_required
@boss_or_finance_required
def supplier_create(request):
    """Yangi taminotchi qo'shish"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"✅ {supplier.name} muvaffaqiyatli qo'shildi!")
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()

    context = {
        'form': form,
        'title': 'Yangi Taminotchi',
        'is_edit': False
    }
    return render(request, 'inventory/supplier_form.html', context)


@login_required
@boss_or_finance_required
def supplier_update(request, pk):
    """Taminotchini tahrirlash"""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"✅ {supplier.name} ma'lumotlari yangilandi!")
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)

    context = {
        'form': form,
        'supplier': supplier,
        'title': 'Taminotchini Tahrirlash',
        'is_edit': True
    }
    return render(request, 'inventory/supplier_form.html', context)


@login_required
@boss_or_finance_required
def supplier_delete(request, pk):
    """Taminotchini o'chirish"""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f"✅ {supplier_name} muvaffaqiyatli o'chirildi!")
        return redirect('inventory:supplier_list')

    context = {
        'supplier': supplier
    }
    return render(request, 'inventory/supplier_confirm_delete.html', context)