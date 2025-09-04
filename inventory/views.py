# views.py - Updated Lab Inventory Management System
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Product, Borrow, Notification, LoanHistory
from .forms import UserRegistrationForm, CustomLoginForm, ProductForm, BorrowForm, UserProfileForm, UserSearchForm, ProductSearchForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import json
import csv


def is_admin(user):
    """Check if user is an admin"""
    return user.is_authenticated and user.role == 'admin'


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Renders the admin dashboard with comprehensive statistics and recent activity.
    """
    # Get comprehensive statistics
    total_products = Product.objects.count()
    available_products = Product.objects.filter(status='available').count()
    borrowed_products = Product.objects.filter(status='borrowed').count()
    maintenance_products = Product.objects.filter(status='maintenance').count()
    damaged_products = Product.objects.filter(status='damaged').count()
    
    total_users = User.objects.filter(is_active=True).count()
    pending_users = User.objects.filter(is_active=False).count()
    
    pending_requests = Borrow.objects.filter(status='pending').count()
    active_borrows = Borrow.objects.filter(status='active').count()
    
    # Calculate overdue items
    overdue_items = Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).count()
    
    # Get recent borrow activity for the activity feed
    recent_borrows = Borrow.objects.select_related('user', 'product', 'added_by').order_by('-created_at')[:10]
    
    # Get category breakdown
    category_stats = Product.objects.values('category').annotate(
        count=Count('pk')
    ).order_by('-count')[:5]
    
    context = {
        'total_products': total_products,
        'available_products': available_products,
        'borrowed_products': borrowed_products,
        'maintenance_products': maintenance_products,
        'damaged_products': damaged_products,
        'total_users': total_users,
        'pending_users': pending_users,
        'pending_requests': pending_requests,
        'active_borrows': active_borrows,
        'overdue_items': overdue_items,
        'recent_borrows': recent_borrows,
        'category_stats': category_stats,
        'is_admin': True,
    }
    
    return render(request, 'admin_dashboard.html', context)


def user_login(request):
    """Handle user login with proper validation and redirects"""
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if user account is active (approved by admin)
                if user.is_active:
                    login(request, user)
                    user.last_login = timezone.now()
                    user.save()
                    
                    # Redirect based on user role
                    if user.role == 'admin':
                        messages.success(request, f'Welcome back, {user.get_full_name()}!')
                        return redirect('admin_dashboard')
                    else:
                        messages.success(request, f'Welcome back, {user.get_full_name()}!')
                        return redirect('dashboard')
                else:
                    messages.error(request, 'Your account is pending approval. Please contact an administrator.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'login.html', {'form': form})


def user_register(request):
    """Handle user registration with admin approval workflow"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set user as inactive until admin approval
            user.is_active = False
            user.save()
            
            # Notify all admins about new user registration
            admin_users = User.objects.filter(role='admin', is_active=True)
            for admin in admin_users:
                try:
                    Notification.objects.create(
                        recipient_user=admin,
                        related_user=user,
                        message=f"New user {user.username} ({user.get_full_name()}) has registered and is waiting for approval."
                    )
                except Exception as e:
                    print(f"Failed to create notification: {e}")
            
            # Create success message with User ID
            messages.success(
                request, 
                f'Registration successful! Your unique User ID is: {user.user_id}. '
                f'Your account is pending approval by an administrator. You will be notified once approved.'
            )
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})


@login_required
def user_logout(request):
    """Logout view with success message"""
    logout(request)
    messages.success(request, 'You have been successfully logged out. Goodbye!')
    return redirect('login')


