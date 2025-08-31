# models.py
import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    USER_ROLES = (
        ('admin', 'Admin'),
        ('regular_user', 'Regular User'),
    )
    
    # Add unique user ID field
    user_id = models.CharField(max_length=5, unique=True, null=True, editable=False)
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    date_created = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='regular_user')
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'firstname', 'lastname']
    
    def save(self, *args, **kwargs):
        # Generate unique 5-digit user ID if not exists
        if not self.user_id:
            self.user_id = self.generate_unique_user_id()
        super().save(*args, **kwargs)
    
    def generate_unique_user_id(self):
        """Generate a unique 5-digit user ID"""
        while True:
            # Generate random 5-digit number (10000-99999)
            user_id = str(random.randint(10000, 99999))
            if not User.objects.filter(user_id=user_id).exists():
                return user_id
    
    def __str__(self):
        return f"{self.username} (ID: {self.user_id})"
    
    def get_full_name(self):
        return f"{self.firstname} {self.lastname}".strip()
    
    def get_borrow_history(self):
        """Return complete borrow history for this user"""
        return self.borrowed_items.all().order_by('-borrow_date')

class Product(models.Model):
    PRODUCT_STATUS = (
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('maintenance', 'Under Maintenance'),
        ('damaged', 'Damaged'),
    )
    
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    quantity_available = models.PositiveIntegerField(default=1)
    current_location = models.CharField(max_length=200, default='Lab Storage')
    status = models.CharField(max_length=20, choices=PRODUCT_STATUS, default='available')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_products')
    
    def __str__(self):
        return f"{self.name} ({self.category})"

class Borrow(models.Model):
    BORROW_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    )
    
    borrow_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='borrow_history')
    borrow_date = models.DateTimeField(default=timezone.now)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=BORROW_STATUS, default='pending')
    notes = models.TextField(blank=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_borrows')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.status})"
    
    @property
    def is_overdue(self):
        if self.status in ['active', 'approved'] and self.expected_return_date < timezone.now().date():
            return True
        return False

class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    recipient_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification to {self.recipient_user.username}: {self.message[:50]}"

class LoanHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.borrow_date}"