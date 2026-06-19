"""
Packages app models – Travel Package catalog
"""

from django.db import models
from django.utils.text import slugify


class Destination(models.Model):
    """Destination/Region model"""
    name = models.CharField(max_length=150)
    country = models.CharField(max_length=100, default='India')
    image = models.ImageField(upload_to='destinations/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Destination'
        verbose_name_plural = 'Destinations'

    def __str__(self):
        return f"{self.name}, {self.country}"


class TravelPackage(models.Model):
    """Travel package offered by Urban Holidays"""
    CATEGORY_CHOICES = [
        ('beach', 'Beach'),
        ('hill', 'Hill Station'),
        ('adventure', 'Adventure'),
        ('pilgrimage', 'Pilgrimage'),
        ('honeymoon', 'Honeymoon'),
        ('wildlife', 'Wildlife'),
        ('international', 'International'),
        ('city', 'City Tour'),
        ('cultural', 'Cultural'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    destination = models.ForeignKey(
        Destination, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packages'
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='beach')

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.PositiveSmallIntegerField(default=0)

    # Details
    duration_days = models.PositiveSmallIntegerField(default=3)
    duration_nights = models.PositiveSmallIntegerField(default=2)
    max_persons = models.PositiveSmallIntegerField(default=10)
    description = models.TextField()
    highlights = models.TextField(help_text='One highlight per line', blank=True)
    inclusions = models.TextField(help_text='One item per line', blank=True)
    exclusions = models.TextField(help_text='One item per line', blank=True)
    itinerary = models.TextField(blank=True)

    # Media
    thumbnail = models.ImageField(upload_to='packages/thumbnails/', blank=True, null=True)
    gallery_images = models.TextField(
        help_text='Comma-separated image URLs',
        blank=True
    )

    # Flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_voucher_applicable = models.BooleanField(
        default=True,
        help_text='Can Urban Holidays vouchers be used for this package?'
    )

    # Rating
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = 'Travel Package'
        verbose_name_plural = 'Travel Packages'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def highlights_list(self):
        return [h.strip() for h in self.highlights.splitlines() if h.strip()]

    @property
    def inclusions_list(self):
        return [i.strip() for i in self.inclusions.splitlines() if i.strip()]

    @property
    def exclusions_list(self):
        return [e.strip() for e in self.exclusions.splitlines() if e.strip()]

    @property
    def discount_amount(self):
        if self.original_price:
            return self.original_price - self.price
        return 0

    @property
    def stars_range(self):
        return range(1, 6)