@login_required
def dashboard(request):
    """Main dashboard for regular users and admins"""
    user = request.user
    
    # Get statistics
    available_items = Product.objects.filter(status='available').count()
    my_borrowed = Borrow.objects.filter(user=user, status='active').count()
    pending_requests = Borrow.objects.filter(status='pending').count()
    total_categories = Product.objects.values('category').distinct().count()
    
    # Get recent activity with optimized queries
    recent_requests = Borrow.objects.select_related('product').filter(user=user).order_by('-created_at')[:5]
    currently_borrowed = Borrow.objects.select_related('product').filter(user=user, status='active')[:5]
    
    # Admin specific data
    pending_users = 0
    pending_borrow_requests = 0
    if user.role == 'admin':
        pending_users = User.objects.filter(is_active=False).count()
        pending_borrow_requests = Borrow.objects.filter(status='pending').count()
    
    # Get today's date for template comparisons
    today = timezone.now().date()
    
    context = {
        'available_items': available_items,
        'my_borrowed': my_borrowed,
        'pending_requests': pending_requests,
        'total_categories': total_categories,
        'recent_requests': recent_requests,
        'currently_borrowed': currently_borrowed,
        'pending_users': pending_users,
        'pending_borrow_requests': pending_borrow_requests,
        'is_admin': user.role == 'admin',
        'today': today,
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def items_list(request):
    """Display and filter product list"""
    # Base query
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
    
    # Get distinct categories for filter dropdown
    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')
    
    context = {
        'products': products.order_by('name'),
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'items_list.html', context)


@login_required
def product_detail(request, pk):
    """Display product details and handle borrow requests"""
    product = get_object_or_404(Product, product_id=pk)
    
    if request.method == 'POST':
        # Check if user already has a pending request for this item
        existing_request = Borrow.objects.filter(
            user=request.user,
            product=product,
            status__in=['pending', 'approved', 'active']
        ).exists()
        
        if existing_request:
            messages.error(request, 'You already have a pending or active request for this item.')
            return redirect('product_detail', pk=pk)
        
        if product.status != 'available':
            messages.error(request, 'This item is not available for borrowing.')
            return redirect('product_detail', pk=pk)
        
        # Create borrow request
        borrow = Borrow.objects.create(
            user=request.user,
            product=product,
            status='pending',
            borrow_date=timezone.now().date(),
            expected_return_date=timezone.now().date() + timedelta(days=7)  # Default 7 days
        )
        
        # Create notification for admins
        admin_users = User.objects.filter(role='admin', is_active=True)
        for admin in admin_users:
            try:
                Notification.objects.create(
                    recipient_user=admin,
                    related_user=request.user,
                    message=f"{request.user.username} requested to borrow {product.name}"
                )
            except Exception as e:
                print(f"Failed to create notification: {e}")
        
        messages.success(request, 'Borrow request submitted successfully!')
        return redirect('product_detail', pk=pk)
    
    # Check if user already has a pending request for this item
    existing_request = Borrow.objects.filter(
        user=request.user,
        product=product,
        status__in=['pending', 'approved', 'active']
    ).exists()
    
    # Get borrow history for this product
    borrow_history = Borrow.objects.filter(
        product=product,
        status__in=['returned', 'active']
    ).select_related('user').order_by('-created_at')[:5]
    
    context = {
        'product': product,
        'existing_request': existing_request,
        'borrow_history': borrow_history,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'product_detail.html', context)


@login_required
@user_passes_test(is_admin)
def add_item(request):
    """Add new item to inventory (Admin only)"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Item "{product.name}" added successfully!')
            return redirect('items_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    return render(request, 'add_item.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def update_product(request, pk):
    """Update existing product (Admin only)"""
    product = get_object_or_404(Product, product_id=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            updated_product = form.save()
            messages.success(request, f'Product "{updated_product.name}" updated successfully!')
            return redirect('items_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'update_product.html', {'form': form, 'product': product})


@login_required
@user_passes_test(is_admin)
def delete_product(request, pk):
    """Delete product (Admin only)"""
    product = get_object_or_404(Product, product_id=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('items_list')
    
    return render(request, 'delete_product.html', {'product': product})


@login_required
def my_requests(request):
    """Display user's borrow requests"""
    requests = Borrow.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    context = {
        'requests': requests,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'my_requests.html', context)


@login_required
def my_borrowed_items(request):
    """Display user's currently borrowed items"""
    borrowed_items = Borrow.objects.filter(
        user=request.user,
        status='active'
    ).select_related('product').order_by('-borrow_date')
    
    context = {
        'borrowed_items': borrowed_items,
        'today': timezone.now().date(),
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'my_borrowed_items.html', context)


@login_required
def borrow_history(request):
    """Display user's complete borrow history"""
    history = Borrow.objects.filter(user=request.user).select_related('product').order_by('-created_at')
    
    context = {
        'history': history,
        'is_admin': request.user.role == 'admin',
    }
    
    return render(request, 'borrow_history.html', context)


@login_required
@user_passes_test(is_admin)
def admin_pending_requests(request):
    """Handle pending borrow requests (Admin only)"""
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        borrow = get_object_or_404(Borrow, borrow_id=request_id)
        
        if action == 'approve':
            borrow.status = 'active'
            borrow.product.status = 'borrowed'
            borrow.product.save()
            borrow.added_by = request.user
            borrow.save()
            
            # Create notification for user
            try:
                Notification.objects.create(
                    recipient_user=borrow.user,
                    related_user=request.user,
                    message=f"Your request for {borrow.product.name} has been approved!"
                )
            except Exception as e:
                print(f"Failed to create notification: {e}")
            
            messages.success(request, f'Request for "{borrow.product.name}" approved!')
            
        elif action == 'reject':
            borrow.status = 'rejected'
            borrow.added_by = request.user
            borrow.save()
            
            # Create notification for user
            try:
                Notification.objects.create(
                    recipient_user=borrow.user,
                    related_user=request.user,
                    message=f"Your request for {borrow.product.name} has been rejected."
                )
            except Exception as e:
                print(f"Failed to create notification: {e}")
            
            messages.success(request, f'Request for "{borrow.product.name}" rejected!')
        
        return redirect('admin_pending_requests')
    
    pending_requests = Borrow.objects.filter(status='pending').select_related('user', 'product').order_by('-created_at')
    
    context = {
        'pending_requests': pending_requests,
        'is_admin': True,
    }
    
    return render(request, 'admin_pending_requests.html', context)


@login_required
@user_passes_test(is_admin)
def admin_pending_users(request):
    """Handle pending user approvals (Admin only)"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, user_id=user_id)
        
        if action == 'approve':
            user.is_active = True
            user.save()
            
            # Create a notification for the approved user
            try:
                Notification.objects.create(
                    recipient_user=user,
                    message=f"Your account has been approved! You can now log in to the system."
                )
            except Exception as e:
                print(f"Failed to create notification: {e}")
            
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
    """Display all users (Admin only)"""
    users = User.objects.all().order_by('-date_created')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(firstname__icontains=search_query) |
            Q(lastname__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
        'is_admin': True,
    }
    
    return render(request, 'user_list.html', context)


@login_required
@user_passes_test(is_admin)
def add_user(request):
    """Add new user (Admin only)"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Admin-created users are active by default
            user.is_active = True
            user.save()
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'add_user.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def reports(request):
    """Generate system reports (Admin only)"""
    # Basic counts
    total_products = Product.objects.count()
    total_users = User.objects.filter(is_active=True).count()
    total_borrows = Borrow.objects.count()
    active_borrows = Borrow.objects.filter(status='active').count()
    
    # Overdue items
    overdue_items = Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).count()
    
    # Category statistics
    category_stats = Product.objects.values('category').annotate(
        count=Count('pk')
    ).order_by('-count')
    
    # Popular items
    popular_items = Product.objects.annotate(
        borrow_count=Count('borrow_history')
    ).order_by('-borrow_count')[:10]
    
    # Monthly statistics
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_borrows = Borrow.objects.filter(
        created_at__month=current_month,
        created_at__year=current_year
    ).count()
    
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_borrows': total_borrows,
        'active_borrows': active_borrows,
        'overdue_items': overdue_items,
        'category_stats': category_stats,
        'popular_items': popular_items,
        'monthly_borrows': monthly_borrows,
        'is_admin': True,
    }
    
    return render(request, 'reports.html', context)



