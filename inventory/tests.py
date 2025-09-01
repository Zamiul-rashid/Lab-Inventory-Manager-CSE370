# tests.py - Comprehensive Django Testing Examples
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, Borrow, Notification
from .forms import UserRegistrationForm, ProductForm, BorrowForm

User = get_user_model()

class UserModelTest(TestCase):
    """Test cases for the User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'firstname': 'Test',
            'lastname': 'User',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
    def test_user_creation(self):
        """Test user creation with user_id generation"""
        user = User.objects.create_user(**self.user_data)
        self.assertTrue(user.user_id)
        self.assertEqual(len(user.user_id), 5)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.get_full_name(), 'Test User')
        
    def test_user_id_uniqueness(self):
        """Test that user_id is unique"""
        user1 = User.objects.create_user(**self.user_data)
        
        self.user_data['username'] = 'testuser2'
        self.user_data['email'] = 'test2@example.com'
        user2 = User.objects.create_user(**self.user_data)
        
        self.assertNotEqual(user1.user_id, user2.user_id)
        
    def test_user_str_representation(self):
        """Test the string representation of User"""
        user = User.objects.create_user(**self.user_data)
        expected = f"testuser (ID: {user.user_id})"
        self.assertEqual(str(user), expected)
        
    def test_get_borrow_history(self):
        """Test getting user's borrow history"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_borrow_history().count(), 0)

class ProductModelTest(TestCase):
    """Test cases for the Product model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            firstname='Admin',
            lastname='User',
            role='admin'
        )
        
        self.product_data = {
            'name': 'Test Microscope',
            'description': 'High-quality microscope for lab use',
            'category': 'Laboratory Equipment',
            'brand': 'TestBrand',
            'quantity_available': 5,
            'current_location': 'Lab Room 101',
            'status': 'available',
            'created_by': self.user
        }
        
    def test_product_creation(self):
        """Test product creation"""
        product = Product.objects.create(**self.product_data)
        self.assertEqual(product.name, 'Test Microscope')
        self.assertEqual(product.status, 'available')
        self.assertEqual(product.quantity_available, 5)
        
    def test_product_str_representation(self):
        """Test product string representation"""
        product = Product.objects.create(**self.product_data)
        expected = "Test Microscope (Laboratory Equipment)"
        self.assertEqual(str(product), expected)

class BorrowModelTest(TestCase):
    """Test cases for the Borrow model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='borrower',
            email='borrower@example.com',
            password='borrowpass123',
            firstname='Borrower',
            lastname='User'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            firstname='Admin',
            lastname='User',
            role='admin'
        )
        
        self.product = Product.objects.create(
            name='Test Equipment',
            category='Test Category',
            quantity_available=1,
            created_by=self.admin
        )
        
    def test_borrow_creation(self):
        """Test borrow record creation"""
        expected_return = timezone.now().date() + timedelta(days=7)
        borrow = Borrow.objects.create(
            user=self.user,
            product=self.product,
            expected_return_date=expected_return
        )
        
        self.assertEqual(borrow.status, 'pending')
        self.assertEqual(borrow.user, self.user)
        self.assertEqual(borrow.product, self.product)
        
    def test_is_overdue_property(self):
        """Test the is_overdue property"""
        # Create overdue borrow
        past_date = timezone.now().date() - timedelta(days=1)
        overdue_borrow = Borrow.objects.create(
            user=self.user,
            product=self.product,
            expected_return_date=past_date,
            status='active'
        )
        
        # Create non-overdue borrow
        future_date = timezone.now().date() + timedelta(days=7)
        normal_borrow = Borrow.objects.create(
            user=self.user,
            product=self.product,
            expected_return_date=future_date,
            status='active'
        )
        
        self.assertTrue(overdue_borrow.is_overdue)
        self.assertFalse(normal_borrow.is_overdue)

