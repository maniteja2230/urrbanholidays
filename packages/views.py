"""
Packages app views – Package list and detail
"""

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import TravelPackage, Destination


def package_list(request):
    """List all travel packages with search and filter"""
    packages = TravelPackage.objects.filter(is_active=True)

    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        packages = packages.filter(
            Q(name__icontains=search_query) |
            Q(destination__name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category filter
    category = request.GET.get('category', '')
    if category:
        packages = packages.filter(category=category)

    # Destination filter
    destination_id = request.GET.get('destination', '')
    if destination_id:
        packages = packages.filter(destination_id=destination_id)

    # Sort
    sort = request.GET.get('sort', '-is_featured')
    valid_sorts = ['-is_featured', 'price', '-price', '-rating', 'name']
    if sort in valid_sorts:
        packages = packages.order_by(sort)

    # Price range
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if min_price:
        packages = packages.filter(price__gte=min_price)
    if max_price:
        packages = packages.filter(price__lte=max_price)

    context = {
        'packages': packages,
        'destinations': Destination.objects.filter(is_active=True),
        'categories': TravelPackage.CATEGORY_CHOICES,
        'search_query': search_query,
        'selected_category': category,
        'selected_sort': sort,
        'total_count': packages.count(),
    }
    return render(request, 'packages/list.html', context)


def package_detail(request, slug):
    """Travel package detail page"""
    package = get_object_or_404(TravelPackage, slug=slug, is_active=True)
    related_packages = TravelPackage.objects.filter(
        is_active=True,
        category=package.category
    ).exclude(id=package.id)[:4]

    context = {
        'package': package,
        'related_packages': related_packages,
    }
    return render(request, 'packages/detail.html', context)