@login_required
def user_profile(request, user_id=None):
    """Display and edit user profile"""
    if user_id:
        try:
            profile_user = get_object_or_404(User, user_id=user_id)
            # Only admins can view other users' profiles
            if profile_user != request.user and request.user.role != 'admin':
                messages.error(request, 'You can only view your own profile.')
                return redirect('user_profile')
        except:
            messages.error(request, 'User not found.')
            return redirect('user_list')
    else:
        profile_user = request.user

    # Base context
    context = {
        'profile_user': profile_user,
        'form': UserProfileForm(instance=profile_user) if profile_user == request.user else None,
        'is_admin': request.user.role == 'admin',
    }

    # Admin-specific data
    if profile_user.role == 'admin':
        admin_products = Product.objects.filter(created_by=profile_user).order_by('-created_at')
        products_added = admin_products.count()
        requests_processed = Borrow.objects.filter(added_by=profile_user).count()
        total_system_users = User.objects.filter(is_active=True).count()
        total_system_products = Product.objects.count()
        
        context.update({
            'admin_products': admin_products,
            'products_added': products_added,
            'requests_processed': requests_processed,
            'total_system_users': total_system_users,
            'total_system_products': total_system_products,
        })
    else:
        # Regular user statistics
        total_borrowed = Borrow.objects.filter(user=profile_user).count()
        currently_borrowed = Borrow.objects.filter(user=profile_user, status='active').count()
        returned_items = Borrow.objects.filter(user=profile_user, status='returned').count()
        pending_requests = Borrow.objects.filter(user=profile_user, status='pending').count()
        overdue_items = Borrow.objects.filter(
            user=profile_user,
            status='active',
            expected_return_date__lt=timezone.now().date()
        ).count()

        borrow_history = Borrow.objects.filter(
            user=profile_user
        ).select_related('product').order_by('-borrow_date')

        recent_requests = Borrow.objects.filter(
            user=profile_user
        ).select_related('product').order_by('-created_at')[:5]

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
            context['form'] = form
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'user_profile.html', context)


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


