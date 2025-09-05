#!/bin/bash

# Lab Inventory Manager - Notification Setup Script
# This script helps set up automated notifications

echo "=== Lab Inventory Manager Notification Setup ==="
echo ""

# Get the current directory
PROJECT_DIR=$(pwd)
echo "Project directory: $PROJECT_DIR"

# Test the notification command
echo ""
echo "Testing notification command..."
python manage.py send_notifications --dry-run

# Check if command worked
if [ $? -eq 0 ]; then
    echo "✅ Notification command test successful!"
else
    echo "❌ Notification command test failed!"
    exit 1
fi

echo ""
echo "=== Cron Job Setup ==="
echo "To set up automated daily notifications, you can add this to your crontab:"
echo ""
echo "# Lab Inventory Manager - Daily notifications at 9 AM"
echo "0 9 * * * cd $PROJECT_DIR && python manage.py send_notifications"
echo ""
echo "To add this to your crontab:"
echo "1. Run: crontab -e"
echo "2. Add the line above"
echo "3. Save and exit"
echo ""

# Offer to add to crontab
read -p "Would you like me to add this to your crontab? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create temporary cron file
    crontab -l > mycron 2>/dev/null || true
    echo "# Lab Inventory Manager - Daily notifications at 9 AM" >> mycron
    echo "0 9 * * * cd $PROJECT_DIR && python manage.py send_notifications" >> mycron
    crontab mycron
    rm mycron
    echo "✅ Cron job added successfully!"
    echo "Notifications will now run daily at 9 AM"
else
    echo "Cron job not added. You can add it manually later."
fi

echo ""
echo "=== Testing Different Scenarios ==="
echo "You can test the notification system with these commands:"
echo ""
echo "# Send reminders 2 days before due date:"
echo "python manage.py send_notifications --reminder-days 2 --dry-run"
echo ""
echo "# Actually send notifications (remove --dry-run):"
echo "python manage.py send_notifications"
echo ""
echo "# Check for overdue items:"
echo "python manage.py send_notifications --reminder-days 0"
echo ""

echo "=== Web Interface ==="
echo "After starting the Django server, you can:"
echo "1. Visit /notifications/ to see all notifications"
echo "2. Check the notification bell in the top navigation"
echo "3. Register new users to trigger admin notifications"
echo "4. Request items to trigger borrow notifications"
echo ""

echo "Setup complete! 🎉"
echo "The notification system is ready to use."
