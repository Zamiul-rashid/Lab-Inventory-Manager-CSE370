# views.py - Updated Lab Inventory Management System
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Product, Borrow, Notification, LoanHistory
from .forms import UserRegistrationForm, CustomLoginForm, ProductForm, BorrowForm, UserProfileForm, UserSearchForm, ProductSearchForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.template.defaultfilters import timesince
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
    borrowed_products = Borrow.objects.filter(status='active').count()  # Count active borrows, not borrowed products
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
    
    # Get recent borrow activity for the activity feed (admin actions only)
    recent_borrows = Borrow.objects.filter(
        status__in=['approved', 'rejected']
    ).select_related('user', 'product', 'added_by').order_by('-created_at')[:15]
    
    # Get recent product additions (limited)
    recent_products = Product.objects.select_related('created_by').order_by('-created_at')[:3]
    
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
        'recent_products': recent_products,
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
                        notification_type='user_registration',
                        priority='medium',
                        title=f"New User Registration: {user.username}",
                        message=f"New user {user.username} ({user.get_full_name()}) has registered and is waiting for approval.\n\nUser Details:\n- Username: {user.username}\n- Email: {user.email}\n- User ID: {user.user_id}\n\nPlease review and approve the user registration."
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
    my_borrowed = Borrow.objects.filter(
        user=user, 
        status='active', 
        actual_return_date__isnull=True
    ).count()
    pending_requests = Borrow.objects.filter(status='pending').count()
    total_categories = Product.objects.values('category').distinct().count()
    
    # Get recent activity with optimized queries
    recent_requests = Borrow.objects.select_related('product').filter(user=user).order_by('-created_at')[:5]
    currently_borrowed = Borrow.objects.select_related('product').filter(
        user=user, 
        status='active',
        actual_return_date__isnull=True  # Ensure item hasn't been returned yet
    )[:5]
    
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
    """Display user's returned items history"""
    # Only show returned items
    history = Borrow.objects.filter(
        user=request.user,
        status='returned'
    ).select_related('product')
    
    # Order by creation date (newest first)
    history = history.order_by('-created_at')
    
    context = {
        'history': history,
        'history_items': history,  # Template expects this name
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
            
            messages.success(request, f'Request for "{borrow.product.name}" approved!')
            
        elif action == 'reject':
            borrow.status = 'rejected'
            borrow.added_by = request.user
            borrow.save()
            
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
        
        try:
            # Use Django's primary key (id) instead of custom user_id field
            user = User.objects.get(pk=user_id)
            
            if action == 'approve':
                user.is_active = True
                user.save()
                
                messages.success(request, f'User {user.username} ({user.get_full_name()}) has been approved!')
                
            elif action == 'reject':
                username = user.username
                full_name = user.get_full_name()
                user.delete()
                messages.success(request, f'User {username} ({full_name}) has been rejected and removed.')
        
        except User.DoesNotExist:
            messages.error(request, f'User with ID {user_id} not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
        
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
    total_items = Product.objects.count()
    available_items = Product.objects.filter(status='available').count()
    borrowed_items = Borrow.objects.filter(status='active').count()  # Count of active borrows, not products
    total_users = User.objects.filter(is_active=True).count()
    total_borrows = Borrow.objects.count()
    active_borrows = Borrow.objects.filter(status='active').count()
    
    # Overdue items
    overdue_items = Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).count()
    
    # Category statistics with percentage calculation
    total_products_for_category = Product.objects.count()
    category_data = []
    category_stats = Product.objects.values('category').annotate(
        count=Count('pk')
    ).order_by('-count')
    
    for category in category_stats:
        # Ensure category name is not None and handle division by zero
        category_name = category['category'] if category['category'] is not None else 'Uncategorized'
        category_count = category['count'] if category['count'] is not None else 0
        
        percentage = (category_count / total_products_for_category * 100) if total_products_for_category > 0 else 0
        category_data.append({
            'name': category_name,
            'count': category_count,
            'percentage': round(percentage, 1) if percentage is not None else 0
        })
    
    # Top borrowers
    top_borrowers = Borrow.objects.values(
        'user__username', 'user__firstname', 'user__lastname', 'user__email'
    ).annotate(count=Count('user')).order_by('-count')[:5]
    
    # Format top borrowers for template
    formatted_top_borrowers = []
    for borrower in top_borrowers:
        full_name = f"{borrower['user__firstname']} {borrower['user__lastname']}".strip()
        formatted_top_borrowers.append({
            'user__username': borrower['user__username'],
            'user__get_full_name': full_name if full_name else borrower['user__username'],
            'user__email': borrower['user__email'],
            'count': borrower['count']
        })
    
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
    
    monthly_returns = Borrow.objects.filter(
        actual_return_date__month=current_month,
        actual_return_date__year=current_year,
        status='returned'
    ).count()
    
    monthly_requests = Borrow.objects.filter(
        created_at__month=current_month,
        created_at__year=current_year
    ).count()
    
    # System health metrics
    total_active_borrows = Borrow.objects.filter(status='active').count()
    utilization_rate = round((borrowed_items / total_items * 100), 1) if total_items > 0 else 0
    
    # Average borrow time calculation
    returned_borrows = Borrow.objects.filter(status='returned', actual_return_date__isnull=False)
    if returned_borrows.exists():
        total_days = 0
        count = 0
        for borrow in returned_borrows:
            if borrow.actual_return_date and borrow.borrow_date:
                # Convert both to date objects to avoid datetime.date vs datetime.datetime issues
                if hasattr(borrow.actual_return_date, 'date'):
                    actual_date = borrow.actual_return_date.date()
                else:
                    actual_date = borrow.actual_return_date
                    
                if hasattr(borrow.borrow_date, 'date'):
                    borrow_date = borrow.borrow_date.date()
                else:
                    borrow_date = borrow.borrow_date
                    
                days = (actual_date - borrow_date).days
                total_days += days
                count += 1
        avg_borrow_time = round(total_days / count, 1) if count > 0 else 0
    else:
        avg_borrow_time = 0
    
    # On-time return rate
    total_returns = Borrow.objects.filter(status='returned').count()
    ontime_returns = Borrow.objects.filter(
        status='returned',
        actual_return_date__lte=F('expected_return_date')
    ).count()
    ontime_rate = round((ontime_returns / total_returns * 100), 1) if total_returns > 0 else 0
    
    # Recent activity (admin actions only)
    recent_activity = Borrow.objects.filter(
        status__in=['approved', 'rejected']
    ).select_related('user', 'product').order_by('-created_at')[:10]
    
    # Recent product additions
    recent_products = Product.objects.select_related('created_by').order_by('-created_at')[:5]
    
    # Current borrowers with product details
    current_borrowers = Borrow.objects.filter(
        status='active'
    ).select_related('user', 'product').order_by('-borrow_date')
    
    # Add overdue status to current borrowers
    current_borrowers_list = []
    for borrow in current_borrowers:
        is_overdue = borrow.expected_return_date < timezone.now().date()
        current_borrowers_list.append({
            'user_full_name': borrow.user.get_full_name() or borrow.user.username,
            'user_username': borrow.user.username,
            'user_id': borrow.user.user_id,
            'product_name': borrow.product.name,
            'product_category': borrow.product.category,
            'borrow_date': borrow.borrow_date,
            'expected_return_date': borrow.expected_return_date,
            'is_overdue': is_overdue,
            'status': 'overdue' if is_overdue else 'active'
        })
    
    # Borrowing overview data
    items_to_return = Borrow.objects.filter(status='active').count()
    overdue_products = Borrow.objects.filter(
        status='active',
        expected_return_date__lt=timezone.now().date()
    ).select_related('product')
    
    overdue_product_list = []
    for borrow in overdue_products:
        overdue_product_list.append({
            'product_name': borrow.product.name,
            'product_category': borrow.product.category,
            'borrower_name': borrow.user.get_full_name() or borrow.user.username,
            'expected_return_date': borrow.expected_return_date,
            'days_overdue': (timezone.now().date() - borrow.expected_return_date).days
        })

    context = {
        'total_items': total_items,
        'available_items': available_items,
        'borrowed_items': borrowed_items,
        'overdue_items': overdue_items,
        'total_users': total_users,
        'total_borrows': total_borrows,
        'active_borrows': active_borrows,
        'category_data': category_data,
        'top_borrowers': formatted_top_borrowers,
        'popular_items': popular_items,
        'monthly_borrows': monthly_borrows,
        'monthly_returns': monthly_returns,
        'monthly_requests': monthly_requests,
        'utilization_rate': utilization_rate,
        'avg_borrow_time': avg_borrow_time,
        'ontime_rate': ontime_rate,
        'recent_activity': recent_activity,
        'recent_products': recent_products,
        'current_borrowers': current_borrowers_list,
        'items_to_return': items_to_return,
        'overdue_product_list': overdue_product_list,
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
        
        # Update product status and decrement available quantity
        borrow.product.status = 'borrowed'
        if borrow.product.quantity_available > 0:
            borrow.product.quantity_available -= 1
        borrow.product.save()
        
        borrow.added_by = request.user
        borrow.save()
        
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
        
        # Update product status and increment available quantity
        borrow.product.status = 'available'
        borrow.product.quantity_available += 1
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
        
        # Redirect back to the referring page if it's the history page, otherwise to my_borrowed_items
        referer = request.META.get('HTTP_REFERER', '')
        if 'history' in referer:
            return redirect('borrow_history')
        else:
            return redirect('my_borrowed_items')
    
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

@login_required
def get_notifications_api(request):
    """API endpoint to get user notifications"""
    if request.user.role == 'admin':
        # Admin gets all types of notifications
        notifications = Notification.objects.filter(
            recipient_user=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    else:
        # Regular users get return reminders and overdue alerts
        notifications = Notification.objects.filter(
            recipient_user=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    
    results = []
    for n in notifications:
        notification_type = 'info'
        icon = 'fas fa-info-circle'
        
        # Determine notification type and icon
        if 'registered' in n.message.lower():
            notification_type = 'info'
            icon = 'fas fa-user-plus'
        elif 'requested' in n.message.lower():
            notification_type = 'warning'
            icon = 'fas fa-hand-holding'
        elif 'overdue' in n.message.lower():
            notification_type = 'danger'
            icon = 'fas fa-exclamation-triangle'
        elif 'approved' in n.message.lower():
            notification_type = 'success'
            icon = 'fas fa-check-circle'
        
        results.append({
            'id': n.notification_id,
            'message': n.message,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': timesince(n.created_at),
            'type': notification_type,
            'icon': icon,
            'related_user': n.related_user.username if n.related_user else None
        })
    
    return JsonResponse({
        'notifications': results,
        'count': len(results)
    })

@login_required
def mark_notification_read_api(request, notification_id):
    """Mark notification as read"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(
                notification_id=notification_id,
                recipient_user=request.user
            )
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
def notifications_view(request):
    """Display notifications for the current user"""
    # Check if user wants to see all notifications or just unread
    show_all = request.GET.get('show_all', 'false').lower() == 'true'
    
    if show_all:
        notifications = Notification.objects.filter(
            recipient_user=request.user
        ).select_related('related_user', 'related_borrow__product').order_by('-created_at')
    else:
        # By default, only show unread notifications
        notifications = Notification.objects.filter(
            recipient_user=request.user,
            is_read=False
        ).select_related('related_user', 'related_borrow__product').order_by('-created_at')
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read') == 'true':
        notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(notifications, 20)  # Show 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts
    total_notifications = Notification.objects.filter(recipient_user=request.user).count()
    unread_count = Notification.objects.filter(recipient_user=request.user, is_read=False).count()
    read_count = total_notifications - unread_count
    
    context = {
        'notifications': page_obj,
        'unread_count': unread_count,
        'total_count': total_notifications,
        'read_count': read_count,
        'show_all': show_all,
        'current_showing': notifications.count(),
    }
    
    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.objects.get(
            notification_id=notification_id,
            recipient_user=request.user
        )
        notification.mark_as_read()
        messages.success(request, 'Notification marked as read.')
    except Notification.DoesNotExist:
        messages.error(request, 'Notification not found.')
    
    return redirect('notifications')


@login_required
def get_notifications_count(request):
    """Get unread notifications count for the current user"""
    unread_count = Notification.objects.filter(
        recipient_user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': unread_count})


@login_required
def get_recent_notifications(request):
    """Get recent notifications for dropdown display"""
    notifications = Notification.objects.filter(
        recipient_user=request.user
    ).select_related('related_user', 'related_borrow__product').order_by('-created_at')[:10]
    
    results = []
    for n in notifications:
        # Set notification style based on type and priority
        if n.notification_type == 'overdue_alert':
            notification_type = 'danger'
            icon = 'fas fa-exclamation-triangle'
        elif n.notification_type == 'return_reminder':
            notification_type = 'warning'
            icon = 'fas fa-clock'
        elif n.notification_type == 'borrow_approved':
            notification_type = 'success'
            icon = 'fas fa-check-circle'
        elif n.notification_type == 'borrow_request':
            notification_type = 'info'
            icon = 'fas fa-hand-holding'
        elif n.notification_type == 'user_registration':
            notification_type = 'primary'
            icon = 'fas fa-user-plus'
        else:
            notification_type = 'secondary'
            icon = 'fas fa-bell'
        
        results.append({
            'id': n.notification_id,
            'title': n.title,
            'message': n.message[:100] + '...' if len(n.message) > 100 else n.message,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': timesince(n.created_at),
            'type': notification_type,
            'icon': icon,
            'is_read': n.is_read,
            'priority': n.priority,
            'related_user': n.related_user.username if n.related_user else None
        })
    
    return JsonResponse({
        'notifications': results,
        'count': len(results)
    })


def get_notification_action_url(notification):
    """
    Generate the appropriate URL for notification action based on notification type
    """
    if notification.notification_type == 'user_registration':
        # Take admin to pending users page
        return '/manage/pending-users/'
    
    elif notification.notification_type == 'return_reminder':
        # Take user to their borrowed items to return
        return '/my-borrowed/'
    
    elif notification.notification_type == 'overdue_alert':
        # Take user to their borrowed items
        return '/my-borrowed/'
    
    elif notification.related_borrow:
        # If there's a related borrow, go to product detail
        return f'/items/{notification.related_borrow.product.product_id}/'
    
    else:
        # Default: go to dashboard
        if notification.recipient_user.role == 'admin':
            return '/admin-dashboard/'
        else:
            return '/dashboard/'


@login_required
def mark_notification_read_and_redirect(request, notification_id):
    """Mark notification as read and redirect to appropriate action page"""
    try:
        notification = Notification.objects.get(
            notification_id=notification_id,
            recipient_user=request.user
        )
        
        # Get the action URL before marking as read
        action_url = get_notification_action_url(notification)
        
        # Mark as read
        notification.mark_as_read()
        
        # Add a success message
        messages.success(request, f'Notification "{notification.title}" marked as read.')
        
        # Redirect to action URL
        return redirect(action_url)
        
    except Notification.DoesNotExist:
        messages.error(request, 'Notification not found.')
        return redirect('notifications')
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@user_passes_test(is_admin)
def admin_manage_returns(request):
    """
    Admin view to manage item returns - mark items as returned when users return them in person
    """
    if request.method == 'POST':
        borrow_id = request.POST.get('borrow_id')
        action = request.POST.get('action')
        
        try:
            borrow = get_object_or_404(Borrow, borrow_id=borrow_id)
            
            if action == 'mark_returned':
                if borrow.status in ['active', 'overdue']:
                    # Mark borrow as returned
                    borrow.status = 'returned'
                    borrow.actual_return_date = timezone.now().date()
                    borrow.save()
                    
                    # Update product status to available
                    if borrow.product:
                        borrow.product.status = 'available'
                        borrow.product.save()
                    
                    messages.success(request, f"Successfully marked '{borrow.product.name}' as returned for user {borrow.user.get_full_name()}.")
                else:
                    messages.error(request, f"Cannot mark this item as returned. Current status: {borrow.get_status_display()}")
            
            elif action == 'mark_active':
                if borrow.status == 'returned':
                    borrow.status = 'active'
                    borrow.actual_return_date = None
                    borrow.save()
                    
                    # Update product status to borrowed
                    if borrow.product:
                        borrow.product.status = 'borrowed'
                        borrow.product.save()
                    
                    messages.success(request, f"Successfully reactivated borrow for '{borrow.product.name}'.")
                else:
                    messages.error(request, "Can only reactivate returned items.")
        
        except Borrow.DoesNotExist:
            messages.error(request, "Borrow record not found.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        
        return redirect('admin_manage_returns')
    
    # Get all active and overdue borrows for admin to manage
    active_borrows = Borrow.objects.filter(
        status__in=['active', 'overdue']
    ).select_related('user', 'product').order_by('-created_at')
    
    # Get recently returned items (last 30 days) for reference
    recent_returns = Borrow.objects.filter(
        status='returned',
        actual_return_date__gte=timezone.now().date() - timedelta(days=30)
    ).select_related('user', 'product').order_by('-actual_return_date')[:20]
    
    context = {
        'active_borrows': active_borrows,
        'recent_returns': recent_returns,
        'today': timezone.now().date(),
    }
    
    return render(request, 'admin_manage_returns.html', context)