# Request management views
@login_required
@user_passes_test(is_admin)
def approve_request(request, request_id):
    """Approve a borrow request"""
    if request.method == 'POST':
        borrow = get_object_or_404(Borrow, borrow_id=request_id)
        borrow.status = 'active'
        borrow.product.status = 'borrowed'
        borrow.product.save()
        borrow.added_by = request.user
        borrow.save()
        
        # Create notification for user
        try:
            Notification.objects.create(
                recipient_user=borrow.user,
                related_user=request.user,
                message=f"Your request for {borrow.product.name} has been approved!"
            )
        except Exception:
            pass
        
        messages.success(request, f'Request for "{borrow.product.name}" approved!')
    
    return redirect('admin_pending_requests')


@login_required
@user_passes_test(is_admin)
def reject_request(request, request_id):
    """Reject a borrow request"""
    if request.method == 'POST':
        borrow = get_object_or_404(Borrow, borrow_id=request_id)
        borrow.status = 'rejected'
        borrow.added_by = request.user
        borrow.save()
        
        # Create notification for user
        try:
            Notification.objects.create(
                recipient_user=borrow.user,
                related_user=request.user,
                message=f"Your request for {borrow.product.name} has been rejected."
            )
        except Exception:
            pass
        
        messages.success(request, f'Request for "{borrow.product.name}" rejected!')
    
    return redirect('admin_pending_requests')


@login_required
def borrow_request(request, product_id):
    """Create a borrow request for a product"""
    product = get_object_or_404(Product, product_id=product_id)
    
    # Check if user already has a pending request for this item
    existing_request = Borrow.objects.filter(
        user=request.user,
        product=product,
        status__in=['pending', 'approved', 'active']
    ).exists()
    
    if existing_request:
        messages.error(request, 'You already have a pending or active request for this item.')
        return redirect('product_detail', pk=product_id)
    
    if product.status != 'available':
        messages.error(request, 'This item is not available for borrowing.')
        return redirect('product_detail', pk=product_id)
    
    if request.method == 'POST':
        # Create borrow request
        borrow = Borrow.objects.create(
            user=request.user,
            product=product,
            status='pending',
            borrow_date=timezone.now().date(),
            expected_return_date=timezone.now().date() + timedelta(days=7)
        )
        
        # Notify admins
        admin_users = User.objects.filter(role='admin', is_active=True)
        for admin in admin_users:
            try:
                Notification.objects.create(
                    recipient_user=admin,
                    related_user=request.user,
                    message=f"{request.user.username} requested to borrow {product.name}"
                )
            except Exception:
                pass
        
        messages.success(request, 'Borrow request submitted successfully!')
        return redirect('product_detail', pk=product_id)
    
    return redirect('product_detail', pk=product_id)


