# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Product, Borrow, Notification, LoanHistory
from .forms import UserRegistrationForm, CustomLoginForm, ProductForm, BorrowForm, UserProfileForm, UserSearchForm, ProductSearchForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import json


def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Renders the admin dashboard with links to user/product management and approvals.
    """
    return render(request, 'admin_dashboard.html', {
        'is_admin': True,
    })

def user_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        
        # Debug output
        print(f"Form data received: {request.POST}")
        print(f"Form is valid: {form.is_valid()}")
        
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
            print(f"Form non-field errors: {form.non_field_errors}")
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            print(f"Cleaned data: username='{username}', password='{password[:3]}***'")
            
            user = authenticate(username=username, password=password)
            print(f"Authentication result: {user}")
            
            if user is not None:
                login(request, user)
                user.last_login = timezone.now()
                user.save()
                return redirect('dashboard')
            else:
                print("authenticate() returned None")
        
        messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'login.html', {'form': form})

def user_register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set user as inactive by default (admin needs to approve)
            user.is_active = False
            user.save()
            
            # Create success message with User ID
            messages.success(
                request, 
                f'Registration successful! Your unique User ID is: {user.user_id}. '
                f'Please remember this ID and wait for admin approval before signing in.'
            )
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

@login_required
def user_logout(request):
    """Logout view with success message"""
    username = request.user.username
    logout(request)
    messages.success(request, f'You have been successfully logged out. Goodbye!')
    return redirect('login')

@login_required
def dashboard(request):
    user = request.user
    
    # Get statistics
    available_items = Product.objects.filter(status='available').count()
    my_borrowed = Borrow.objects.filter(user=user, status='active').count()
    pending_requests = Borrow.objects.filter(status='pending').count()
    total_categories = Product.objects.values('category').distinct().count()
    
    # Get recent activity
    recent_requests = Borrow.objects.filter(user=user).order_by('-created_at')[:5]
    currently_borrowed = Borrow.objects.filter(user=user, status='active')[:5]
    
    # Admin specific data
    pending_users = 0
    if user.role == 'admin':
        pending_users = User.objects.filter(is_active=False).count()
    
    context = {
        'available_items': available_items,
        'my_borrowed': my_borrowed,
        'pending_requests': pending_requests,
        'total_categories': total_categories,
        'recent_requests': recent_requests,
        'currently_borrowed': currently_borrowed,
        'pending_users': pending_users,
        'is_admin': user.role == 'admin',
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def items_list(request):
    products = Product.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(brand__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category=category_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        products = products.filter(status=status_filter)
    
    categories = Product.objects.values_list('category', flat=True).distinct()
    
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'items_list.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = BorrowForm(request.POST)
        if form.is_valid():
            borrow = form.save(commit=False)
            borrow.user = request.user
            borrow.product = product
            borrow.save()
            
            # Create notification for admin
            admin_users = User.objects.filter(role='admin')
            for admin in admin_users:
                Notification.objects.create(
                    recipient_user=admin,
                    related_user=request.user,
                    message=f"{request.user.username} requested to borrow {product.name}"
                )
            
            messages.success(request, 'Borrow request submitted successfully!')
            return redirect('product_detail', pk=pk)
    else:
        form = BorrowForm()
    
    # Check if user already has a pending request for this item
    existing_request = Borrow.objects.filter(
        user=request.user,
        product=product,
        status__in=['pending', 'approved', 'active']
    ).exists()
    
    context = {
        'product': product,
        'form': form,
        'existing_request': existing_request,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'product_detail.html', context)

@login_required
@user_passes_test(is_admin)
def add_item(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user  # Track who created this product
            product.save()
            messages.success(request, 'Item added successfully!')
            return redirect('items_list')
    else:
        form = ProductForm()
    
    return render(request, 'add_item.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('items_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'update_product.html', {'form': form, 'product': product})

@login_required
@user_passes_test(is_admin)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('items_list')
    
    return render(request, 'delete_product.html', {'product': product})

@login_required
def my_requests(request):
    requests = Borrow.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'requests': requests,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'my_requests.html', context)

@login_required
def my_borrowed_items(request):
    borrowed_items = Borrow.objects.filter(
        user=request.user,
        status='active'
    ).order_by('-borrow_date')
    
    context = {
        'borrowed_items': borrowed_items,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'my_borrowed_items.html', context)

@login_required
def borrow_history(request):
    history = Borrow.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'history': history,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'borrow_history.html', context)

@login_required
@user_passes_test(is_admin)
def admin_pending_requests(request):
    pending_requests = Borrow.objects.filter(status='pending').order_by('-created_at')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        borrow = get_object_or_404(Borrow, borrow_id=request_id)
        
        if action == 'approve':
            borrow.status = 'active'
            borrow.product.status = 'borrowed'
            borrow.product.save()
            borrow.added_by = request.user  # Track which admin approved this
            borrow.save()
            
            # Create notification for user
            Notification.objects.create(
                recipient_user=borrow.user,
                related_user=request.user,
                message=f"Your request for {borrow.product.name} has been approved!"
            )
            
            messages.success(request, f'Request for {borrow.product.name} approved!')
            
        elif action == 'reject':
            borrow.status = 'rejected'
            borrow.added_by = request.user  # Track which admin rejected this
            borrow.save()
            
            # Create notification for user
            Notification.objects.create(
                recipient_user=borrow.user,
                related_user=request.user,
                message=f"Your request for {borrow.product.name} has been rejected."
            )
            
            messages.success(request, f'Request for {borrow.product.name} rejected!')
    
    context = {
        'pending_requests': pending_requests,
        'is_admin': True,
    }
    
    return render(request, 'admin_pending_requests.html', context)

@login_required
@user_passes_test(is_admin)
def admin_pending_users(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)
        
        if action == 'approve':
            user.is_active = True
            user.save()
            
            # Create a notification for the approved user (optional)
            Notification.objects.create(
                recipient_user=user,
                message=f"Your account has been approved! You can now log in to the system."
            )
            
            messages.success(request, f'User {user.username} ({user.get_full_name()}) has been approved!')
            
        elif action == 'reject':
            username = user.username
            full_name = user.get_full_name()
            user.delete()
            messages.success(request, f'User {username} ({full_name}) has been rejected and removed.')
        
        return redirect('admin_pending_users')
    
    # GET request - show pending users
    pending_users = User.objects.filter(is_active=False).order_by('-date_created')
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    context = {
        'pending_users': pending_users,
        'total_users': total_users,
        'active_users': active_users,
        'pending_count': pending_users.count(),
        'is_admin': True,
    }
    
    return render(request, 'admin_pending_users.html', context)

@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().order_by('-date_created')
    
    context = {
        'users': users,
        'is_admin': True,
    }
    
    return render(request, 'user_list.html', context)

@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('user_list')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'add_user.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def reports(request):
    # Generate various reports
    total_products = Product.objects.count()
    total_users = User.objects.filter(is_active=True).count()
    total_borrows = Borrow.objects.count()
    active_borrows = Borrow.objects.filter(status='active').count()
    overdue_items = Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).count()
    
    # Category distribution
    category_stats = Product.objects.values('category').annotate(
        count=Count('pk')  # Changed from Count('product_id') to Count('pk')
    ).order_by('-count')
    
    # Most borrowed items
    popular_items = Product.objects.annotate(
        borrow_count=Count('borrow_history')
    ).order_by('-borrow_count')[:10]
    
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_borrows': total_borrows,
        'active_borrows': active_borrows,
        'overdue_items': overdue_items,
        'category_stats': category_stats,
        'popular_items': popular_items,
        'is_admin': True,
    }
    
    return render(request, 'reports.html', context)

# Updated user_profile view with proper admin/regular user differentiation
@login_required
def user_profile(request, user_id=None):
    if user_id:
        profile_user = get_object_or_404(User, id=user_id)
    else:
        profile_user = request.user

    # Base context that applies to all users
    context = {
        'profile_user': profile_user,
        'form': UserProfileForm(instance=profile_user) if profile_user == request.user else None,
        'is_admin': request.user.role == 'admin',
    }

    # Admin-specific data
    if profile_user.role == 'admin':
        # Get products added by this admin
        admin_products = Product.objects.filter(created_by=profile_user).order_by('-created_at')
        products_added = admin_products.count()
        
        # Count users approved by this admin (you may need to add a field to track this)
        # For now, we'll use a placeholder or count from notifications
        users_approved = User.objects.filter(is_active=True).count() if profile_user.is_superuser else 0
        
        # Count requests processed by this admin
        requests_processed = Borrow.objects.filter(added_by=profile_user).count()
        
        # System-wide statistics that admins should see
        total_system_users = User.objects.filter(is_active=True).count()
        total_system_products = Product.objects.count()
        
        # Update context with admin-specific data
        context.update({
            'admin_products': admin_products,
            'products_added': products_added,
            'users_approved': users_approved,
            'requests_processed': requests_processed,
            'total_system_users': total_system_users,
            'total_system_products': total_system_products,
        })
    else:
        # Regular user statistics
        total_borrowed = Borrow.objects.filter(user=profile_user).count()
        currently_borrowed = Borrow.objects.filter(
            user=profile_user,
            status='active'
        ).count()
        returned_items = Borrow.objects.filter(
            user=profile_user,
            status='returned'
        ).count()
        pending_requests = Borrow.objects.filter(
            user=profile_user,
            status='pending'
        ).count()
        overdue_items = Borrow.objects.filter(
            user=profile_user,
            status='active',
            expected_return_date__lt=timezone.now().date()
        ).count()

        # Get complete borrow history with product details
        borrow_history = Borrow.objects.filter(
            user=profile_user
        ).select_related('product').order_by('-borrow_date')

        # Get recent requests for activity display
        recent_requests = Borrow.objects.filter(
            user=profile_user
        ).order_by('-created_at')[:5]

        # Update context with regular user data
        context.update({
            'total_borrowed': total_borrowed,
            'currently_borrowed': currently_borrowed,
            'returned_items': returned_items,
            'pending_requests': pending_requests,
            'overdue_items': overdue_items,
            'borrow_history': borrow_history,
            'recent_requests': recent_requests,
        })

    # Handle profile update form submission
    if request.method == 'POST' and profile_user == request.user:
        form = UserProfileForm(request.POST, instance=profile_user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
        else:
            # If form is invalid, update the context with the form containing errors
            context['form'] = form

    return render(request, 'user_profile.html', context)

# API endpoints
@login_required
def search_products_api(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__icontains=query)
    )[:10]
    
    results = [{
        'id': p.pk,  # Using pk instead of product_id
        'name': p.name,
        'category': p.category,
        'status': p.status
    } for p in products]
    
    return JsonResponse({'results': results})

@login_required
@user_passes_test(is_admin)
def update_product_status_api(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        new_status = request.POST.get('status')
        
        if new_status in dict(Product.PRODUCT_STATUS):
            product.status = new_status
            product.save()
            return JsonResponse({'success': True, 'message': 'Status updated successfully'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def change_password(request):
    """Handle password change via AJAX"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate old password
        if not request.user.check_password(old_password):
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect.'
            })
        
        # Validate new passwords match
        if new_password1 != new_password2:
            return JsonResponse({
                'success': False,
                'error': 'New passwords do not match.'
            })
        
        # Validate password length
        if len(new_password1) < 8:
            return JsonResponse({
                'success': False,
                'error': 'Password must be at least 8 characters long.'
            })
        
        # Change password
        request.user.set_password(new_password1)
        request.user.save()
        
        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully!'
        })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method.'
    })