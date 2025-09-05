"""
Management command to send automated return reminders and overdue alerts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from inventory.models import Borrow, Notification, User


class Command(BaseCommand):
    help = 'Send return reminders and overdue alerts to users with borrowed items'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reminder-days',
            type=int,
            default=1,
            help='Send reminder N days before due date (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what notifications would be sent without actually sending them'
        )
    
    def handle(self, *args, **options):
        reminder_days = options['reminder_days']
        dry_run = options['dry_run']
        
        today = timezone.now().date()
        reminder_date = today + timedelta(days=reminder_days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Checking for notifications on {today}')
        )
        
        # Find items due for return reminder
        items_for_reminder = Borrow.objects.filter(
            status='active',
            expected_return_date=reminder_date
        ).select_related('user', 'product')
        
        # Find overdue items
        overdue_items = Borrow.objects.filter(
            status='active',
            expected_return_date__lt=today
        ).select_related('user', 'product')
        
        reminder_count = 0
        overdue_count = 0
        
        # Send return reminders
        for borrow in items_for_reminder:
            # Check if reminder already sent
            existing_reminder = Notification.objects.filter(
                recipient_user=borrow.user,
                related_borrow=borrow,
                notification_type='return_reminder',
                created_at__date=today
            ).exists()
            
            if not existing_reminder:
                title = f"Return Reminder: {borrow.product.name}"
                message = (
                    f"Hi {borrow.user.get_full_name()},\n\n"
                    f"This is a friendly reminder that you have borrowed '{borrow.product.name}' "
                    f"which is due for return on {borrow.expected_return_date.strftime('%B %d, %Y')}.\n\n"
                    f"Please return the item on time to avoid any overdue penalties.\n\n"
                    f"If you need to extend the borrowing period, please contact an administrator.\n\n"
                    f"Thank you!"
                )
                
                if not dry_run:
                    Notification.objects.create(
                        recipient_user=borrow.user,
                        related_borrow=borrow,
                        notification_type='return_reminder',
                        priority='medium',
                        title=title,
                        message=message
                    )
                
                self.stdout.write(
                    f"{'[DRY RUN] ' if dry_run else ''}Return reminder sent to {borrow.user.username} "
                    f"for {borrow.product.name}"
                )
                reminder_count += 1
        
        # Send overdue alerts
        for borrow in overdue_items:
            days_overdue = (today - borrow.expected_return_date).days
            
            # Check if overdue alert already sent today
            existing_alert = Notification.objects.filter(
                recipient_user=borrow.user,
                related_borrow=borrow,
                notification_type='overdue_alert',
                created_at__date=today
            ).exists()
            
            if not existing_alert:
                # Update borrow status to overdue
                if not dry_run:
                    borrow.status = 'overdue'
                    borrow.save()
                
                title = f"OVERDUE ALERT: {borrow.product.name}"
                message = (
                    f"URGENT: {borrow.user.get_full_name()},\n\n"
                    f"Your borrowed item '{borrow.product.name}' is now {days_overdue} day(s) overdue!\n"
                    f"Expected return date was: {borrow.expected_return_date.strftime('%B %d, %Y')}\n\n"
                    f"Please return the item immediately to avoid further penalties.\n"
                    f"Contact an administrator if you have any issues.\n\n"
                    f"This is an automated alert."
                )
                
                if not dry_run:
                    Notification.objects.create(
                        recipient_user=borrow.user,
                        related_borrow=borrow,
                        notification_type='overdue_alert',
                        priority='urgent',
                        title=title,
                        message=message
                    )
                    
                    # Also notify admins about overdue items
                    admin_users = User.objects.filter(role='admin', is_active=True)
                    for admin in admin_users:
                        Notification.objects.create(
                            recipient_user=admin,
                            related_user=borrow.user,
                            related_borrow=borrow,
                            notification_type='overdue_alert',
                            priority='high',
                            title=f"User has overdue item: {borrow.product.name}",
                            message=(
                                f"User {borrow.user.get_full_name()} ({borrow.user.username}) "
                                f"has an overdue item: '{borrow.product.name}'\n"
                                f"Expected return date: {borrow.expected_return_date.strftime('%B %d, %Y')}\n"
                                f"Days overdue: {days_overdue}\n\n"
                                f"Please follow up with the user."
                            )
                        )
                
                self.stdout.write(
                    self.style.WARNING(
                        f"{'[DRY RUN] ' if dry_run else ''}Overdue alert sent to {borrow.user.username} "
                        f"for {borrow.product.name} ({days_overdue} days overdue)"
                    )
                )
                overdue_count += 1
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[DRY RUN] Would send {reminder_count} return reminders and {overdue_count} overdue alerts"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSent {reminder_count} return reminders and {overdue_count} overdue alerts"
                )
            )