@login_required
def return_item(request, borrow_id):
    """Return a borrowed item"""
    borrow = get_object_or_404(Borrow, borrow_id=borrow_id, user=request.user)
    
    if request.method == 'POST':
        borrow.status = 'returned'
        borrow.actual_return_date = timezone.now().date()
        borrow.product.status = 'available'
        borrow.product.save()
        borrow.save()
        
        # Create loan history record
        try:
            LoanHistory.objects.create(
                user=borrow.user,
                product=borrow.product,
                borrow_date=borrow.borrow_date,
                return_date=borrow.actual_return_date,
                status='returned'
            )
        except Exception as e:
            print(f"Failed to create loan history: {e}")
        
        messages.success(request, f'Successfully returned "{borrow.product.name}"!')
    
    return redirect('my_borrowed_items')


@login_required
def extend_request(request, borrow_id):
    """Request extension for a borrowed item"""
    borrow = get_object_or_404(Borrow, borrow_id=borrow_id, user=request.user)
    
    if request.method == 'POST':
        # Extend by 7 days (configurable)
        if borrow.expected_return_date and borrow.status == 'active':
            old_date = borrow.expected_return_date
            borrow.expected_return_date += timedelta(days=7)
            borrow.save()
            
            # Notify admins about extension
            admin_users = User.objects.filter(role='admin', is_active=True)
            for admin in admin_users:
                try:
                    Notification.objects.create(
                        recipient_user=admin,
                        related_user=request.user,
                        message=f"{request.user.username} extended return date for {borrow.product.name} to {borrow.expected_return_date}"
                    )
                except Exception:
                    pass
            
            messages.success(request, f'Extension granted for "{borrow.product.name}" until {borrow.expected_return_date}!')
        else:
            messages.error(request, 'Unable to extend this item.')
    
    return redirect('my_borrowed_items')


# User management views
@login_required
@user_passes_test(is_admin)
def activate_user(request, user_id):
    """Activate a user account"""
    if request.method == 'POST':
        user = get_object_or_404(User, user_id=user_id)
        user.is_active = True
        user.save()
        
        # Notify user of activation
        try:
            Notification.objects.create(
                recipient_user=user,
                message="Your account has been activated! You can now log in to the system."
            )
        except Exception:
            pass
            
        messages.success(request, f'User "{user.username}" has been activated!')
    
    return redirect('user_list')


@login_required
@user_passes_test(is_admin)
def deactivate_user(request, user_id):
    """Deactivate a user account"""
    if request.method == 'POST':
        user = get_object_or_404(User, user_id=user_id)
        if user != request.user:  # Don't allow deactivating self
            user.is_active = False
            user.save()
            
            # Notify user of deactivation
            try:
                Notification.objects.create(
                    recipient_user=user,
                    message="Your account has been deactivated. Please contact an administrator if you believe this is an error."
                )
            except Exception:
                pass
                
            messages.success(request, f'User "{user.username}" has been deactivated!')
        else:
            messages.error(request, 'You cannot deactivate your own account!')
    
    return redirect('user_list')


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete a user account"""
    if request.method == 'POST':
        user = get_object_or_404(User, user_id=user_id)
        if user != request.user:  # Don't allow deleting self
            username = user.username
            user.delete()
            messages.success(request, f'User "{username}" has been deleted!')
        else:
            messages.error(request, 'You cannot delete your own account!')
    
    return redirect('user_list')


# Export and reporting views
@login_required
@user_passes_test(is_admin)
def export_csv(request):
    """Export data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'
    
    writer = csv.writer(response)
    
    # Determine what to export based on GET parameters
    export_type = request.GET.get('type', 'products')
    
    if export_type == 'products':
        writer.writerow(['Product ID', 'Name', 'Category', 'Brand', 'Status', 'Location', 'Created By', 'Created Date'])
        
        products = Product.objects.select_related('created_by').all()
        for product in products:
            writer.writerow([
                product.product_id,
                product.name,
                product.category,
                product.brand,
                product.status,
                product.location,
                product.created_by.username if product.created_by else 'N/A',
                product.created_at.strftime('%Y-%m-%d')
            ])
    
    elif export_type == 'users':
        writer.writerow(['User ID', 'Username', 'Full Name', 'Email', 'Role', 'Status', 'Date Created'])
        
        users = User.objects.all()
        for user in users:
            writer.writerow([
                user.user_id,
                user.username,
                user.get_full_name(),
                user.email,
                user.role,
                'Active' if user.is_active else 'Inactive',
                user.date_created.strftime('%Y-%m-%d')
            ])
    
    elif export_type == 'borrows':
        writer.writerow(['Borrow ID', 'User', 'Product', 'Status', 'Borrow Date', 'Expected Return', 'Actual Return', 'Created Date'])
        
        borrows = Borrow.objects.select_related('user', 'product').all()
        for borrow in borrows:
            writer.writerow([
                borrow.borrow_id,
                borrow.user.username,
                borrow.product.name,
                borrow.status,
                borrow.borrow_date.strftime('%Y-%m-%d') if borrow.borrow_date else '',
                borrow.expected_return_date.strftime('%Y-%m-%d') if borrow.expected_return_date else '',
                borrow.actual_return_date.strftime('%Y-%m-%d') if borrow.actual_return_date else '',
                borrow.created_at.strftime('%Y-%m-%d %H:%M')
            ])
    
    return response