class ViewTest(TestCase):
    """Test cases for views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            firstname='Test',
            lastname='User'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            firstname='Admin',
            lastname='User',
            role='admin'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            category='Test Category',
            quantity_available=1,
            created_by=self.admin
        )
        
    def test_login_required_views(self):
        """Test that login is required for protected views"""
        protected_urls = [
            reverse('dashboard'),
            reverse('items_list'),
            reverse('user_profile'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'/login/?next={url}')
            
    def test_dashboard_view(self):
        """Test dashboard view for logged-in user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Overview')
        self.assertContains(response, 'Test User')
        
    def test_admin_required_views(self):
        """Test that admin role is required for admin views"""
        self.client.login(username='testuser', password='testpass123')
        
        admin_urls = [
            reverse('add_item'),
            reverse('admin_pending_users'),
            reverse('reports'),
        ]
        
        for url in admin_urls:
            response = self.client.get(url)
            # Should redirect to dashboard with error
            self.assertRedirects(response, reverse('dashboard'))
            
    def test_admin_views_for_admin(self):
        """Test that admin can access admin views"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get(reverse('add_item'))
        self.assertEqual(response.status_code, 200)
        
    def test_product_detail_view(self):
        """Test product detail view"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('product_detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        
    def test_user_registration(self):
        """Test user registration"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'firstname': 'New',
            'lastname': 'User',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'role': 'regular_user'
        })
        
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Check that new user is inactive by default
        new_user = User.objects.get(username='newuser')
        self.assertFalse(new_user.is_active)

class FormTest(TestCase):
    """Test cases for forms"""
    
    def test_user_registration_form_valid(self):
        """Test valid user registration form"""
        form_data = {
            'username': 'testuser',
            'firstname': 'Test',
            'lastname': 'User',
            'email': 'test@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'role': 'regular_user'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_user_registration_form_duplicate_email(self):
        """Test form validation for duplicate email"""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='test@example.com',
            password='pass123'
        )
        
        form_data = {
            'username': 'newuser',
            'firstname': 'New',
            'lastname': 'User',
            'email': 'test@example.com',  # Duplicate email
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'role': 'regular_user'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_product_form_valid(self):
        """Test valid product form"""
        form_data = {
            'name': 'Test Product',
            'description': 'A test product',
            'category': 'Test Category',
            'brand': 'Test Brand',
            'quantity_available': 5,
            'current_location': 'Lab A',
            'status': 'available',
            'notes': 'Some notes'
        }
        
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_product_form_negative_quantity(self):
        """Test product form with negative quantity"""
        form_data = {
            'name': 'Test Product',
            'category': 'Test Category',
            'quantity_available': -1,  # Invalid
            'status': 'available'
        }
        
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity_available', form.errors)
        
    def test_borrow_form_valid(self):
        """Test valid borrow form"""
        future_date = timezone.now().date() + timedelta(days=7)
        form_data = {
            'expected_return_date': future_date,
            'notes': 'Need for project'
        }
        
        form = BorrowForm(data=form_data)
        self.assertTrue(form.is_valid())

class APITest(TestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )
        
        for i in range(3):
            Product.objects.create(
                name=f'Product {i}',
                category='Category A',
                created_by=self.admin
            )
            
    def test_search_products_api(self):
        """Test product search API"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('search_products_api'), {'q': 'Product'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 3)
        
    def test_search_products_api_unauthorized(self):
        """Test product search API without login"""
        response = self.client.get(reverse('search_products_api'), {'q': 'Product'})
        self.assertRedirects(response, '/login/?next=/api/search-products/')

class IntegrationTest(TestCase):
    """Integration tests for complete workflows"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            firstname='Admin',
            lastname='User',
            role='admin',
            is_active=True
        )
        
        # Create regular user
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123',
            firstname='Regular',
            lastname='User',
            role='regular_user',
            is_active=True
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Lab Equipment',
            category='Equipment',
            quantity_available=1,
            created_by=self.admin
        )
        
    def test_complete_borrow_workflow(self):
        """Test complete borrow request workflow"""
        
        # Step 1: User logs in
        login_response = self.client.login(username='user', password='userpass123')
        self.assertTrue(login_response)
        
        # Step 2: User views product
        product_url = reverse('product_detail', kwargs={'pk': self.product.pk})
        product_response = self.client.get(product_url)
        self.assertEqual(product_response.status_code, 200)
        
        # Step 3: User submits borrow request
        future_date = timezone.now().date() + timedelta(days=7)
        borrow_response = self.client.post(product_url, {
            'expected_return_date': future_date,
            'notes': 'Need for experiment'
        })
        
        # Should redirect back to product page
        self.assertRedirects(borrow_response, product_url)
        
        # Check that borrow request was created
        borrow = Borrow.objects.get(user=self.user, product=self.product)
        self.assertEqual(borrow.status, 'pending')
        
        # Step 4: Admin logs in and approves request
        self.client.login(username='admin', password='adminpass123')
        
        # Admin views pending requests
        pending_url = reverse('admin_pending_requests')
        pending_response = self.client.get(pending_url)
        self.assertEqual(pending_response.status_code, 200)
        
        # Admin approves the request
        approve_response = self.client.post(pending_url, {
            'request_id': borrow.borrow_id,
            'action': 'approve'
        })
        
        # Check that request was approved
        borrow.refresh_from_db()
        self.assertEqual(borrow.status, 'active')
        
        # Check that product status changed
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'borrowed')
        
        # Check that notification was created
        notification = Notification.objects.get(recipient_user=self.user)
        self.assertIn('approved', notification.message.lower())

# Run tests with:
# python manage.py test
# python manage.py test inventory.tests.UserModelTest
# python manage.py test inventory.tests.UserModelTest.test_user_creation
