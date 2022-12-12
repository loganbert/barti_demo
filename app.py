from datetime import datetime, timedelta

from flask import Flask, request
from typing import Dict, List, Union

from models import db, Appointment, Doctor, OfficeHour

app = Flask(__name__)


class HTTPReturn:
    """This class is for enforcing return formats and acts as a future hook for
    validation.

    Args:
        status (int): HTTP status code.
        message (str): HTTP response message.
        data (many): Requested data or None.

    """
    status: int
    message: str
    data: Union[Dict, List, str, None]

    def __init__(self, status, message, data):
        self.status = status
        self.message = message
        self.data = data

    def as_dict(self):
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data
        }


@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    """This endpoint receives GET and POST requests.

    GET requests return either all Appointments if no filters are provided,
    or a filtered set of Appointments after a provided start_time filter,
    before a provided end_time filter, and for a doctor specified by the doctor_id filter.

    POST requests create an appointment with the given required start and end times for
    the doctor specified by the required doctor_id.

    Args:
        doctor_id (str): ID of the doctor to book or check.
        start_time (str): Start time expressed as a DateTime string in '%Y-%d-%m %H:%M' format.
        end_time (str): End time expressed as a DateTime string in '%Y-%d-%m %H:%M' format.

    Returns:
        dict: a dictionary representation of the HTTPReturns class.

    """
    db.connect()
    # Initial values from POST, all fields required on Create
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        request_start_time = request.form.get('start_time')
        request_end_time = request.form.get('end_time')
        # Return Error for incomplete requests
        if not doctor_id or not request_start_time or not request_end_time:
            return HTTPReturn(
                400,
                "Doctor id, start time, and end time are all required, but one or more is missing.",
                None
            ).as_dict()
    # Initial value from GET, all fields optional filtering
    else:
        doctor_id = request.args.get('doctor_id')
        request_start_time = request.args.get('start_time')
        request_end_time = request.args.get('end_time')

    start_time = None
    end_time = None

    if request_start_time:
        start_time = datetime.strptime(request_start_time, '%Y-%d-%m %H:%M')

    if request_end_time:
        end_time = datetime.strptime(request_end_time, '%Y-%d-%m %H:%M')

    # Base Query for unfiltered GET request
    if not doctor_id and not start_time and not end_time:
        existing_appointments = Appointment.select()
    # Filtered GET request and conflict checks for Appointment creation
    else:
        expression = (Appointment.id >= 1)
        if doctor_id:
            expression &= (Appointment.doctor == doctor_id)
        if start_time:
            expression &= (Appointment.end_time >= start_time)
        if end_time:
            expression &= (Appointment.start_time <= end_time)
        existing_appointments = (Appointment.select().where(expression))

    # Handle GET request, returns filtered or complete Appointments
    if request.method == "GET":
        db.close()
        return HTTPReturn(
            200,
            "Successfully retrieved appointments.",
            [apt for apt in existing_appointments]
        ).as_dict()

    # Handle POST request, creates and Appointment record if no conflicts.
    else:
        day_of_week = start_time.weekday()

        doctor_hours = OfficeHour.select().where(
            (OfficeHour.doctor == doctor_id) & (OfficeHour.day_of_the_week == day_of_week)
        ).get()

        # Check if doctor has hours on requested day, and time requested is in those hours and
        # not during another appointment for that doctor. Returns error otherwise
        if not doctor_hours \
                or start_time.time() > doctor_hours.end_time\
                or end_time.time() < doctor_hours.start_time \
                or existing_appointments:
            return HTTPReturn(
                400,
                "Appointment unavailable at this time with this doctor.",
                None
            ).as_dict()

        # Create record
        new_apt = Appointment.create(
            start_time=start_time,
            end_time=end_time,
            doctor_id=doctor_id
        )

        db.close()
        doctor = Doctor.get(Doctor.id == doctor_id)
        return HTTPReturn(
            200,
            f"Appointment created from {new_apt.start_time} to {new_apt.end_time} with Dr. {doctor.last_name}",
            None
        ).as_dict()


@app.route('/appointments/get_first_available', methods=['GET'])
def get_first_available():
    """This endpoint receives GET requests. It takes an optional start_time
    filter and returns the first appointment with any doctor available after that time
    or now, in the case where no start_time is provided.

    Args:
        start_time (str): Start time expressed as a DateTime string in '%Y-%d-%m %H:%M' format.

    Returns:
        dict: a dictionary representation of the HTTPReturns class.

    """
    # Take optional start time or set to now
    request_start_time = request.args.get('time')
    if request_start_time:
        start_time = datetime.strptime(request_start_time, '%Y-%d-%m %H:%M')
    else:
        start_time = datetime.now()

    next_apt = Appointment.select().where(Appointment.start_time > start_time).get()

    # If now or provided start time is a weekend, shift to monday.
    if start_time.weekday() == 5:
        start_time = start_time + timedelta(days=2)
    elif start_time.weekday() == 6:
        start_time = start_time + timedelta(days=1)

    # Check if next appointment is far enough after start time and return start time if it is.
    if next_apt.start_time > start_time + timedelta(minutes=20) or not next_apt:
        db.close()
        return HTTPReturn(
            200,
            "Found acceptable start time.",
            start_time
        ).as_dict()

    # Make a reference for every doctor's individual schedule
    doctor_schedules = {
        doctor.id: Appointment.select().where(
            (Appointment.doctor == doctor.id) & (Appointment.start_time > start_time)
        ) for doctor in Doctor.select()
    }

    return doctor_schedules

    cur_best_time = start_time
    for doctor, schedule in doctor_schedules.items():
        # Get current daily schedule for a this doctor
        doc_cur_time = OfficeHour.select().where(
            (OfficeHour.day_of_the_week == cur_best_time.weekday()) & (OfficeHour.doctor == doctor)
        ).get()

        # Iterate over schedule
        for i, apt in enumerate(schedule):
            # The first appointment whose time is greater than the current marked time by enough time is returned
            if apt.start_time > cur_best_time + timedelta(minutes=20):
                db.close()
                return HTTPReturn(
                    200,
                    "Found acceptable start time.",
                    cur_best_time
                )
            # Set current marked time to the end of this appointment before continuing iteration.
            cur_best_time = apt.end_time

            # Check the next day for morning times before continuing to iterate over next appointments.
            next_day_index = cur_best_time.weekday() + 1 if cur_best_time.weekday < 5 else 1
            next_day_schedule = OfficeHour.select().where(
                (OfficeHour.day_of_the_week == next_day_index) & (OfficeHour.doctor == doctor.id)
            ).get()
            if cur_best_time + timedelta(minutes=20) >= doc_cur_time.end_time \
                    and schedule[i + 1].start_time > next_day_schedule.start_time + timedelta(minutes=20):
                db.close()
                return HTTPReturn(
                    200,
                    "Found acceptable start time.",
                    schedule[i + 1].start_time
                ).as_dict()

    # Default error condition return. Returning this means something is wrong.
    return HTTPReturn(
        500,
        "Could not locate the next available appointment time. Please modify your query or try again later.",
        None
    ).as_dict()


if __name__ == '__main__':
    app.run()