@login_required
@user_passes_test(is_admin)
def export_pdf(request):
    """Export data as PDF (placeholder for future implementation)"""
    messages.info(request, 'PDF export feature is under development. Please use CSV export for now.')
    return redirect('reports')


@login_required
@user_passes_test(is_admin)
def print_report(request):
    """Print report (placeholder for future implementation)"""
    messages.info(request, 'Print report feature is under development.')
    return redirect('reports')


# API endpoints
@login_required
def search_products_api(request):
    """API endpoint for product search"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'results': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__icontains=query) |
        Q(brand__icontains=query)
    )[:10]
    
    results = [{
        'id': p.product_id,
        'name': p.name,
        'category': p.category,
        'brand': p.brand,
        'status': p.status,
        'location': p.location
    } for p in products]
    
    return JsonResponse({'results': results})


@login_required
@user_passes_test(is_admin)
def update_product_status_api(request, pk):
    """API endpoint to update product status"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, product_id=pk)
            new_status = request.POST.get('status')
            
            # Validate status
            valid_statuses = [choice[0] for choice in Product.PRODUCT_STATUS]
            if new_status not in valid_statuses:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid status'
                })
            
            # Check if status change is allowed
            if new_status == 'borrowed' and product.status != 'available':
                return JsonResponse({
                    'success': False,
                    'message': 'Only available items can be marked as borrowed'
                })
            
            product.status = new_status
            product.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Status updated to {product.get_status_display()}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Error updating status: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# Notification management
@login_required
def get_notifications_api(request):
    """API endpoint to get user notifications"""
    notifications = Notification.objects.filter(
        recipient_user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]
    
    results = [{
        'id': n.id,
        'message': n.message,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'related_user': n.related_user.username if n.related_user else None
    } for n in notifications]
    
    return JsonResponse({
        'notifications': results,
        'count': notifications.count()
    })


@login_required
def mark_notification_read_api(request, notification_id):
    """API endpoint to mark notification as read"""
    if request.method == 'POST':
        try:
            notification = get_object_or_404(
                Notification, 
                id=notification_id, 
                recipient_user=request.user
            )
            notification.is_read = True
            notification.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


# Utility functions
def get_overdue_items():
    """Get all overdue items"""
    return Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).select_related('user', 'product')


def send_overdue_notifications():
    """Send notifications for overdue items (can be called from management command)"""
    overdue_items = get_overdue_items()
    
    for borrow in overdue_items:
        # Check if notification already sent today
        today = timezone.now().date()
        existing_notification = Notification.objects.filter(
            recipient_user=borrow.user,
            message__contains=f"overdue: {borrow.product.name}",
            created_at__date=today
        ).exists()
        
        if not existing_notification:
            try:
                Notification.objects.create(
                    recipient_user=borrow.user,
                    message=f"Item overdue: {borrow.product.name} was due on {borrow.expected_return_date}"
                )
            except Exception as e:
                print(f"Failed to create overdue notification: {e}")


def get_system_stats():
    """Get system-wide statistics"""
    return {
        'total_products': Product.objects.count(),
        'available_products': Product.objects.filter(status='available').count(),
        'borrowed_products': Product.objects.filter(status='borrowed').count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'pending_users': User.objects.filter(is_active=False).count(),
        'active_borrows': Borrow.objects.filter(status='active').count(),
        'overdue_items': get_overdue_items().count(),
        'pending_requests': Borrow.objects.filter(status='pending').count(),
    }