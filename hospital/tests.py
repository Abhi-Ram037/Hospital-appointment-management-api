
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Patient, Doctor, Appointment, Payment


class HospitalAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.patient = Patient.objects.create(
            name="Ravi Kumar",
            email="ravi@example.com",
            phone="9876543210",
            age=25
        )

        self.doctor = Doctor.objects.create(
            name="Dr. Suresh",
            specialization="Cardiology",
            consultation_fee=Decimal("800.00"),
            is_available=True
        )

        future = timezone.localtime() + timedelta(days=5)

        self.appointment_data = {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": future.date().isoformat(),
            "appointment_time": future.strftime("%H:%M:%S"),
            "reason": "Regular checkup"
        }

    def create_appointment(self, status="Scheduled"):
        return Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_data["appointment_date"],
            appointment_time=self.appointment_data["appointment_time"],
            reason="Regular checkup",
            status=status
        )

    def test_create_patient(self):
        response = self.client.post("/patients/", {
            "name": "Anil",
            "email": "anil@example.com",
            "phone": "9876543211",
            "age": 30
        }, format="json")

        self.assertEqual(response.status_code, 201)

    def test_duplicate_patient_email(self):
        response = self.client.post("/patients/", {
            "name": "Duplicate",
            "email": "ravi@example.com",
            "phone": "9876543212",
            "age": 20
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_invalid_patient_age(self):
        response = self.client.post("/patients/", {
            "name": "Test Patient",
            "email": "test@example.com",
            "phone": "9876543212",
            "age": 0
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_invalid_phone(self):
        response = self.client.post("/patients/", {
            "name": "Test Patient",
            "email": "test@example.com",
            "phone": "abc",
            "age": 25
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_invalid_doctor_fee(self):
        response = self.client.post("/doctors/", {
            "name": "Dr. Test",
            "specialization": "General",
            "consultation_fee": "0.00",
            "is_available": True
        }, format="json")

        self.assertEqual(response.status_code, 400)

    def test_book_appointment(self):
        response = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "Scheduled")

    def test_unavailable_doctor(self):
        self.doctor.is_available = False
        self.doctor.save()

        response = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_patient_id(self):
        data = self.appointment_data.copy()
        data["patient"] = 99999

        response = self.client.post(
            "/appointments/",
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_past_appointment(self):
        data = self.appointment_data.copy()
        past = timezone.localtime() - timedelta(days=2)

        data["appointment_date"] = past.date().isoformat()
        data["appointment_time"] = past.strftime("%H:%M:%S")

        response = self.client.post(
            "/appointments/",
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_double_booking(self):
        first = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        second = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        self.assertEqual(first.status_code, 201)
        self.assertIn(second.status_code, [400, 409])
        self.assertEqual(Appointment.objects.count(), 1)

    def test_invalid_appointment_status(self):
        appointment = self.create_appointment()

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Invalid"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_complete_unconfirmed_appointment(self):
        appointment = self.create_appointment()

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Completed"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_complete_future_appointment(self):
        appointment = self.create_appointment(status="Confirmed")

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Completed"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_payment_creation(self):
        appointment = self.create_appointment()

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "UPI"},
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        payment = Payment.objects.get(appointment=appointment)

        self.assertEqual(payment.payment_status, "Paid")
        self.assertEqual(
            payment.amount,
            Decimal(str(self.doctor.consultation_fee))
        )

    def test_invalid_payment_method(self):
        appointment = self.create_appointment()

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Bitcoin"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            Payment.objects.filter(
                appointment=appointment
            ).exists()
        )

    def test_duplicate_payment(self):
        appointment = self.create_appointment()

        first = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "UPI"},
            format="json"
        )

        second = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)

        self.assertEqual(
            Payment.objects.filter(
                appointment=appointment
            ).count(),
            1
        )

    def test_cannot_pay_for_cancelled_appointment(self):
        appointment = self.create_appointment(status="Cancelled")

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "UPI"},
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cancel_paid_appointment_refunds_payment(self):
        appointment = self.create_appointment()

        payment = Payment.objects.create(
            appointment=appointment,
            amount=self.doctor.consultation_fee,
            payment_method="UPI",
            payment_status="Paid",
            payment_date=timezone.now()
        )

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            format="json"
        )

        self.assertEqual(response.status_code, 200)

        appointment.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(appointment.status, "Cancelled")
        self.assertEqual(payment.payment_status, "Refunded")

    def test_cannot_cancel_completed_appointment(self):
        appointment = self.create_appointment(status="Completed")

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cannot_cancel_twice(self):
        appointment = self.create_appointment(status="Cancelled")

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_cancelled_slot_can_be_booked_again(self):
        first = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        self.assertEqual(first.status_code, 201)

        appointment_id = first.data["id"]

        cancelled = self.client.post(
            f"/appointments/{appointment_id}/cancel/",
            format="json"
        )

        self.assertEqual(cancelled.status_code, 200)

        second = self.client.post(
            "/appointments/",
            self.appointment_data,
            format="json"
        )

        self.assertEqual(second.status_code, 201)
