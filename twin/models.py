from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import datetime

"""
UserBackend and UserManager are necessary classes to nicely integrate our
own `User` model object as a Django user entity.
"""
class UserBackend(object):
    def authenticate(self, username=None):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def get_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

class UserManager(BaseUserManager):
    def create_user(self, username, is_student, student=None):
        user = self.model(
            username=username,
            is_student=is_student,
            student=student
        )

        user.set_unusable_password()
        user.save()
        return user

"""
`User` represents a user that can log in via the Single Sign-on.
This can be a student (in which case it is linked to a Student object)
but it can also be an employee.
"""
class User(AbstractBaseUser):
    username = models.CharField(max_length=100, unique=True, db_index=True, primary_key=True)
    is_student = models.BooleanField()
    student = models.ForeignKey('Student', null=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'

    @property
    def is_staff(self):
        return not self.is_student

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def get_short_name(self):
        return self.username

    def get_full_name(self):
        return self.username

"""
A student that can be twinned, students can also log in as these.
They can be created by importing them via the admin interface,
or by the student by simply logging into the site.
"""
class Student(models.Model):
    student_number = models.IntegerField(primary_key=True, verbose_name="Studentnummer")
    name = models.CharField(max_length=200, verbose_name="Volledige naam")

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Studenten"
        ordering = ["name"]

"""
A twin is a match between two students who want to be in the same group next year.
The order of the students is not important. A twin is created when two students have eachother as preference. A twin can end if one of the students changes it preference, in that case
"""
""" TODO: Have a better understanding of how students should be matched to terms
class Twin(models.Model):
    student1 = models.ForeignKey('Student', related_name='student1')
    student2 = models.ForeignKey('Student', related_name='student2')

    start_date = models.DateField()
    end_date = models.DateField(null=True)
"""

"""
A preference contains which other student is the preferred choice for a particular student.
A student can choose anyone as a preference, but is only twinned when the preference is reciprocal.
"""
class Preference(models.Model):
    student = models.ForeignKey('Student')
    preference_for = models.ForeignKey('Student', related_name='preference_for', verbose_name='Heeft voorkeur voor')

    def __unicode__(self):
        return u'{0} heeft voorkeur voor {1}'.format(self.student, self.preference_for)

    class Meta:
        verbose_name = "Voorkeur"
        verbose_name_plural = "Voorkeuren"
        ordering = ["student"]

class PreferenceHistory(models.Model):
    student = models.ForeignKey('Student')
    preference_for = models.ForeignKey('Student', related_name='preferencehistory_for', verbose_name='Heeft voorkeur voor')
    date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'{0} heeft/had voorkeur voor {1}'.format(self.student, self.preference_for)

    class Meta:
        verbose_name = "Voorkeur geschiedenis"
        verbose_name_plural = "Voorkeuren geschiedenis"
        ordering = ["student"]
