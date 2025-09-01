# performance_tips.py - Django Performance Optimization Examples

from django.db import models
from django.core.cache import cache
from django.db.models import Prefetch, F, Q, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from .models import User, Product, Borrow

# 1. Database Query Optimization

def get_products_with_borrows_optimized():
    """
    Optimized query using select_related and prefetch_related
    to avoid N+1 query problem
    """
    return Product.objects.select_related('created_by').prefetch_related(
        Prefetch(
            'borrow_history',
            queryset=Borrow.objects.select_related('user').filter(status='active')
        )
    )

def get_user_dashboard_data_optimized(user):
    """
    Optimized dashboard data fetching with minimal queries
    """
    # Single query for counts using aggregation
    stats = Product.objects.aggregate(
        available_count=Count('pk', filter=Q(status='available')),
        total_categories=Count('category', distinct=True)
    )
    
    # User-specific counts with single queries
    user_stats = Borrow.objects.filter(user=user).aggregate(
        my_borrowed=Count('pk', filter=Q(status='active')),
        pending_requests=Count('pk', filter=Q(status='pending'))
    )
    
    # Recent activity with select_related to avoid additional queries
    recent_requests = Borrow.objects.select_related('product').filter(
        user=user
    ).order_by('-created_at')[:5]
    
    return {
        **stats,
        **user_stats,
        'recent_requests': recent_requests
    }

def bulk_update_products(product_updates):
    """
    Bulk update products for better performance
    """
    products_to_update = []
    
    for product_id, new_data in product_updates.items():
        product = Product(pk=product_id, **new_data)
        products_to_update.append(product)
    
    # Bulk update in single query
    Product.objects.bulk_update(
        products_to_update, 
        ['status', 'quantity_available', 'current_location']
    )

# 2. Caching Strategies

def get_popular_products(limit=10):
    """
    Cache popular products list
    """
    cache_key = f'popular_products_{limit}'
    popular_products = cache.get(cache_key)
    
    if popular_products is None:
        popular_products = list(
            Product.objects.annotate(
                borrow_count=Count('borrow_history')
            ).order_by('-borrow_count')[:limit]
        )
        
        # Cache for 1 hour
        cache.set(cache_key, popular_products, 3600)
    
    return popular_products

def invalidate_product_cache(product_id):
    """
    Invalidate related caches when product is updated
    """
    cache.delete_many([
        f'product_{product_id}',
        'popular_products_10',
        'category_stats',
        'dashboard_stats'
    ])

class CachedProductStats:
    """
    Class-based caching for product statistics
    """
    
    @classmethod
    def get_category_distribution(cls):
        cache_key = 'category_stats'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = list(
                Product.objects.values('category').annotate(
                    count=Count('pk')
                ).order_by('-count')
            )
            cache.set(cache_key, stats, 1800)  # 30 minutes
            
        return stats
    
    @classmethod
    def get_system_overview(cls):
        cache_key = 'system_overview'
        overview = cache.get(cache_key)
        
        if overview is None:
            overview = {
                'total_products': Product.objects.count(),
                'total_users': User.objects.filter(is_active=True).count(),
                'active_borrows': Borrow.objects.filter(status='active').count(),
                'categories': Product.objects.values_list('category', flat=True).distinct().count()
            }
            cache.set(cache_key, overview, 300)  # 5 minutes
            
        return overview

# 3. View-Level Caching

@cache_page(60 * 15)  # Cache for 15 minutes
@vary_on_cookie  # Vary cache by user
def cached_dashboard_view(request):
    """
    Example of view-level caching
    """
    # This view will be cached per user for 15 minutes
    pass

# 4. Database Connection Optimization

# In settings.py, you should configure:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#         'CONN_MAX_AGE': 600,  # Connection pooling
#     }
# }

# 5. Efficient Pagination

def paginate_products_efficiently(request, queryset, per_page=20):
    """
    Efficient pagination using cursor-based pagination for large datasets
    """
    from django.core.paginator import Paginator
    from django.shortcuts import get_object_or_404
    
    # For very large datasets, use cursor pagination
    cursor = request.GET.get('cursor')
    
    if cursor:
        # Cursor-based pagination (more efficient for large datasets)
        products = queryset.filter(pk__gt=cursor).order_by('pk')[:per_page + 1]
        
        has_next = len(products) > per_page
        if has_next:
            products = products[:-1]
            next_cursor = products[-1].pk if products else None
        else:
            next_cursor = None
            
        return {
            'products': products,
            'has_next': has_next,
            'next_cursor': next_cursor
        }
    else:
        # Traditional pagination for smaller datasets
        paginator = Paginator(queryset, per_page)
        page = request.GET.get('page', 1)
        return paginator.get_page(page)

