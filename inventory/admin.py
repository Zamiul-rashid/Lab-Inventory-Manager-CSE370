# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.contrib import messages
from .models import User, Product, Borrow, Notification, LoanHistory # Import all models here..

@admin.register(User) #register the User model with the admin site
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'firstname', 'lastname', 'role', 'date_created', 'is_active')
    list_filter = ('role', 'is_active', 'date_created')
    search_fields = ('username', 'email', 'firstname', 'lastname')
    ordering = ('-date_created',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('firstname', 'lastname', 'role', 'date_created')  # Removed user_name
        }),
    )
    
    readonly_fields = ('date_created',)

@admin.register(Product) # Register the Product model with the admin site
class ProductAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'category', 'brand', 'status', 'quantity_available', 'current_location', 'created_at')
    list_filter = ('status', 'category', 'brand', 'created_at')
    search_fields = ('name', 'description', 'category', 'brand')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'category', 'brand')
        }),
        ('Inventory Details', {
            'fields': ('quantity_available', 'current_location', 'status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)

@admin.register(Borrow)
class BorrowAdmin(admin.ModelAdmin):
    list_display = ('borrow_id', 'user', 'product', 'borrow_date', 'expected_return_date', 'status', 'is_overdue')
    list_filter = ('status', 'borrow_date', 'expected_return_date')
    search_fields = ('user__username', 'product__name', 'notes')
    ordering = ('-created_at',)
    actions = ['mark_as_returned', 'mark_as_active']
    
    fieldsets = (
        ('Borrow Information', {
            'fields': ('user', 'product', 'borrow_date', 'expected_return_date', 'actual_return_date')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes', 'added_by')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'is_overdue')
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def mark_as_returned(self, request, queryset):
        """Admin action to mark selected borrows as returned"""
        updated_count = 0
        for borrow in queryset:
            if borrow.status in ['active', 'overdue']:
                # Mark borrow as returned
                borrow.status = 'returned'
                borrow.actual_return_date = timezone.now().date()
                borrow.save()
                
                # Update product status to available
                if borrow.product:
                    borrow.product.status = 'available'
                    borrow.product.save()
                
                updated_count += 1
        
        if updated_count:
            messages.success(request, f'{updated_count} borrow(s) marked as returned and products set to available.')
        else:
            messages.warning(request, 'No eligible borrows were updated. Only active/overdue borrows can be marked as returned.')
    
    mark_as_returned.short_description = "Mark selected borrows as returned"
    
    def mark_as_active(self, request, queryset):
        """Admin action to mark selected borrows as active (in case of mistakes)"""
        updated_count = 0
        for borrow in queryset:
            if borrow.status == 'returned':
                borrow.status = 'active'
                borrow.actual_return_date = None
                borrow.save()
                
                # Update product status to borrowed
                if borrow.product:
                    borrow.product.status = 'borrowed'
                    borrow.product.save()
                
                updated_count += 1
        
        if updated_count:
            messages.success(request, f'{updated_count} borrow(s) marked as active and products set to borrowed.')
        else:
            messages.warning(request, 'No returned borrows were found to reactivate.')
    
    mark_as_active.short_description = "Mark selected borrows as active (undo return)"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_id', 'recipient_user', 'message_preview', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('recipient_user__username', 'message')
    ordering = ('-created_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'

@admin.register(LoanHistory)
class LoanHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'borrow_date', 'return_date', 'status')
    list_filter = ('status', 'borrow_date', 'return_date')
    search_fields = ('user__username', 'product__name')
    ordering = ('-borrow_date',)

# Customize admin site headers
admin.site.site_header = "LIT - Lab Inventory Tracker"
admin.site.site_title = "LIT Admin"
admin.site.index_title = "Lab Inventory Tracker Administration"