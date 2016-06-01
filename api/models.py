from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import AbstractBaseUser



class User(AbstractBaseUser):
    username = models.CharField(max_length=100, unique=True, primary_key=True)
    is_student = models.BooleanField()
    student = models.ForeignKey('Student')

    USERNAME_FIELD = 'username'

"""
    A student is
"""
class Student(models.Model):
    student_number = models.IntegerField(primary_key=True)

    first_name = models.CharField(max_length=200)
    last_name_prefix = models.CharField(max_length=200) # Tussenvoegsel
    last_name = models.CharField(max_length=200)

class Twin(models.Model):
    student1 = models.ForeignKey('Student', related_name='student1')
    student2 = models.ForeignKey('Student', related_name='student2')

    start_date = models.DateField()
    end_date = models.DateField(null=True)

class Preference(models.Model):
    student = models.ForeignKey('Student')
    preference_for = models.ForeignKey('Student', related_name='preference_for')


class Term(models.Model):
    quarter = models.IntegerField()
    year = models.IntegerField()

    start_date = models.DateField()
    end_date = models.DateField()
