# Hospital Appointment Management API

## Project Overview

A backend REST API developed using Python, Django, and Django REST Framework to manage patients, doctors, appointments, and payment records.

## Features

- Patient registration and validation
- Create and list doctors
- Book and retrieve appointments
- Prevent double booking of active appointment slots
- Allow rebooking after cancellation
- Update appointment statuses
- Cancel appointments
- Record simulated payments and refunds
- JWT access and refresh token endpoints
- JWT-protected user profile endpoint
- Automated API tests

## Technologies Used

- Python
- Django
- Django REST Framework
- Django REST Framework Simple JWT
- SQLite3
- Git and GitHub

## Project Structure

```text
hospital_appointment/
├── hospital/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
├── hospital_api/
│   ├── settings.py
│   └── urls.py
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Abhi-Ram037/Hospital-appointment-management-api.git
cd Hospital-appointment-management-api
```

### 2. Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Apply migrations

```powershell
python manage.py migrate
```

### 5. Create an administrator account

```powershell
python manage.py createsuperuser
```

### 6. Run the development server

```powershell
python manage.py runserver
```

Server URL: http://127.0.0.1:8000/

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/patients/` | Register a patient |
| GET | `/doctors/` | List doctors |
| POST | `/doctors/` | Create a doctor |
| GET | `/appointments/` | List appointments |
| POST | `/appointments/` | Book an appointment |
| GET | `/appointments/<id>/` | Get appointment details |
| PUT | `/appointments/<id>/status/` | Update appointment status |
| POST | `/appointments/<id>/payment/` | Record payment |
| POST | `/appointments/<id>/cancel/` | Cancel an appointment |
| POST | `/api/token/` | Obtain JWT tokens |
| POST | `/api/token/refresh/` | Refresh an access token |
| GET | `/api/user/profile/` | Get authenticated user profile |

## Example: Register a Patient

Send a POST request to `/patients/`:

```json
{
  "name": "Rahul Kumar",
  "email": "rahul@example.com",
  "phone": "9876543210",
  "age": 25
}
```

## Example: Book an Appointment

Send a POST request to `/appointments/` using valid patient and doctor IDs:

```json
{
  "patient": 1,
  "doctor": 1,
  "appointment_date": "2026-10-20",
  "appointment_time": "10:30:00",
  "reason": "Regular health checkup"
}
```

Use a future date and time when testing.

## JWT Authentication

Send a POST request to `/api/token/` with the username and password of an active Django user. The response contains access and refresh tokens.

Send the access token in the following HTTP header when calling a protected endpoint:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Never publish passwords, JWT tokens, secret keys, or environment files.

## Appointment Statuses

- Scheduled
- Confirmed
- Completed
- Cancelled

The API validates status transitions and allows cancelled appointment slots to be booked again.

## Payments

The API supports Cash, UPI, and Card payment methods. Payment amounts are based on the doctor's consultation fee.

Payments and refunds are simulated database updates. No real financial transaction is processed.

## Running Tests

```powershell
python manage.py test hospital
```

During development, all 21 tests passed. Run the tests again after code changes to verify the current project.

## Security Notes

- Configure strong secret keys using environment variables.
- Review role-based and object-level permissions before production deployment.
- Use HTTPS and a production-ready server.
- Integrate a payment gateway if real payments are required.

## Future Improvements

- Patient, doctor, and administrator roles
- Doctor availability schedules
- Email and SMS notifications
- Real payment gateway integration
- Swagger/OpenAPI documentation
- Production deployment

## Author

Developed as a Python and Django REST API project demonstrating backend development, validation, appointment scheduling, JWT authentication setup, and automated testing.
