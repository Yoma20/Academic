from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import path
from django.template.response import TemplateResponse
from django.utils import timezone
from datetime import timedelta
from .models import AcademicCategory, Gig, GigPackage, GigExtra, Order


@admin.register(AcademicCategory)
class AcademicCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']

@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = ['title', 'expert', 'category', 'is_active', 'is_pinned', 'created_at']
    list_filter = ['is_pinned', 'is_active']
    actions = ['pin_gigs', 'unpin_gigs']

    def pin_gigs(self, request, queryset):
        queryset.update(is_pinned=True, pinned_at=timezone.now())
    pin_gigs.short_description = "Pin selected gigs"

    def unpin_gigs(self, request, queryset):
        queryset.update(is_pinned=False, pinned_at=None)
    unpin_gigs.short_description = "Unpin selected gigs"

@admin.register(GigPackage)
class GigPackageAdmin(admin.ModelAdmin):
    list_display = ['gig', 'tier', 'price', 'delivery_days']

@admin.register(GigExtra)
class GigExtraAdmin(admin.ModelAdmin):
    list_display = ['gig', 'name', 'price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'student', 'get_expert', 'get_gig_title',
        'total_price', 'status', 'payment_status', 'updated_at'
    ]
    list_filter  = ['status', 'payment_status', 'updated_at']
    search_fields = ['student__username', 'package__gig__expert__user__username']
    readonly_fields = ['created_at', 'updated_at']

    def get_expert(self, obj):
        try:
            return obj.package.gig.expert.user.username
        except Exception:
            return '-'
    get_expert.short_description = 'Expert'

    def get_gig_title(self, obj):
        try:
            return obj.package.gig.title
        except Exception:
            return '-'
    get_gig_title.short_description = 'Gig'

    # ── Custom earnings summary page ──────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('earnings/', self.admin_site.admin_view(self.earnings_view), name='order-earnings'),
        ]
        return custom + urls

    def earnings_view(self, request):
        today      = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end   = week_start + timedelta(days=6)

        from_date = request.GET.get('from', str(week_start))
        to_date   = request.GET.get('to',   str(week_end))

        orders = Order.objects.filter(
            status='completed',
            payment_status='released',
            updated_at__date__range=[from_date, to_date],
        ).select_related('package__gig__expert__user')

        from collections import defaultdict
        earnings = defaultdict(lambda: {'username': '', 'email': '', 'orders': 0, 'gross': 0.0, 'fee': 0.0, 'net': 0.0})

        for order in orders:
            try:
                user = order.package.gig.expert.user
            except Exception:
                continue
            earnings[user.id]['username'] = user.username
            earnings[user.id]['email']    = user.email
            earnings[user.id]['orders']  += 1
            gross = float(order.total_price)
            earnings[user.id]['gross']   += gross
            earnings[user.id]['fee']     += gross * 0.10
            earnings[user.id]['net']     += gross * 0.90

        context = {
            **self.admin_site.each_context(request),
            'title':     'Expert Earnings',
            'from_date': from_date,
            'to_date':   to_date,
            'earnings':  sorted(earnings.values(), key=lambda x: x['net'], reverse=True),
        }
        return TemplateResponse(request, 'admin/order_earnings.html', context)