# Lab Inventory Manager - Setup and Run Guide

## 🚀 How to Run the Lab Inventory Manager Project

### Prerequisites
- Python 3.8+ (you have Python 3.10.12 ✅)
- MySQL/XAMPP (for database)
- Git (for version control)

### Step 1: Install Required Dependencies

First, install Django and other required packages:

```bash
# Install Django and MySQL client
python3 -m pip install Django==4.2.23
python3 -m pip install mysqlclient
python3 -m pip install python-decouple

# Or install all at once
python3 -m pip install Django==4.2.23 mysqlclient python-decouple
```

### Step 2: Database Setup

#### Option A: Using XAMPP (Recommended for development)
1. Start XAMPP Control Panel
2. Start Apache and MySQL services
3. Open phpMyAdmin (http://localhost/phpmyadmin)
4. Create a new database named `lit_database`

#### Option B: Using MySQL directly
```bash
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE lit_database;
```

### Step 3: Environment Configuration

Your settings are already configured in `lit_project/settings.py` for MySQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lit_database',
        'USER': 'root',
        'PASSWORD': '',  # Change if you have a password
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

### Step 4: Run Database Migrations

Navigate to your project directory and run:

```bash
cd /path/to/Lab-Inventory-Manager-CSE370

# Make migrations
python3 manage.py makemigrations

# Apply migrations to create database tables
python3 manage.py migrate
```

### Step 5: Create Superuser (Admin Account)

```bash
# Create admin user
python3 manage.py createsuperuser

# Or use your custom command
python3 manage.py create_admin
```

### Step 6: Load Sample Data (Optional)

```bash
# If you have sample data command
python3 manage.py populate_sample_data
```

### Step 7: Run the Development Server

```bash
# Start the Django development server
python3 manage.py runserver

# Or specify port
python3 manage.py runserver 8000
```

### Step 8: Access the Application

Open your web browser and navigate to:
- **Main Application**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/

## 🔧 Troubleshooting Common Issues

### Issue 1: mysqlclient installation fails
```bash
# On Ubuntu/Debian
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential

# On CentOS/RHEL
sudo yum install python3-devel mysql-devel

# Then retry
python3 -m pip install mysqlclient
```

### Issue 2: Database connection error
- Check if MySQL/XAMPP is running
- Verify database name and credentials in settings.py
- Ensure the database `lit_database` exists

### Issue 3: Migration errors
```bash
# Reset migrations (if needed)
python3 manage.py migrate --fake-initial

# Or delete migration files and recreate
rm inventory/migrations/0*.py
python3 manage.py makemigrations
python3 manage.py migrate
```

### Issue 4: Static files not loading
```bash
# Collect static files
python3 manage.py collectstatic
```

## 📝 Project Structure

```
Lab-Inventory-Manager-CSE370/
├── manage.py                 # Django management script
├── lit_project/             # Main project settings
│   ├── settings.py          # Configuration
│   ├── urls.py             # URL routing
│   └── wsgi.py             # Web server interface
├── inventory/              # Main application
│   ├── models.py           # Database models
│   ├── views.py            # Business logic
│   ├── forms.py            # Form handling
│   ├── urls.py             # App URLs
│   ├── admin.py            # Admin interface
│   └── templates/          # HTML templates
└── static/                 # CSS, JS, Images
```

## 🎯 Key Features

1. **User Management**: Registration, login, role-based access
2. **Product Management**: Add, edit, delete lab equipment
3. **Borrowing System**: Request, approve, track borrowed items
4. **Admin Dashboard**: Manage users, products, and requests
5. **Reports**: Generate usage statistics and reports

## 🔐 Default Login

After creating a superuser, you can:
1. Login as admin to manage the system
2. Create regular user accounts
3. Approve user registrations

## 🚨 Important Notes

- Make sure MySQL is running before starting the server
- The application uses custom User model, so run migrations before creating users
- Regular users need admin approval before they can log in
- Keep your SECRET_KEY secure in production

## 📊 Database Schema

Your models create these main tables:
- `inventory_user` - User accounts with roles
- `inventory_product` - Lab equipment/products
- `inventory_borrow` - Borrowing records
- `inventory_notification` - System notifications

## 🔄 Development Workflow

1. Make changes to models → `makemigrations` → `migrate`
2. Update views/templates → Restart server if needed
3. Add static files → Run `collectstatic`
4. Test changes → Check browser and logs

Happy coding! 🎉