# 6. Index Optimization (Add to models.py)

class OptimizedProduct(models.Model):
    """
    Example of optimized Product model with proper indexing
    """
    name = models.CharField(max_length=200, db_index=True)  # Index for searches
    category = models.CharField(max_length=100, db_index=True)  # Index for filtering
    status = models.CharField(max_length=20, choices=[...], db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        # Composite indexes for common query patterns
        indexes = [
            models.Index(fields=['category', 'status']),  # Category + status filtering
            models.Index(fields=['status', '-created_at']),  # Status with ordering
            models.Index(fields=['name', 'category']),  # Search optimization
        ]

# 7. Background Tasks for Heavy Operations

from django.core.management.base import BaseCommand
import logging

class Command(BaseCommand):
    """
    Management command for background processing
    Usage: python manage.py process_overdue_items
    """
    help = 'Process overdue items and send notifications'
    
    def handle(self, *args, **options):
        from datetime import date
        
        # Find overdue items
        overdue_borrows = Borrow.objects.filter(
            status='active',
            expected_return_date__lt=date.today()
        ).select_related('user', 'product')
        
        # Update status and create notifications in batch
        overdue_ids = []
        notifications = []
        
        for borrow in overdue_borrows:
            overdue_ids.append(borrow.pk)
            notifications.append(
                Notification(
                    recipient_user=borrow.user,
                    message=f"Your borrowed item '{borrow.product.name}' is overdue."
                )
            )
        
        # Bulk operations
        Borrow.objects.filter(pk__in=overdue_ids).update(status='overdue')
        Notification.objects.bulk_create(notifications)
        
        self.stdout.write(
            self.style.SUCCESS(f'Processed {len(overdue_ids)} overdue items')
        )

# 8. Memory-Efficient QuerySets

def process_all_products_memory_efficient():
    """
    Process all products without loading them all into memory
    """
    # Use iterator() for large querysets to avoid memory issues
    for product in Product.objects.all().iterator(chunk_size=1000):
        # Process each product individually
        # This won't load all products into memory at once
        process_single_product(product)

def process_single_product(product):
    """Process a single product"""
    pass

# 9. Database Function Usage

from django.db.models import Case, When, Value, IntegerField

def get_products_with_priority():
    """
    Use database functions for complex calculations
    """
    return Product.objects.annotate(
        priority=Case(
            When(status='damaged', then=Value(1)),
            When(status='maintenance', then=Value(2)),
            When(status='borrowed', then=Value(3)),
            When(status='available', then=Value(4)),
            default=Value(5),
            output_field=IntegerField()
        ),
        # Calculate days since creation at database level
        days_old=F('created_at') - models.functions.Now()
    ).order_by('priority', 'days_old')

# 10. Monitoring and Profiling

import time
import functools
import logging

logger = logging.getLogger(__name__)

def log_db_queries(func):
    """
    Decorator to log database queries for a view
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import connection
        
        # Reset queries
        connection.queries_log.clear()
        start_time = time.time()
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Log performance metrics
        end_time = time.time()
        query_count = len(connection.queries)
        
        logger.info(
            f"View {func.__name__}: {query_count} queries in "
            f"{end_time - start_time:.2f}s"
        )
        
        # Log slow queries
        for query in connection.queries:
            if float(query['time']) > 0.5:  # Log queries slower than 500ms
                logger.warning(f"Slow query: {query['sql'][:100]}...")
        
        return result
    return wrapper

# Usage:
# @log_db_queries
# def my_view(request):
#     return render(request, 'template.html', context)

# Performance Tips Summary:
# 1. Use select_related() for foreign keys
# 2. Use prefetch_related() for reverse foreign keys and many-to-many
# 3. Use only() and defer() to limit fields loaded
# 4. Use bulk_create(), bulk_update() for mass operations
# 5. Use database indexes for frequently queried fields
# 6. Implement caching at multiple levels
# 7. Use database functions instead of Python logic when possible
# 8. Monitor query performance and optimize N+1 problems
# 9. Use iterator() for large datasets
# 10. Implement background tasks for heavy operations
