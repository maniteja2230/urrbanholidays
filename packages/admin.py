"""
Packages app admin
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import TravelPackage, Destination


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'country']


@admin.register(TravelPackage)
class TravelPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'destination', 'category', 'price', 'duration_days',
                    'is_featured', 'is_active', 'rating', 'thumbnail_preview']
    list_editable = ['is_featured', 'is_active', 'price']
    list_filter = ['is_active', 'is_featured', 'category', 'destination']
    search_fields = ['name', 'description', 'destination__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Basic Info', {'fields': ['name', 'slug', 'destination', 'category', 'description']}),
        ('Pricing', {'fields': ['price', 'original_price', 'discount_percent']}),
        ('Duration', {'fields': ['duration_days', 'duration_nights', 'max_persons']}),
        ('Details', {'fields': ['highlights', 'inclusions', 'exclusions', 'itinerary']}),
        ('Media', {'fields': ['thumbnail', 'gallery_images']}),
        ('Settings', {'fields': ['is_active', 'is_featured', 'is_voucher_applicable', 'rating', 'review_count']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="60" height="40" style="object-fit:cover;border-radius:4px;">', obj.thumbnail.url)
        return '–'
    thumbnail_preview.short_description = 'Image'
