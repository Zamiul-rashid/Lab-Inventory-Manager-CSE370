# orm_examples.py - Advanced Django ORM Examples

from django.db.models import Q, F, Count, Sum, Avg, Max, Min
from django.db.models import Case, When, Value
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Product, Borrow

# 1. Complex Filtering with Q Objects
def complex_product_search(search_term, category=None, min_quantity=0):
    """Advanced product search with multiple conditions"""
    query = Q(name__icontains=search_term) | Q(description__icontains=search_term)
    
    if category:
        query &= Q(category=category)
    
    if min_quantity > 0:
        query &= Q(quantity_available__gte=min_quantity)
    
    return Product.objects.filter(query)

# 2. Aggregation Queries
def get_user_statistics():
    """Get aggregated user statistics"""
    return User.objects.aggregate(
        total_users=Count('id'),
        active_users=Count('id', filter=Q(is_active=True)),
        admin_users=Count('id', filter=Q(role='admin')),
        avg_borrows_per_user=Avg('borrowed_items__id')
    )

def get_product_statistics():
    """Get product statistics with annotations"""
    return Product.objects.annotate(
        total_borrows=Count('borrow_history'),
        active_borrows=Count('borrow_history', filter=Q(borrow_history__status='active')),
        popularity_score=Count('borrow_history') * 10
    ).order_by('-popularity_score')

# 3. F Expressions for Database-Level Operations
def update_product_quantities():
    """Update product quantities using F expressions"""
    # Increase all quantities by 1 (done at database level)
    Product.objects.update(quantity_available=F('quantity_available') + 1)
    
    # Update based on conditions
    Product.objects.filter(status='borrowed').update(
        quantity_available=F('quantity_available') - 1
    )

# 4. Subqueries and Exists
def get_products_with_pending_requests():
    """Get products that have pending borrow requests"""
    return Product.objects.filter(
        borrow_history__status='pending'
    ).distinct()

def get_users_with_overdue_items():
    """Get users who have overdue items"""
    today = timezone.now().date()
    return User.objects.filter(
        borrowed_items__status='active',
        borrowed_items__expected_return_date__lt=today
    ).distinct()

# 5. Complex Annotations with Case/When
def get_products_with_status_priority():
    """Annotate products with priority based on status"""
    return Product.objects.annotate(
        priority=Case(
            When(status='damaged', then=Value(1)),
            When(status='maintenance', then=Value(2)),
            When(status='borrowed', then=Value(3)),
            When(status='available', then=Value(4)),
            default=Value(5)
        )
    ).order_by('priority', 'name')

# 6. Date-based Queries
def get_recently_created_products(days=30):
    """Get products created in the last N days"""
    cutoff_date = timezone.now() - timedelta(days=days)
    return Product.objects.filter(created_at__gte=cutoff_date)

def get_overdue_borrows():
    """Get all overdue borrows with detailed info"""
    today = timezone.now().date()
    return Borrow.objects.select_related('user', 'product').filter(
        status='active',
        expected_return_date__lt=today
    ).annotate(
        days_overdue=Case(
            When(
                expected_return_date__lt=today,
                then=F('expected_return_date') - today
            ),
            default=Value(0)
        )
    )

# 7. Custom Managers
class ProductManager(models.Manager):
    def available(self):
        return self.filter(status='available', quantity_available__gt=0)
    
    def popular(self, limit=10):
        return self.annotate(
            borrow_count=Count('borrow_history')
        ).order_by('-borrow_count')[:limit]
    
    def by_category(self, category):
        return self.filter(category__iexact=category)

# Add to Product model:
# objects = ProductManager()

# 8. Bulk Operations
def bulk_update_product_status(product_ids, new_status):
    """Bulk update product status"""
    Product.objects.filter(id__in=product_ids).update(status=new_status)

def bulk_create_notifications(user_message_pairs):
    """Bulk create notifications"""
    notifications = [
        Notification(recipient_user=user, message=message)
        for user, message in user_message_pairs
    ]
    Notification.objects.bulk_create(notifications)

# 9. Raw SQL (when ORM isn't enough)
def get_complex_report():
    """Example of raw SQL query"""
    return Product.objects.raw('''
        SELECT p.*, 
               COUNT(b.borrow_id) as total_borrows,
               AVG(DATEDIFF(b.actual_return_date, b.borrow_date)) as avg_borrow_days
        FROM inventory_product p
        LEFT JOIN inventory_borrow b ON p.product_id = b.product_id
        WHERE p.created_at >= %s
        GROUP BY p.product_id
        ORDER BY total_borrows DESC
    ''', [timezone.now() - timedelta(days=365)])

# 10. Database Functions
from django.db.models import Extract
def get_monthly_borrow_stats():
    """Get borrow statistics by month"""
    return Borrow.objects.annotate(
        month=Extract('borrow_date', 'month'),
        year=Extract('borrow_date', 'year')
    ).values('year', 'month').annotate(
        total_borrows=Count('id'),
        unique_users=Count('user', distinct=True),
        unique_products=Count('product', distinct=True)
    ).order_by('year', 'month')
