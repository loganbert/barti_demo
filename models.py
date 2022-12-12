from peewee import *

db = SqliteDatabase('data.db')


class Doctor(Model):
    first_name = CharField(null=False)
    last_name = CharField(null=False)

    class Meta:
        database = db


class OfficeHour(Model):
    start_time = TimeField(null=False)
    end_time = TimeField(null=False)
    day_of_the_week = IntegerField(null=False)
    doctor = ForeignKeyField(Doctor, backref='office_hours', null=False)

    class Meta:
        database = db


class Appointment(Model):
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)
    doctor = ForeignKeyField(Doctor, backref='office_hours', null=False)

    class Meta:
        database = db
