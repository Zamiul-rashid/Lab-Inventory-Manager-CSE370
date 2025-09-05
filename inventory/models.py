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
    # SQL: user_id VARCHAR(5) UNIQUE NULL
    user_id = models.CharField(max_length=5, unique=True, null=True, editable=False)
    
    # SQL: firstname VARCHAR(50) NOT NULL
    firstname = models.CharField(max_length=50)
    
    # SQL: lastname VARCHAR(50) NOT NULL
    lastname = models.CharField(max_length=50)
    
    # SQL: email VARCHAR(254) UNIQUE NOT NULL
    email = models.EmailField(unique=True)
    
    # SQL: date_created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    date_created = models.DateTimeField(default=timezone.now)
    
    # SQL: role VARCHAR(20) NOT NULL DEFAULT 'regular_user'
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
    
    # SQL: product_id INT AUTO_INCREMENT PRIMARY KEY
    product_id = models.AutoField(primary_key=True)
    
    # SQL: name VARCHAR(200) NOT NULL
    name = models.CharField(max_length=200)
    
    # SQL: description TEXT NULL
    description = models.TextField(blank=True)
    
    # SQL: category VARCHAR(100) NOT NULL
    category = models.CharField(max_length=100)
    
    # SQL: brand VARCHAR(100) NULL
    brand = models.CharField(max_length=100, blank=True)
    
    # SQL: quantity_available INT UNSIGNED NOT NULL DEFAULT 1
    quantity_available = models.PositiveIntegerField(default=1)
    
    # SQL: current_location VARCHAR(200) NOT NULL DEFAULT 'Lab Storage'
    current_location = models.CharField(max_length=200, default='Lab Storage')
    
    # SQL: status VARCHAR(20) NOT NULL DEFAULT 'available'
    status = models.CharField(max_length=20, choices=PRODUCT_STATUS, default='available')
    
    # SQL: notes TEXT NULL
    notes = models.TextField(blank=True)
    
    # SQL: created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    created_at = models.DateTimeField(default=timezone.now)
    
    # SQL: created_by_id INT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE SET NULL
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
    
    # SQL: borrow_id INT AUTO_INCREMENT PRIMARY KEY
    borrow_id = models.AutoField(primary_key=True)
    
    # SQL: user_id INT NOT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE CASCADE
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_items')
    
    # SQL: product_id INT NOT NULL, FOREIGN KEY REFERENCES inventory_product(product_id) ON DELETE CASCADE
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='borrow_history')
    
    # SQL: borrow_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    borrow_date = models.DateTimeField(default=timezone.now)
    
    # SQL: expected_return_date DATE NOT NULL
    expected_return_date = models.DateField()
    
    # SQL: actual_return_date DATE NULL
    actual_return_date = models.DateField(null=True, blank=True)
    
    # SQL: status VARCHAR(20) NOT NULL DEFAULT 'pending'
    status = models.CharField(max_length=20, choices=BORROW_STATUS, default='pending')
    
    # SQL: notes TEXT NULL
    notes = models.TextField(blank=True)
    
    # SQL: added_by_id INT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE SET NULL
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_borrows')
    
    # SQL: created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.status})"
    
    @property
    def is_overdue(self):
        if self.status in ['active', 'approved'] and self.expected_return_date < timezone.now().date():
            return True
        return False
    
    @property
    def days_until_due(self):
        """Calculate days until the item is due"""
        if self.expected_return_date:
            today = timezone.now().date()
            delta = self.expected_return_date - today
            return max(0, delta.days)  # Don't return negative days
        return 0
    
    @property
    def days_overdue(self):
        """Calculate how many days overdue the item is"""
        if self.expected_return_date and self.status in ['active', 'approved']:
            today = timezone.now().date()
            if self.expected_return_date < today:
                delta = today - self.expected_return_date
                return delta.days
        return 0

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('user_registration', 'User Registration'),
        ('borrow_request', 'Borrow Request'),
        ('borrow_approved', 'Borrow Approved'),
        ('borrow_rejected', 'Borrow Rejected'),
        ('return_reminder', 'Return Reminder'),
        ('overdue_alert', 'Overdue Alert'),
        ('item_returned', 'Item Returned'),
        ('general', 'General'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    # SQL: notification_id INT AUTO_INCREMENT PRIMARY KEY
    notification_id = models.AutoField(primary_key=True)
    
    # SQL: recipient_user_id INT NOT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE CASCADE
    recipient_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # SQL: related_user_id INT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE SET NULL
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # SQL: related_borrow_id INT NULL, FOREIGN KEY REFERENCES inventory_borrow(borrow_id) ON DELETE SET NULL
    related_borrow = models.ForeignKey('Borrow', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    # SQL: notification_type VARCHAR(30) NOT NULL DEFAULT 'general'
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='general')
    
    # SQL: priority VARCHAR(10) NOT NULL DEFAULT 'medium'
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # SQL: title VARCHAR(200) NOT NULL
    title = models.CharField(max_length=200, default='Notification')
    
    # SQL: message TEXT NOT NULL
    message = models.TextField()
    
    # SQL: created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    created_at = models.DateTimeField(default=timezone.now)
    
    # SQL: is_read BOOLEAN NOT NULL DEFAULT 0
    is_read = models.BooleanField(default=False)
    
    # SQL: read_at DATETIME NULL
    read_at = models.DateTimeField(null=True, blank=True)
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Notification to {self.recipient_user.username}: {self.title[:50]}"
    
    class Meta:
        ordering = ['-created_at']

class LoanHistory(models.Model):
    # SQL: user_id INT NOT NULL, FOREIGN KEY REFERENCES inventory_user(id) ON DELETE CASCADE
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # SQL: product_id INT NOT NULL, FOREIGN KEY REFERENCES inventory_product(product_id) ON DELETE CASCADE
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # SQL: borrow_date DATETIME NOT NULL
    borrow_date = models.DateTimeField()
    
    # SQL: return_date DATETIME NULL
    return_date = models.DateTimeField(null=True, blank=True)
    
    # SQL: status VARCHAR(20) NOT NULL
    status = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.borrow_date}"