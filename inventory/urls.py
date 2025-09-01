# inventory/urls.py
from django.urls import path
from . import views
from django.shortcuts import redirect

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

urlpatterns = [
    # Home redirect logic
    path('', home_redirect, name='home'),
    
    # Authentication  
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    
    # Main dashboard (different URL)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Product/Item management
    path('items/', views.items_list, name='items_list'),
    path('items/<int:pk>/', views.product_detail, name='product_detail'),
    path('add-item/', views.add_item, name='add_item'),
    path('update-product/<int:pk>/', views.update_product, name='update_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    
    # User borrow management
    path('my-requests/', views.my_requests, name='my_requests'),
    path('my-borrowed/', views.my_borrowed_items, name='my_borrowed_items'),
    path('history/', views.borrow_history, name='borrow_history'),
    
    # Admin functions
    path('manage/pending-requests/', views.admin_pending_requests, name='admin_pending_requests'),
    path('manage/pending-users/', views.admin_pending_users, name='admin_pending_users'),
    path('manage/users/', views.user_list, name='user_list'),
    path('manage/add-user/', views.add_user, name='add_user'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/', views.reports, name='reports'),
    
    # Request management
    path('approve-request/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject-request/<int:request_id>/', views.reject_request, name='reject_request'),
    path('borrow-request/<int:product_id>/', views.borrow_request, name='borrow_request'),
    path('return-item/<int:borrow_id>/', views.return_item, name='return_item'),
    path('extend-request/<int:borrow_id>/', views.extend_request, name='extend_request'),
    
    # User management
    path('activate-user/<int:user_id>/', views.activate_user, name='activate_user'),
    path('deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    
    # Export functions
    path('export-csv/', views.export_csv, name='export_csv'),
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    path('print-report/', views.print_report, name='print_report'),
    
    # User profiles
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/<int:user_id>/', views.user_profile, name='user_profile_detail'),
    path('change-password/', views.change_password, name='change_password'),
    
    # API endpoints
    path('api/search-products/', views.search_products_api, name='search_products_api'),
    path('api/update-product-status/<int:pk>/', views.update_product_status_api, name='update_product_status_api'),
]