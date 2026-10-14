from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Patient, Doctor, Appointment, Payment


class HospitalAPITests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_superuser(
            username="testadmin",
            email="testadmin@example.com",
            password="TestAdmin123!"
        )
        self.client.force_authenticate(user=self.admin_user)

        self.patient = Patient.objects.create(
            name="Test Patient",
            email="patient@example.com",
            phone="9876543210",
            age=25
        )

        self.doctor = Doctor.objects.create(
            name="Test Doctor",
            specialization="General",
            consultation_fee=500,
            is_available=True
        )

        self.future_date = timezone.localdate() + timedelta(days=2)
        self.future_time = (timezone.localtime().time().replace(
            second=0, microsecond=0
        ))

        self.future_time = (
            timezone.localtime() + timedelta(hours=2)
        ).time().replace(second=0, microsecond=0)

    def create_appointment(self, patient=None, doctor=None, **kwargs):
        data = {
            "patient": patient or self.patient,
            "doctor": doctor or self.doctor,
            "appointment_date": self.future_date,
            "appointment_time": self.future_time,
            "reason": "General checkup",
            "status": "Scheduled",
        }
        data.update(kwargs)
        return Appointment.objects.create(**data)

    def test_create_patient(self):
        response = self.client.post("/patients/", {
            "name": "New Patient",
            "email": "newpatient@example.com",
            "phone": "9876543211",
            "age": 30
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_patient_email(self):
        response = self.client.post("/patients/", {
            "name": "Another Patient",
            "email": self.patient.email,
            "phone": "9876543212",
            "age": 28
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_invalid_patient_age(self):
        response = self.client.post("/patients/", {
            "name": "Invalid Patient",
            "email": "invalidage@example.com",
            "phone": "9876543213",
            "age": -1
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_invalid_patient_phone(self):
        response = self.client.post("/patients/", {
            "name": "Invalid Phone",
            "email": "invalidphone@example.com",
            "phone": "abc",
            "age": 25
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_invalid_doctor_fee(self):
        response = self.client.post("/doctors/", {
            "name": "Invalid Doctor",
            "specialization": "General",
            "consultation_fee": -100,
            "is_available": True
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_book_appointment(self):
        response = self.client.post("/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": str(self.future_date),
            "appointment_time": self.future_time.strftime("%H:%M:%S"),
            "reason": "Checkup"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unavailable_doctor(self):
        self.doctor.is_available = False
        self.doctor.save()

        response = self.client.post("/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": str(self.future_date),
            "appointment_time": self.future_time.strftime("%H:%M:%S"),
            "reason": "Checkup"
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_invalid_patient_id(self):
        response = self.client.post("/appointments/", {
            "patient": 99999,
            "doctor": self.doctor.id,
            "appointment_date": str(self.future_date),
            "appointment_time": self.future_time.strftime("%H:%M:%S"),
            "reason": "Checkup"
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_past_appointment(self):
        past_date = timezone.localdate() - timedelta(days=1)

        response = self.client.post("/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": str(past_date),
            "appointment_time": "10:00:00",
            "reason": "Checkup"
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_double_booking(self):
        self.create_appointment()

        response = self.client.post("/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": str(self.future_date),
            "appointment_time": self.future_time.strftime("%H:%M:%S"),
            "reason": "Second appointment"
        }, format="json")

        self.assertGreaterEqual(response.status_code, 400)

    def test_invalid_appointment_status(self):
        appointment = self.create_appointment()

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "InvalidStatus"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_cannot_complete_unconfirmed_appointment(self):
        appointment = self.create_appointment()

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Completed"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_cannot_complete_future_appointment(self):
        appointment = self.create_appointment(status="Confirmed")

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Completed"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_create_payment(self):
        appointment = self.create_appointment()

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_payment_method(self):
        appointment = self.create_appointment()

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Bitcoin"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_duplicate_payment(self):
        appointment = self.create_appointment()

        self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "UPI"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_cannot_pay_for_cancelled_appointment(self):
        appointment = self.create_appointment(status="Cancelled")

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_cancel_paid_appointment_refunds_payment(self):
        appointment = self.create_appointment()

        self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payment = Payment.objects.get(appointment=appointment)
        self.assertEqual(payment.payment_status, "Refunded")

    def test_cannot_cancel_completed_appointment(self):
        appointment = self.create_appointment(status="Completed")

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        self.assertGreaterEqual(response.status_code, 400)

    def test_cannot_cancel_appointment_twice(self):
        appointment = self.create_appointment(status="Scheduled")

        first_response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        second_response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(second_response.status_code, 400)

    def test_cancelled_slot_can_be_rebooked(self):
        appointment = self.create_appointment()

        self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        response = self.client.post("/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": str(self.future_date),
            "appointment_time": self.future_time.strftime("%H:%M:%S"),
            "reason": "Rebooked appointment"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_user_cannot_create_patient(self):
        self.client.force_authenticate(user=None)

        response = self.client.post("/patients/", {
            "name": "Test Patient",
            "email": "unauthenticated@example.com",
            "phone": "9876543214",
            "age": 25
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_view_another_patients_appointment(self):
        patient_group, _ = Group.objects.get_or_create(name="Patient")
        patient_user = User.objects.create_user(
            username="patientuser",
            password="Patient123!"
        )
        patient_user.groups.add(patient_group)

        self.patient.user = patient_user
        self.patient.save()

        other_patient = Patient.objects.create(
            name="Other Patient",
            email="otherpatient@example.com",
            phone="9876543215",
            age=30
        )
        appointment = self.create_appointment(patient=other_patient)

        self.client.force_authenticate(user=patient_user)

        response = self.client.get(f"/appointments/{appointment.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_cannot_cancel_another_patients_appointment(self):
        patient_group, _ = Group.objects.get_or_create(name="Patient")
        patient_user = User.objects.create_user(
            username="patientcancel",
            password="Patient123!"
        )
        patient_user.groups.add(patient_group)

        self.patient.user = patient_user
        self.patient.save()

        other_patient = Patient.objects.create(
            name="Other Patient",
            email="othercancel@example.com",
            phone="9876543216",
            age=28
        )
        appointment = self.create_appointment(patient=other_patient)

        self.client.force_authenticate(user=patient_user)

        response = self.client.post(
            f"/appointments/{appointment.id}/cancel/",
            {},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "Scheduled")

    def test_doctor_cannot_update_another_doctors_appointment(self):
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")
        doctor_user = User.objects.create_user(
            username="doctoruser",
            password="Doctor123!"
        )
        doctor_user.groups.add(doctor_group)

        self.doctor.user = doctor_user
        self.doctor.save()

        other_doctor = Doctor.objects.create(
            name="Other Doctor",
            specialization="Cardiology",
            consultation_fee=700,
            is_available=True
        )
        appointment = self.create_appointment(doctor=other_doctor)

        self.client.force_authenticate(user=doctor_user)

        response = self.client.put(
            f"/appointments/{appointment.id}/status/",
            {"status": "Confirmed"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "Scheduled")

    def test_patient_cannot_pay_for_another_patients_appointment(self):
        patient_group, _ = Group.objects.get_or_create(name="Patient")
        patient_user = User.objects.create_user(
            username="patientpayment",
            password="Patient123!"
        )
        patient_user.groups.add(patient_group)

        self.patient.user = patient_user
        self.patient.save()

        other_patient = Patient.objects.create(
            name="Payment Patient",
            email="paymentpatient@example.com",
            phone="9876543217",
            age=29
        )
        appointment = self.create_appointment(patient=other_patient)

        self.client.force_authenticate(user=patient_user)

        response = self.client.post(
            f"/appointments/{appointment.id}/payment/",
            {"payment_method": "Cash"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Payment.objects.filter(appointment=appointment).exists())
