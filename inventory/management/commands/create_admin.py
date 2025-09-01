# create_admin.py - Custom Django Management Command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
import getpass

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser admin account for the Lab Inventory Manager'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the admin user',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the admin user',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='First name for the admin user',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Last name for the admin user',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating Admin User for Lab Inventory Manager')
        )
        
        # Get username
        username = options.get('username')
        if not username:
            username = input('Username: ')
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')
        
        # Get email
        email = options.get('email')
        if not email:
            email = input('Email: ')
        
        # Validate email
        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists.')
        
        # Get first name
        firstname = options.get('first_name')
        if not firstname:
            firstname = input('First Name: ')
        
        # Get last name
        lastname = options.get('last_name')
        if not lastname:
            lastname = input('Last Name: ')
        
        # Get password
        password = getpass.getpass('Password: ')
        password_confirm = getpass.getpass('Password (again): ')
        
        if password != password_confirm:
            raise CommandError('Passwords do not match.')
        
        # Create the user
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    firstname=firstname,
                    lastname=lastname,
                    password=password,
                    role='admin',
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created admin user "{username}" with ID: {user.user_id}'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error creating user: {str(e)}')

# Usage:
# python manage.py create_admin
# python manage.py create_admin --username admin --email admin@lab.com --first-name Admin --last-name User