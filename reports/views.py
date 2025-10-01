# reports/views.py - TO'LIQ CASH FLOW INTEGRATSIYASI

from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
from decimal import Decimal
from calendar import monthrange

from shops.models import Shop
from .models import ReportCalculator, ProfitCalculator


class ReportMixin:
    """Hisobot view'lari uchun mixin"""

    @staticmethod
    def get_user_shops(user):
        """Foydalanuvchiga tegishli do'konlarni olish"""
        shops = Shop.objects.all()
        if hasattr(user, 'userprofile') and user.userprofile.role != 'boss':
            shops = shops.filter(owner=user)
        return shops

    @staticmethod
    def get_selected_shop(shops, shop_id):
        """Tanlangan do'konni olish"""
        if shop_id:
            return get_object_or_404(shops, id=shop_id)
        return shops.first()

    @staticmethod
    def parse_date(date_string, default=None):
        """Sana stringini datetime.date formatiga aylantirish"""
        if not date_string:
            return default or timezone.now().date()
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return default or timezone.now().date()


@login_required
def daily_report(request):
    """Kunlik hisobot - CASH FLOW bilan"""
    from sales.models import PhoneSale, AccessorySale, PhoneExchange

    shops = ReportMixin.get_user_shops(request.user)
    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    selected_date = ReportMixin.parse_date(request.GET.get('date'))

    calculator = ReportCalculator(selected_shop)
    daily_data = calculator.get_daily_report(selected_date)

    # ✅ DEBUG - CASHFLOW
    print("=" * 80)
    print(f"📅 SANA: {selected_date}")
    print(f"💵 UZS KIRIM: {daily_data['cashflow']['uzs']['income']}")
    print(f"💸 UZS CHIQIM: {daily_data['cashflow']['uzs']['expense']}")
    print(f"📊 XARAJAT: {daily_data['cashflow']['details']['daily_expenses']}")
    print(f"💰 NET: {daily_data['cashflow']['uzs']['net']}")
    print("=" * 80)

    # Sotuvchilar statistikasi
    phone_sellers = PhoneSale.objects.filter(
        phone__shop=selected_shop,
        sale_date=selected_date
    ).values_list('salesman_id', flat=True).distinct()

    accessory_sellers = AccessorySale.objects.filter(
        accessory__shop=selected_shop,
        sale_date=selected_date
    ).values_list('salesman_id', flat=True).distinct()

    exchange_sellers = PhoneExchange.objects.filter(
        new_phone__shop=selected_shop,
        exchange_date=selected_date
    ).values_list('salesman_id', flat=True).distinct()

    seller_ids = set(phone_sellers) | set(accessory_sellers) | set(exchange_sellers)
    sellers = User.objects.filter(id__in=seller_ids)

    seller_stats = []
    profit_calc = ProfitCalculator()

    for seller in sellers:
        seller_data = calculator.get_seller_daily_report(seller, selected_date)

        # ✅ DEBUG - SELLER DATA
        print(f"\n👤 SELLER: {seller.username}")
        print(f"   seller_data: {seller_data}")  # Debug full seller_data structure

        # Check if 'sales' key exists, provide default if missing
        if 'sales' not in seller_data:
            seller_data['sales'] = {
                'phone_total_usd': 0,
                'accessory_total_uzs': 0,
                'total': 0
            }
        if 'counts' not in seller_data:
            seller_data['counts'] = {'total': 0}
        if 'sales_data' not in seller_data:
            seller_data['sales_data'] = {
                'phone_sales': [],
                'accessory_sales': [],
                'exchanges': []
            }

        print(f"   phone_total_usd: {seller_data['sales'].get('phone_total_usd', 'MAVJUD EMAS!')}")
        print(f"   accessory_total_uzs: {seller_data['sales'].get('accessory_total_uzs', 'MAVJUD EMAS!')}")
        print(f"   total: {seller_data['sales'].get('total', 'MAVJUD EMAS!')}")

        if seller_data['counts']['total'] > 0:
            for sale in seller_data['sales_data']['phone_sales']:
                sale.calculated_profit = profit_calc.calculate_phone_profit(sale)

            for exchange in seller_data['sales_data']['exchanges']:
                exchange.calculated_profit = profit_calc.calculate_exchange_profit(exchange)

            seller_stats.append(seller_data)

    # ✅ DEBUG - SELLER STATS COUNT
    print(f"\n📊 SELLER_STATS COUNT: {len(seller_stats)}")
    print("=" * 80)

    seller_stats.sort(key=lambda x: x['sales']['total'], reverse=True)

    return render(request, 'reports/daily_report.html', {
        'shops': shops,
        'selected_shop': selected_shop,
        'selected_date': selected_date,
        'daily_stats': daily_data,
        'seller_stats': seller_stats,
        'today': timezone.now().date(),
    })


