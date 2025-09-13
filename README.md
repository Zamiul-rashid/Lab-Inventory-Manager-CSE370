# Lab Inventory Manager (CSE 370 Project)

A comprehensive lab inventory management system built with Django, designed to streamline equipment borrowing, user management, and administrative oversight for educational institutions.

## 🎯 Project Overview

This system provides a complete solution for managing laboratory equipment with role-based access control, automated notifications, and comprehensive reporting capabilities. Built as part of CSE 370 Database Systems course.

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Layer    │    │  Admin Layer    │    │  Database Layer │
│                 │    │                 │    │                 │
│ • Registration  │    │ • User Approval │    │ • User Model    │
│ • Product Browse│◄──►│ • Product CRUD  │◄──►│ • Product Model │
│ • Borrow Request│    │ • Reports       │    │ • Borrow Model  │
│ • Notifications │    │ • Analytics     │    │ • Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

##  Key Features

### User Management
- **Registration System**: New user registration with admin approval workflow
- **Role-based Access**: Student and Admin roles with different permissions
- **Profile Management**: User profile editing and password management
- **Authentication**: Secure login/logout with session management

### Product Management
- **Inventory Tracking**: Complete product catalog with categories and status
- **CRUD Operations**: Add, edit, delete products (admin only)
- **Search & Filter**: Advanced filtering by category, status, and availability
- **Location Tracking**: Physical location management for equipment

### Borrowing System
- **Request Workflow**: Students can request to borrow available items
- **Approval Process**: Admins approve/reject borrow requests
- **Return Management**: Track expected and actual return dates
- **History Tracking**: Complete borrowing history for audit purposes

### Notifications & Alerts
- **Automated Reminders**: Email notifications for upcoming due dates
- **Overdue Alerts**: Automatic alerts for overdue items
- **Status Updates**: Real-time notifications for request approvals/rejections
- **Admin Notifications**: Alerts for pending requests and registrations

### Reporting & Analytics
- **Borrowing Trends**: Visual charts showing usage patterns
- **Category Analysis**: Distribution of items across categories
- **User Statistics**: Active users and borrowing statistics
- **CSV Exports**: Data export functionality for external analysis

## 🛠️ Technical Stack

- **Backend**: Django 4.x, Python 3.x
- **Database**: SQLite (Development), PostgreSQL (Production Ready)
- **Frontend**: Django Templates, Bootstrap 5, JavaScript
- **Authentication**: Django Auth System
- **Notifications**: Django Email Backend
- **Charts**: Chart.js for analytics visualization

## 👥 Contributors

### [Azra Humayra Alam Prova](https://github.com/you-know-wh0)
### [Zamiul Rashid](https://github.com/Zamiul-rashid)


## 📋 Installation & Setup

### Prerequisites
```bash
- Python 3.8+
- pip (Python package manager)
- Git
```

### Quick Start
```bash
# Clone the repository
git clone https://github.com/you-know-wh0/Lab-Inventory-Manager-CSE370.git
cd Lab-Inventory-Manager-CSE370

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py create_admin

# Load sample data (optional)
python manage.py populate_sample_data

# Start development server
python manage.py runserver
```

### Environment Setup
```bash
# Development settings
export DJANGO_SETTINGS_MODULE=lit_project.settings_dev

# Production settings
export DJANGO_SETTINGS_MODULE=lit_project.settings
```

## 🎯 Usage Examples

### For Students
1. **Register**: Create account and wait for admin approval
2. **Browse**: Search and filter available lab equipment
3. **Request**: Submit borrow requests for needed items
4. **Track**: Monitor request status and borrowed items
5. **Return**: Mark items as returned when done

### For Admins
1. **Approve Users**: Review and approve new registrations
2. **Manage Inventory**: Add, edit, and remove lab equipment
3. **Process Requests**: Approve/reject borrow requests
4. **Monitor**: Track overdue items and send reminders
5. **Analyze**: Generate reports and export data

## 🔮 Future Enhancements

- 📱 **Mobile App**: React Native mobile application
- 🔗 **REST API**: Django REST Framework integration
- 📧 **Advanced Notifications**: SMS and push notifications
- 📊 **Enhanced Analytics**: Machine learning for usage prediction
- 🔍 **Barcode Scanner**: QR/Barcode integration for equipment
- 🌐 **Multi-language**: Internationalization support

## 📝 License

This project is licensed under the MIT License - see the details below:

**MIT License**

Copyright (c) 2025 Lab Inventory Manager Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*This project was developed as part of CSE 370 Database Systems course at BRAC University.*

## 🤝 Contributing

This is an academic project. For suggestions or improvements, please open an issue.

---
