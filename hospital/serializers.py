import re
from datetime import datetime
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from .models import Patient, Doctor, Appointment, Payment


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = "__all__"

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Patient name cannot be empty."
            )
        return value.strip()

    def validate_email(self, value):
        value = value.strip().lower()

        patients = Patient.objects.filter(email__iexact=value)

        if self.instance:
            patients = patients.exclude(pk=self.instance.pk)

        if patients.exists():
            raise serializers.ValidationError(
                "A patient with this email already exists."
            )

        return value

    def validate_phone(self, value):
        value = value.strip()

        if not re.fullmatch(r"\+?[0-9\s-]{7,20}", value):
            raise serializers.ValidationError(
                "Enter a valid phone number."
            )

        digits = re.sub(r"\D", "", value)

        if not 7 <= len(digits) <= 15:
            raise serializers.ValidationError(
                "Phone number must contain 7 to 15 digits."
            )

        return value

    def validate_age(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Age must be greater than zero."
            )
        return value


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = "__all__"

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Doctor name cannot be empty."
            )
        return value.strip()

    def validate_specialization(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Specialization cannot be empty."
            )
        return value.strip()

    def validate_consultation_fee(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Consultation fee must be greater than zero."
            )
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source="patient.name",
        read_only=True
    )
    doctor_name = serializers.CharField(
        source="doctor.name",
        read_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "appointment_date",
            "appointment_time",
            "reason",
            "status",
        ]
        read_only_fields = ["id", "status"]

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Appointment reason cannot be empty."
            )
        return value.strip()

    def validate(self, attrs):
        patient = attrs.get(
            "patient",
            getattr(self.instance, "patient", None)
        )
        doctor = attrs.get(
            "doctor",
            getattr(self.instance, "doctor", None)
        )
        appointment_date = attrs.get(
            "appointment_date",
            getattr(self.instance, "appointment_date", None)
        )
        appointment_time = attrs.get(
            "appointment_time",
            getattr(self.instance, "appointment_time", None)
        )

        if patient is None:
            raise serializers.ValidationError(
                {"patient": "A valid patient is required."}
            )

        if doctor is None:
            raise serializers.ValidationError(
                {"doctor": "A valid doctor is required."}
            )

        if appointment_date is None or appointment_time is None:
            raise serializers.ValidationError(
                "Appointment date and time are required."
            )

        if not doctor.is_available:
            raise serializers.ValidationError(
                {"doctor": "This doctor is not available."}
            )

        appointment_datetime = datetime.combine(
            appointment_date,
            appointment_time
        )

        if timezone.is_naive(appointment_datetime):
            appointment_datetime = timezone.make_aware(
                appointment_datetime,
                timezone.get_current_timezone()
            )

        if appointment_datetime <= timezone.now():
            raise serializers.ValidationError(
                "Appointment must be scheduled for a future date and time."
            )

        # Check whether the doctor already has an active appointment.
        # Cancelled appointments do not block the time slot.
        appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).exclude(status="Cancelled")

        if self.instance:
            appointments = appointments.exclude(
                pk=self.instance.pk
            )

        if appointments.exists():
            raise serializers.ValidationError(
                "This doctor already has an appointment at this time."
            )

        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = [
            "id",
            "amount",
            "payment_status",
            "payment_date",
        ]

    def validate_payment_method(self, value):
        allowed_methods = ["Cash", "UPI", "Card"]

        if value not in allowed_methods:
            raise serializers.ValidationError(
                "Payment method must be Cash, UPI, or Card."
            )

        return value