@login_required
def monthly_report(request):
    """Oylik hisobot"""
    shops = ReportMixin.get_user_shops(request.user)
    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    try:
        calculator = ReportCalculator(selected_shop)
        monthly_data = calculator.get_monthly_report(year, month)
    except Exception as e:
        print(f"Oylik hisobot xatosi: {e}")
        monthly_data = {
            'year': year,
            'month': month,
            'totals': {
                'phone_sales_usd': Decimal('0'),
                'accessory_sales_uzs': Decimal('0'),
                'phone_cash_usd': Decimal('0'),
                'accessory_cash_uzs': Decimal('0'),
                'phone_card_usd': Decimal('0'),
                'accessory_card_uzs': Decimal('0'),
                'expenses': Decimal('0'),
                'net_cash': Decimal('0'),
                'sales': Decimal('0'),
                'cash': Decimal('0'),
                'card': Decimal('0')
            },
            'counts': {'phone': 0, 'accessory': 0, 'exchange': 0, 'total': 0},
            'daily_stats': [],
            'profits': {
                'phone_profit': Decimal('0'),
                'accessory_profit': Decimal('0'),
                'exchange_profit': Decimal('0'),
                'total_profit': Decimal('0')
            },
            'profit_margin': Decimal('0.00'),
            'averages': {
                'daily_phone_sales': Decimal('0'),
                'daily_accessory_sales': Decimal('0'),
                'daily_cash': Decimal('0')
            }
        }

    from sales.models import PhoneSale, AccessorySale, PhoneExchange

    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    phone_sellers = PhoneSale.objects.filter(
        phone__shop=selected_shop,
        sale_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    accessory_sellers = AccessorySale.objects.filter(
        accessory__shop=selected_shop,
        sale_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    exchange_sellers = PhoneExchange.objects.filter(
        new_phone__shop=selected_shop,
        exchange_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    seller_ids = set(phone_sellers) | set(accessory_sellers) | set(exchange_sellers)
    sellers = User.objects.filter(id__in=seller_ids)

    seller_monthly_stats = []
    for seller in sellers:
        salary_data = calculator.get_seller_monthly_salary(seller, year, month)
        if salary_data['sales']['phone_count'] > 0 or salary_data['sales']['accessory_count'] > 0:
            phone_sales_usd = salary_data['sales']['phone_total']
            accessory_sales_uzs = salary_data['sales']['accessory_total']

            seller_monthly_stats.append({
                'seller': seller,
                'phone_sales': phone_sales_usd,
                'accessory_sales': accessory_sales_uzs,
                'total_sales': phone_sales_usd + accessory_sales_uzs,
                'cash': salary_data['profits']['phone_profit'] + salary_data['profits']['accessory_profit'],
                'profit': salary_data['profits']['total_profit'],
                'transactions': salary_data['sales']['phone_count'] + salary_data['sales']['exchange_count'],
                'accessory_count': salary_data['sales']['accessory_count'],
                'exchange_count': salary_data['sales']['exchange_count'],
                'days': len(salary_data.get('daily_data', []))
            })

    seller_monthly_stats.sort(key=lambda x: x['phone_sales'], reverse=True)

    return render(request, 'reports/monthly_report.html', {
        'shops': shops,
        'selected_shop': selected_shop,
        'year': year,
        'month': month,
        'monthly_stats': monthly_data,
        'seller_monthly_stats': seller_monthly_stats,
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
        'years': range(2020, timezone.now().year + 2),
        'months': range(1, 13),
        'month_names': {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
        }
    })


@login_required
def yearly_report(request):
    """Yillik hisobot"""
    shops = ReportMixin.get_user_shops(request.user)
    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    year = int(request.GET.get('year', timezone.now().year))

    try:
        calculator = ReportCalculator(selected_shop)
        yearly_data = calculator.get_yearly_report(year)

        if not yearly_data:
            yearly_data = {}

        yearly_data.setdefault('year', year)
        yearly_data.setdefault('totals', {})
        yearly_data.setdefault('counts', {})
        yearly_data.setdefault('profits', {})
        yearly_data.setdefault('monthly_stats', [])

        totals = yearly_data['totals']
        totals.setdefault('phone_sales', Decimal('0'))
        totals.setdefault('accessory_sales', Decimal('0'))
        totals.setdefault('phone_cash', Decimal('0'))
        totals.setdefault('accessory_cash', Decimal('0'))
        totals.setdefault('expenses', Decimal('0'))
        totals.setdefault('net_cash', Decimal('0'))
        totals.setdefault('sales', Decimal('0'))
        totals.setdefault('cash', Decimal('0'))

        counts = yearly_data['counts']
        counts.setdefault('phone', 0)
        counts.setdefault('accessory', 0)
        counts.setdefault('exchange', 0)
        counts.setdefault('total', 0)

        profits = yearly_data['profits']
        profits.setdefault('phone_profit', Decimal('0'))
        profits.setdefault('accessory_profit', Decimal('0'))
        profits.setdefault('exchange_profit', Decimal('0'))
        profits.setdefault('total_profit', Decimal('0'))
        profits.setdefault('profit_margin', Decimal('0.00'))

        for monthly in yearly_data['monthly_stats']:
            monthly.setdefault('month', 1)
            monthly.setdefault('totals', {})
            monthly.setdefault('counts', {})
            monthly.setdefault('profits', {})
            monthly.setdefault('period', {})

            m_totals = monthly['totals']
            m_totals.setdefault('phone_sales_usd', Decimal('0'))
            m_totals.setdefault('accessory_sales_uzs', Decimal('0'))
            m_totals.setdefault('phone_cash_usd', Decimal('0'))
            m_totals.setdefault('accessory_cash_uzs', Decimal('0'))

            m_counts = monthly['counts']
            m_counts.setdefault('phone', 0)
            m_counts.setdefault('accessory', 0)
            m_counts.setdefault('exchange', 0)

            m_profits = monthly['profits']
            m_profits.setdefault('phone_profit', Decimal('0'))
            m_profits.setdefault('accessory_profit', Decimal('0'))
            m_profits.setdefault('exchange_profit', Decimal('0'))

            m_period = monthly['period']
            m_period.setdefault('working_days', 0)

    except Exception as e:
        print(f"Yillik hisobot xatosi: {e}")
        yearly_data = {
            'year': year,
            'totals': {
                'phone_sales': Decimal('0'),
                'accessory_sales': Decimal('0'),
                'phone_cash': Decimal('0'),
                'accessory_cash': Decimal('0'),
                'expenses': Decimal('0'),
                'net_cash': Decimal('0'),
                'sales': Decimal('0'),
                'cash': Decimal('0')
            },
            'counts': {'phone': 0, 'accessory': 0, 'exchange': 0, 'total': 0},
            'monthly_stats': [],
            'profits': {
                'phone_profit': Decimal('0'),
                'accessory_profit': Decimal('0'),
                'exchange_profit': Decimal('0'),
                'total_profit': Decimal('0'),
                'profit_margin': Decimal('0.00')
            }
        }

    from sales.models import PhoneSale, AccessorySale, PhoneExchange

    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    phone_sellers = PhoneSale.objects.filter(
        phone__shop=selected_shop,
        sale_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    accessory_sellers = AccessorySale.objects.filter(
        accessory__shop=selected_shop,
        sale_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    exchange_sellers = PhoneExchange.objects.filter(
        new_phone__shop=selected_shop,
        exchange_date__range=[start_date, end_date]
    ).values_list('salesman_id', flat=True).distinct()

    seller_ids = set(phone_sellers) | set(accessory_sellers) | set(exchange_sellers)
    sellers = User.objects.filter(id__in=seller_ids)

    yearly_sellers_stats = []
    profit_calc = ProfitCalculator()

    for seller in sellers:
        try:
            seller_phone_sales = PhoneSale.objects.filter(
                phone__shop=selected_shop,
                salesman=seller,
                sale_date__range=[start_date, end_date]
            )

            seller_accessory_sales = AccessorySale.objects.filter(
                accessory__shop=selected_shop,
                salesman=seller,
                sale_date__range=[start_date, end_date]
            )

            seller_exchanges = PhoneExchange.objects.filter(
                new_phone__shop=selected_shop,
                salesman=seller,
                exchange_date__range=[start_date, end_date]
            )

            phone_totals = seller_phone_sales.aggregate(
                total=Sum('sale_price'),
                count=Count('id')
            )

            accessory_totals = seller_accessory_sales.aggregate(
                total=Sum('total_price'),
                count=Count('id')
            )

            exchange_totals = seller_exchanges.aggregate(
                total=Sum('new_phone_price'),
                count=Count('id')
            )

            phone_profit = sum(
                profit_calc.calculate_phone_profit(sale)
                for sale in seller_phone_sales
            )

            accessory_profit = sum(
                sale.profit for sale in seller_accessory_sales
            )

            exchange_profit = sum(
                profit_calc.calculate_exchange_profit(exchange)
                for exchange in seller_exchanges
            )

            phone_dates = set(seller_phone_sales.values_list('sale_date', flat=True))
            accessory_dates = set(seller_accessory_sales.values_list('sale_date', flat=True))
            exchange_dates = set(seller_exchanges.values_list('exchange_date', flat=True))
            working_days = len(phone_dates | accessory_dates | exchange_dates)

            phone_sales_value = phone_totals.get('total') or Decimal('0')
            phone_count = phone_totals.get('count') or 0
            accessory_sales_value = accessory_totals.get('total') or Decimal('0')
            accessory_count = accessory_totals.get('count') or 0
            exchange_sales_value = exchange_totals.get('total') or Decimal('0')
            exchange_count = exchange_totals.get('count') or 0

            if phone_count > 0 or accessory_count > 0 or exchange_count > 0:
                yearly_sellers_stats.append({
                    'seller': seller,
                    'phone_sales': phone_sales_value,
                    'accessory_sales': accessory_sales_value,
                    'exchange_sales': exchange_sales_value,
                    'phone_count': phone_count,
                    'accessory_count': accessory_count,
                    'exchange_count': exchange_count,
                    'phone_profit': phone_profit,
                    'accessory_profit': accessory_profit,
                    'exchange_profit': exchange_profit,
                    'total_profit': phone_profit + accessory_profit + exchange_profit,
                    'working_days': working_days,
                    'total_sales': phone_sales_value + accessory_sales_value + exchange_sales_value,
                    'total_transactions': phone_count + accessory_count + exchange_count
                })

        except Exception as e:
            print(f"Sotuvchi {seller.username} uchun xatolik: {e}")
            continue

    yearly_sellers_stats.sort(
        key=lambda x: (x['phone_sales'], x['total_transactions']),
        reverse=True
    )

    return render(request, 'reports/yearly_report.html', {
        'shops': shops,
        'selected_shop': selected_shop,
        'year': year,
        'yearly_stats': yearly_data,
        'yearly_sellers_stats': yearly_sellers_stats,
        'current_year': timezone.now().year,
        'years': range(2020, timezone.now().year + 2),
        'month_names': {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
        }
    })


@login_required
def seller_detail_page(request, seller_id):
    """Sotuvchi KUNLIK tafsilot - QAYTARILGANLAR bilan"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    seller = get_object_or_404(User, id=seller_id)
    shops = ReportMixin.get_user_shops(request.user)

    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    selected_date = ReportMixin.parse_date(request.GET.get('date'))

    month = selected_date.month
    year = selected_date.year

    month_names = {
        1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
        5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
        9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
    }

    calculator = ReportCalculator(selected_shop)
    seller_stats = calculator.get_seller_daily_report(seller, selected_date)

    profit_calc = ProfitCalculator()

    # Telefon sotuvlari uchun foyda hisoblash
    for sale in seller_stats['sales_data']['phone_sales']:
        sale.calculated_profit = profit_calc.calculate_phone_profit(sale)

    # Almashtirishlar uchun foyda hisoblash
    for exchange in seller_stats['sales_data']['exchanges']:
        exchange.calculated_profit = profit_calc.calculate_exchange_profit(exchange)

    # ✅ QAYTARILGANLAR uchun foyda hisoblash
    for return_obj in seller_stats['sales_data']['phone_returns']:
        # Qaytarilgan telefonning yo'qotilgan foydasi
        return_obj.lost_profit = (
                return_obj.phone_sale.sale_price -
                return_obj.phone_sale.phone.cost_price
        )

    # Pagination
    phone_page = request.GET.get('phone_page', 1)
    phone_paginator = Paginator(seller_stats['sales_data']['phone_sales'], 10)
    try:
        phone_sales_page = phone_paginator.page(phone_page)
    except PageNotAnInteger:
        phone_sales_page = phone_paginator.page(1)
    except EmptyPage:
        phone_sales_page = phone_paginator.page(phone_paginator.num_pages)

    accessory_page = request.GET.get('accessory_page', 1)
    accessory_paginator = Paginator(seller_stats['sales_data']['accessory_sales'], 10)
    try:
        accessory_sales_page = accessory_paginator.page(accessory_page)
    except PageNotAnInteger:
        accessory_sales_page = accessory_paginator.page(1)
    except EmptyPage:
        accessory_sales_page = accessory_paginator.page(accessory_paginator.num_pages)

    exchange_page = request.GET.get('exchange_page', 1)
    exchange_paginator = Paginator(seller_stats['sales_data']['exchanges'], 10)
    try:
        exchanges_page = exchange_paginator.page(exchange_page)
    except PageNotAnInteger:
        exchanges_page = exchange_paginator.page(1)
    except EmptyPage:
        exchanges_page = exchange_paginator.page(exchange_paginator.num_pages)

    return render(request, 'reports/seller_detail.html', {
        'seller': seller,
        'shops': shops,
        'selected_shop': selected_shop,
        'selected_date': selected_date,
        'month': month,
        'year': year,
        'month_name': month_names.get(month),
        'seller_stats': seller_stats,
        'phone_sales_page': phone_sales_page,
        'accessory_sales_page': accessory_sales_page,
        'exchanges_page': exchanges_page,
        'today': timezone.now().date(),
    })


@login_required
def seller_detail_modal(request, seller_id):
    """Sotuvchi modal tafsiloti"""
    seller = get_object_or_404(User, id=seller_id)

    shop_id = request.GET.get('shop')
    selected_date = ReportMixin.parse_date(request.GET.get('date'))

    if not shop_id:
        return JsonResponse({'error': "Do'kon ID kerak"}, status=400)

    try:
        shop = Shop.objects.get(id=shop_id)
    except Shop.DoesNotExist:
        return JsonResponse({'error': "Do'kon topilmadi"}, status=404)

    calculator = ReportCalculator(shop)
    seller_stats = calculator.get_seller_daily_report(seller, selected_date)

    profit_calc = ProfitCalculator()
    for sale in seller_stats['sales_data']['phone_sales']:
        sale.calculated_profit = profit_calc.calculate_phone_profit(sale)
    for sale in seller_stats['sales_data']['accessory_sales']:
        sale.profit = profit_calc.calculate_accessory_profit(sale)
    for exchange in seller_stats['sales_data']['exchanges']:
        exchange.profit = profit_calc.calculate_exchange_profit(exchange)

    return render(request, 'reports/seller_detail_modal.html', {
        'seller': seller,
        'seller_stats': seller_stats,
        'selected_date': selected_date,
        'shop_id': shop_id,
    })


@login_required
def seller_salary_report(request, seller_id):
    """Sotuvchi OYLIK maoshi"""
    seller = get_object_or_404(User, id=seller_id)
    shops = ReportMixin.get_user_shops(request.user)

    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    calculator = ReportCalculator(selected_shop)
    salary_data = calculator.get_seller_monthly_salary(seller, year, month)

    profit_calc = ProfitCalculator()

    for day_data in salary_data.get('daily_data', []):
        for sale in day_data['sales_data']['phone_sales']:
            sale.calculated_profit = profit_calc.calculate_phone_profit(sale)

        for exchange in day_data['sales_data']['exchanges']:
            exchange.calculated_profit = profit_calc.calculate_exchange_profit(exchange)

    return render(request, 'reports/seller_salary.html', {
        'seller': seller,
        'shops': shops,
        'selected_shop': selected_shop,
        'year': year,
        'month': month,
        'salary_data': salary_data,
        'daily_data': salary_data.get('daily_data', []),
        'years': range(2020, timezone.now().year + 2),
        'months': range(1, 13),
        'month_names': {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
        }
    })


@login_required
def phone_sales_api(request):
    """Telefon sotuvlari API"""
    shop_id = request.GET.get('shop')
    date_str = request.GET.get('date')
    page = int(request.GET.get('page', 1))

    if not shop_id or not date_str:
        return JsonResponse({'error': "Do'kon va sana parametrlari kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shop = Shop.objects.get(id=shop_id)
    except (ValueError, Shop.DoesNotExist):
        return JsonResponse({'error': "Noto'g'ri parametrlar"}, status=400)

    from sales.models import PhoneSale
    phone_sales = PhoneSale.objects.filter(
        phone__shop=shop,
        sale_date=selected_date
    ).select_related('phone', 'customer', 'salesman').order_by('-id')

    paginator = Paginator(phone_sales, 20)
    page_obj = paginator.get_page(page)

    profit_calc = ProfitCalculator()
    results = []
    for sale in page_obj:
        results.append({
            'phone_model': f"{sale.phone.phone_model} {sale.phone.memory_size}",
            'customer_name': sale.customer.name,
            'salesman_name': sale.salesman.get_full_name() or sale.salesman.username,
            'sale_price_usd': float(sale.sale_price),
            'cash_amount_usd': float(sale.cash_amount),
            'card_amount_usd': float(sale.card_amount),
            'debt_amount_usd': float(sale.debt_amount),
            'credit_amount_usd': float(sale.credit_amount),
            'profit_usd': float(profit_calc.calculate_phone_profit(sale)),
            'sale_time': sale.created_at.strftime('%H:%M') if hasattr(sale, 'created_at') else sale.sale_date.strftime('%H:%M'),
            'currency': 'USD'
        })

    return JsonResponse({
        'results': results,
        'count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@login_required
def accessory_sales_api(request):
    """Aksessuar sotuvlari API"""
    shop_id = request.GET.get('shop')
    date_str = request.GET.get('date')
    page = int(request.GET.get('page', 1))

    if not shop_id or not date_str:
        return JsonResponse({'error': "Do'kon va sana parametrlari kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shop = Shop.objects.get(id=shop_id)
    except (ValueError, Shop.DoesNotExist):
        return JsonResponse({'error': "Noto'g'ri parametrlar"}, status=400)

    from sales.models import AccessorySale
    accessory_sales = AccessorySale.objects.filter(
        accessory__shop=shop,
        sale_date=selected_date
    ).select_related('accessory', 'customer', 'salesman').order_by('-id')

    paginator = Paginator(accessory_sales, 20)
    page_obj = paginator.get_page(page)

    profit_calc = ProfitCalculator()
    results = []
    for sale in page_obj:
        results.append({
            'accessory_name': sale.accessory.name,
            'quantity': sale.quantity,
            'customer_name': sale.customer.name,
            'salesman_name': sale.salesman.get_full_name() or sale.salesman.username,
            'total_price_uzs': int(sale.total_price),
            'unit_price_uzs': int(sale.unit_price),
            'cash_amount_uzs': int(sale.cash_amount),
            'card_amount_uzs': int(sale.card_amount),
            'debt_amount_uzs': int(sale.debt_amount),
            'profit_uzs': int(profit_calc.calculate_accessory_profit(sale)),
            'sale_time': sale.created_at.strftime('%H:%M') if hasattr(sale, 'created_at') else sale.sale_date.strftime('%H:%M'),
            'currency': 'UZS'
        })

    return JsonResponse({
        'results': results,
        'count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@login_required
def exchange_sales_api(request):
    """Almashtirish sotuvlari API"""
    shop_id = request.GET.get('shop')
    date_str = request.GET.get('date')
    page = int(request.GET.get('page', 1))

    if not shop_id or not date_str:
        return JsonResponse({'error': "Do'kon va sana parametrlari kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shop = Shop.objects.get(id=shop_id)
    except (ValueError, Shop.DoesNotExist):
        return JsonResponse({'error': "Noto'g'ri parametrlar"}, status=400)

    from sales.models import PhoneExchange
    exchanges = PhoneExchange.objects.filter(
        new_phone__shop=shop,
        exchange_date=selected_date
    ).select_related('old_phone', 'new_phone', 'customer', 'salesman').order_by('-id')

    paginator = Paginator(exchanges, 20)
    page_obj = paginator.get_page(page)

    profit_calc = ProfitCalculator()
    results = []
    for exchange in page_obj:
        results.append({
            'old_phone_model': f"{exchange.old_phone.phone_model} {exchange.old_phone.memory_size}",
            'new_phone_model': f"{exchange.new_phone.phone_model} {exchange.new_phone.memory_size}",
            'customer_name': exchange.customer.name,
            'salesman_name': exchange.salesman.get_full_name() or exchange.salesman.username,
            'new_phone_price_usd': float(exchange.new_phone_price),
            'old_phone_value_usd': float(exchange.old_phone_value),
            'additional_payment_usd': float(exchange.additional_payment),
            'profit_usd': float(profit_calc.calculate_exchange_profit(exchange)),
            'exchange_time': exchange.created_at.strftime('%H:%M') if hasattr(exchange, 'created_at') else exchange.exchange_date.strftime('%H:%M'),
            'currency': 'USD'
        })

    return JsonResponse({
        'results': results,
        'count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@login_required
def comparison_report(request):
    """Taqqoslash hisoboti"""
    shops = ReportMixin.get_user_shops(request.user)
    if not shops.exists():
        return render(request, 'reports/no_shop.html')

    selected_shop = ReportMixin.get_selected_shop(shops, request.GET.get('shop'))
    calculator = ReportCalculator(selected_shop)

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    today_stats = calculator.get_daily_report(today)
    yesterday_stats = calculator.get_daily_report(yesterday)

    def calc_change(current, previous):
        if previous == 0:
            return Decimal('0.00')
        return ((current - previous) / previous * 100).quantize(Decimal('0.01'))

    daily_comparison = {
        'today': today_stats,
        'yesterday': yesterday_stats,
        'phone_sales_change': calc_change(
            today_stats['sales']['phone_total_usd'],
            yesterday_stats['sales']['phone_total_usd']
        ),
        'accessory_sales_change': calc_change(
            today_stats['sales']['accessory_total_uzs'],
            yesterday_stats['sales']['accessory_total_uzs']
        ),
        'phone_cash_change': calc_change(
            today_stats['sales']['phone_cash_usd'],
            yesterday_stats['sales']['phone_cash_usd']
        ),
        'accessory_cash_change': calc_change(
            today_stats['sales']['accessory_cash_uzs'],
            yesterday_stats['sales']['accessory_cash_uzs']
        ),
        'profit_change': calc_change(
            today_stats['profits']['total_profit'],
            yesterday_stats['profits']['total_profit']
        )
    }

    current_month = today.month
    current_year = today.year

    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year

    current_monthly = calculator.get_monthly_report(current_year, current_month)
    previous_monthly = calculator.get_monthly_report(previous_year, previous_month)

    monthly_comparison = {
        'current': current_monthly,
        'previous': previous_monthly,
        'sales_change': calc_change(
            current_monthly['totals']['sales'],
            previous_monthly['totals']['sales']
        ),
        'profit_change': calc_change(
            current_monthly['profits']['total_profit'],
            previous_monthly['profits']['total_profit']
        )
    }

    return render(request, 'reports/comparison_report.html', {
        'shops': shops,
        'selected_shop': selected_shop,
        'daily_comparison': daily_comparison,
        'monthly_comparison': monthly_comparison
    })


@login_required
def yearly_profit_detail(request):
    """Yillik foyda tafsiloti API"""
    shop_id = request.GET.get('shop')
    year = int(request.GET.get('year', timezone.now().year))

    if not shop_id:
        return JsonResponse({'error': "Do'kon ID kerak"}, status=400)

    try:
        shop = Shop.objects.get(id=shop_id)
    except Shop.DoesNotExist:
        return JsonResponse({'error': "Do'kon topilmadi"}, status=404)

    calculator = ReportCalculator(shop)
    yearly_data = calculator.get_yearly_report(year)

    return JsonResponse({
        'success': True,
        'period': f"{year}",
        'profits': {
            'phone_profit': float(yearly_data.get('profits', {}).get('phone_profit', 0)),
            'accessory_profit': float(yearly_data.get('profits', {}).get('accessory_profit', 0)),
            'exchange_profit': float(yearly_data.get('profits', {}).get('exchange_profit', 0)),
            'total_profit': float(yearly_data.get('profits', {}).get('total_profit', 0))
        },
        'totals': {
            'phone_sales': float(yearly_data.get('totals', {}).get('phone_sales', 0)),
            'accessory_sales': float(yearly_data.get('totals', {}).get('accessory_sales', 0)),
            'exchange_sales': float(yearly_data.get('totals', {}).get('exchange_sales', 0)),
            'total_sales': float(yearly_data.get('totals', {}).get('sales', 0))
        },
        'counts': {
            'phone': yearly_data.get('counts', {}).get('phone', 0),
            'accessory': yearly_data.get('counts', {}).get('accessory', 0),
            'exchange': yearly_data.get('counts', {}).get('exchange', 0),
            'total': yearly_data.get('counts', {}).get('total', 0)
        },
        'profit_margin': float(yearly_data.get('profits', {}).get('profit_margin', 0))
    })


@login_required
def cashflow_api(request):
    """Cash Flow API - kunlik"""
    shop_id = request.GET.get('shop')
    date_str = request.GET.get('date')

    if not shop_id or not date_str:
        return JsonResponse({'error': "Parametrlar kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shop = Shop.objects.get(id=shop_id)
    except (ValueError, Shop.DoesNotExist):
        return JsonResponse({'error': "Noto'g'ri parametrlar"}, status=400)

    calculator = ReportCalculator(shop)
    daily_data = calculator.get_daily_report(selected_date)
    cashflow = daily_data.get('cashflow', {})

    return JsonResponse({
        'success': True,
        'date': str(selected_date),
        'cashflow': {
            'usd': {
                'income': float(cashflow.get('usd', {}).get('income', 0)),
                'expense': float(cashflow.get('usd', {}).get('expense', 0)),
                'net': float(cashflow.get('usd', {}).get('net', 0))
            },
            'uzs': {
                'income': float(cashflow.get('uzs', {}).get('income', 0)),
                'expense': float(cashflow.get('uzs', {}).get('expense', 0)),
                'net': float(cashflow.get('uzs', {}).get('net', 0))
            },
            'details': {
                'phone_sales': float(cashflow.get('details', {}).get('phone_sales', 0)),
                'accessory_sales': float(cashflow.get('details', {}).get('accessory_sales', 0)),
                'exchange_income': float(cashflow.get('details', {}).get('exchange_income', 0)),
                'exchange_equal': int(cashflow.get('details', {}).get('exchange_equal', 0)),
                'daily_seller_payments': float(cashflow.get('details', {}).get('daily_seller_payments', 0)),
                'exchange_expenses': float(cashflow.get('details', {}).get('exchange_expenses', 0)),
                'phone_returns': float(cashflow.get('details', {}).get('phone_returns', 0)),
                'daily_expenses': float(cashflow.get('details', {}).get('daily_expenses', 0)),
            }
        }
    })


@login_required
def cashflow_details_api(request):
    """Cash Flow tafsilotlari"""
    from .models import CashFlowTransaction

    shop_id = request.GET.get('shop')
    date_str = request.GET.get('date')

    if not shop_id or not date_str:
        return JsonResponse({'error': "Parametrlar kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shop = Shop.objects.get(id=shop_id)
    except (ValueError, Shop.DoesNotExist):
        return JsonResponse({'error': "Noto'g'ri parametrlar"}, status=400)

    transactions = CashFlowTransaction.objects.filter(
        shop=shop,
        transaction_date=selected_date
    ).order_by('-created_at')

    results = []
    for trans in transactions:
        results.append({
            'id': trans.id,
            'type': trans.get_transaction_type_display(),
            'amount_usd': float(trans.amount_usd),
            'amount_uzs': float(trans.amount_uzs),
            'description': trans.description,
            'notes': trans.notes,
            'created_at': trans.created_at.strftime('%H:%M:%S')
        })

    return JsonResponse({
        'success': True,
        'count': len(results),
        'transactions': results
    })

