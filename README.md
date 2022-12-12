# Appointments API

## Installation
Clone this repository, set up a new virtual environment, activate it, then run 
`pip install -r requirements.txt` from the project root. 

Data should be initialized prior to working with the API. For convenience
a sqlite DB is included in this repository with doctors, their office hours,
and three sample appointments.

A test server can be run by executing `flask --debug run`. 
To convert this to a production application, review the 
[Flask documentation on deployment](https://flask.palletsprojects.com/en/2.2.x/deploying/).

## Concepts
This API provides three core functions:
* GET /appointments returns all appointments and accepts three optional filters:
  * doctor_id: The id of the doctor whose availability you would like to check
  * start_time: The earliest appointment time you want to check
  * end_time: The latest appointment time you want to check
* POST /appointments creates an appointment using three required parameters:
  * doctor_id: The id of the doctor with whom you'd like to book an appointment.
  * start_time: The start time of the appointment you'd like to book
  * end_time: The end time of the appointment you'd like to book
* GET /appointments/get_first_available returns the earliest time an appointment
slot at least 20 minutes long is available starting either now, or after an optional
time parameter.

## OpenAPI Specification

```
openapi: 3.0.0
servers: []
info:
  description: Appointments API
  version: "1.0.0"
  title: Appointments API
  contact:
    email: logan.bertram@protonmail.com
  license:
    name: MIT
    url: 'https://www.mit.edu/~amini/LICENSE.md'
paths:
  /appointments:
    get:
      summary: gets appointments with optional filters
      operationId: search_appointments
      description: |
        Find existing appointments using the provided optional parameters.
      parameters:
        - in: query
          name: doctor_id
          description: ID of a doctor to search
          required: false
          schema:
            type: string
        - in: query
          name: start_time
          description: earliest time to search for appointemnts
          schema:
            type: string
            format: '%Y-%d-%m %H:%M'
        - in: query
          name: end_time
          description: latest time to search for appointments
          schema:
            type: string
            format: '%Y-%d-%m %H:%M'
      responses:
        '200':
          description: found 0 or more appointments matching criteria
          content:
            application/json:
              schema:
                type: object
    post:
      summary: create an appointment
      operationId: create_appointment
      description: Uses the required parameters to create an appointment, provided one is available with the requested doctor in the requested times.
      parameters:
        - in: query
          name: doctor_id
          description: ID of a doctor with whom to set appointment
          required: true
          schema:
            type: string
        - in: query
          name: start_time
          description: desired appointment start time
          required: true
          schema:
            type: string
            format: '%Y-%d-%m %H:%M'
        - in: query
          name: end_time
          description: desired appointment end time
          required: true
          schema:
            type: string
            format: '%Y-%d-%m %H:%M'
      responses:
        '200':
          description: appointment created
        '400':
          description: appointment unavailable with this doctor at this time
  /appointments/get_first_available:
    get:
      summary: get first appointment available
      operationId: search_first_appointment
      description: |
        Find the earliest available appointment time with an optional
        time to begin looking after.
      parameters:
        - in: query
          name: time
          description: time after which to search for available appointments
          required: false
          schema:
            type: string
            format: '%Y-%d-%m %H:%M'
      responses:
        '200':
          description: found next appointment time
```

## License
[MIT License](https://www.mit.edu/~amini/LICENSE.md)