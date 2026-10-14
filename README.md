# Hospital Appointment Management API

## Project Overview

The Hospital Appointment Management API is a backend application developed using Django and Django REST Framework. It allows users to manage patients, doctors, appointments, appointment statuses, and payment records through RESTful API endpoints.

## Features

- Patient management
- Doctor management
- Appointment booking and viewing
- Appointment status updates
- Appointment cancellation
- Payment record management
- JWT authentication
- Role-based access control
- Swagger API documentation
- SQLite database integration
- Automated API tests

## Technologies Used

- Python
- Django
- Django REST Framework
- SQLite
- Simple JWT
- drf-spectacular
- Swagger UI
- Git and GitHub

## Project Structure

```text
hospital_appointment/
├── hospital/
│   ├── migrations/
│   ├── admin.py
│   ├── models.py
│   ├── serializers.py
│   ├── permissions.py
│   ├── tests.py
│   ├── views.py
│   └── urls.py
├── hospital_api/
│   ├── settings.py
│   └── urls.py
├── manage.py
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Abhi-Ram037/Hospital-appointment-management-api.git
cd Hospital-appointment-management-api
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

## API Documentation

Once the development server is running, access the Swagger documentation at:

`http://127.0.0.1:8000/swagger/`

## Authentication

The project uses JSON Web Token (JWT) authentication.

- Obtain tokens through `/api/token/`.
- Refresh an access token through `/api/token/refresh/`.
- Send the access token in the HTTP Authorization header using the Bearer scheme.

## Testing

Run the automated tests with:

```bash
python manage.py test hospital
```

## Database

SQLite is used as the development database. Django migrations manage database schema changes.

## Repository

GitHub: https://github.com/Abhi-Ram037/Hospital-appointment-management-api

## Future Improvements

- Email notifications for appointments
- Integration with a real payment gateway
- Deployment to a production server
- Additional reporting and analytics
