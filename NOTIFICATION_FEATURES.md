# Enhanced Notification System Features

## Overview
I've successfully added comprehensive notification features to your Lab Inventory Manager system. Here's what's been implemented:

## 1. Enhanced Notification Model
The `Notification` model has been enhanced with the following new fields:
- **notification_type**: Categorizes notifications (user_registration, borrow_request, return_reminder, overdue_alert, etc.)
- **priority**: Sets priority level (low, medium, high, urgent)
- **title**: Short title for the notification
- **related_borrow**: Links notifications to specific borrow records
- **read_at**: Timestamp when notification was read
- **Improved organization** with proper ordering and methods

## 2. Admin Notifications
Admins now receive notifications for:

### User Registration
- **Trigger**: When a new user registers
- **Content**: Detailed user information including username, email, and user ID
- **Priority**: Medium
- **Action Required**: Admin needs to approve/reject the registration

### Borrow Requests
- **Trigger**: When a user requests to borrow an item
- **Content**: Product details, requester information, expected return date
- **Priority**: Medium
- **Action Required**: Admin needs to approve/reject the request

## 3. User Notifications
Regular users receive notifications for:

### Return Reminders
- **Trigger**: Automated daily check (1 day before due date by default)
- **Content**: Friendly reminder with item name and due date
- **Priority**: Medium
- **Purpose**: Help users return items on time

### Overdue Alerts
- **Trigger**: Automated daily check for items past due date
- **Content**: Urgent warning with days overdue
- **Priority**: Urgent
- **Additional Action**: 
  - Item status changed to "overdue"
  - Admins also notified about overdue items

### Approval/Rejection Status
- **Trigger**: When admin approves/rejects borrow requests
- **Content**: Status update with item details
- **Priority**: Medium-High
- **Purpose**: Keep users informed about their requests

## 4. Automated Notification System

### Management Command
Created `send_notifications.py` management command that can:
- Send return reminders (configurable days before due date)
- Send overdue alerts
- Notify admins about overdue items
- Support dry-run mode for testing
- Provide detailed logging

**Usage Examples:**
```bash
# Send notifications with default settings (1 day before due)
python manage.py send_notifications

# Send reminders 2 days before due date
python manage.py send_notifications --reminder-days 2

# Test what notifications would be sent without actually sending them
python manage.py send_notifications --dry-run
```

### Scheduling
You can schedule this command to run daily using:
- **Cron jobs** (Linux/Mac)
- **Task Scheduler** (Windows)
- **Django-crontab** package
- **Celery** with periodic tasks

Example cron job (runs daily at 9 AM):
```bash
0 9 * * * cd /path/to/your/project && python manage.py send_notifications
```

## 5. User Interface Enhancements

### Notification Bell
- Added notification bell icon to navigation
- Shows real-time unread count badge
- Links to full notifications page
- Auto-refreshes every 30 seconds

### Notifications Page
- Comprehensive notifications view with pagination
- Color-coded notifications by type and priority
- Filtering and sorting options
- Mark all as read functionality
- Detailed notification history

### Visual Indicators
- **Urgent**: Red border and icon (overdue items)
- **High**: Orange border (important updates)
- **Medium**: Blue border (standard notifications)
- **Low**: Gray border (general information)

## 6. API Endpoints
Created RESTful API endpoints for:
- `GET /api/notifications/count/` - Get unread count
- `GET /api/notifications/recent/` - Get recent notifications
- `POST /api/notifications/mark-read/<id>/` - Mark notification as read

## 7. Database Schema Updates
The enhanced notification system includes proper database relationships:
- Foreign key to User (recipient)
- Foreign key to User (related user, optional)
- Foreign key to Borrow (related borrow record, optional)
- Proper indexing for performance
- Timestamps for tracking

## 8. Security & Performance
- **User Isolation**: Users only see their own notifications
- **Admin Privileges**: Admins see system-wide notifications
- **Pagination**: Large notification lists are paginated
- **Optimized Queries**: Uses select_related for efficient database queries
- **Error Handling**: Graceful handling of notification failures

## 9. Notification Types Supported

| Type | Trigger | Recipients | Priority | Auto-Generated |
|------|---------|------------|----------|----------------|
| user_registration | User registers | Admins | Medium | ✅ |
| borrow_request | User requests item | Admins | Medium | ✅ |
| borrow_approved | Admin approves request | User | High | ✅ |
| borrow_rejected | Admin rejects request | User | Medium | ✅ |
| return_reminder | 1 day before due | User | Medium | ✅ |
| overdue_alert | Item overdue | User & Admins | Urgent | ✅ |
| item_returned | User returns item | Admins | Low | ✅ |
| general | Manual/System | Any | Variable | Manual |

## 10. Setup Instructions

### 1. Database Migration
Already completed - the notification model has been migrated.

### 2. Set Up Automated Notifications
Add to your system's cron jobs:
```bash
# Edit crontab
crontab -e

# Add this line to run notifications check daily at 9 AM
0 9 * * * cd /Users/lmh/Documents/LITproject && python manage.py send_notifications

# Add this line to run every 6 hours for more frequent checks
0 */6 * * * cd /Users/lmh/Documents/LITproject && python manage.py send_notifications
```

### 3. Test the System
```bash
# Test with dry run
python manage.py send_notifications --dry-run

# Test with actual notifications
python manage.py send_notifications
```

## 11. Usage Examples

### For Testing
1. Register a new user → Admin gets notification
2. Login as user and request an item → Admin gets notification
3. Login as admin and approve request → User gets notification
4. Wait for due date or manually change dates → Users get reminders/alerts

### For Production
1. Set up the cron job for automated daily checks
2. Notifications will be sent automatically
3. Users and admins will see notifications in the web interface
4. Email notifications can be added later if needed

## 12. Future Enhancements
The system is designed to easily support:
- Email notifications
- SMS notifications  
- Push notifications
- Custom notification templates
- Notification preferences per user
- Bulk notification operations
- Advanced filtering and search

## Files Modified/Created
1. **Enhanced**: `inventory/models.py` - Notification model
2. **Enhanced**: `inventory/views.py` - Notification views and functions
3. **Enhanced**: `inventory/urls.py` - Notification URL patterns
4. **Enhanced**: `inventory/templates/base.html` - Notification bell
5. **Created**: `inventory/templates/notifications.html` - Notifications page
6. **Created**: `inventory/management/commands/send_notifications.py` - Automation command
7. **Created**: Migration file for database updates

The notification system is now fully functional and ready for use!
