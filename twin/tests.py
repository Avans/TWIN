# -*- coding: utf-8 -*-

from django.test import TestCase, Client
from .models import Student, User, Preference
import json

client = Client()

"""
Tests the /api/students list that should return a list of all the students
"""
class ApiStudentsTest(TestCase):
    def setUp(self):
        self.paul = Student.objects.create(student_number=1, email='paul@avans.nl', name='Paul Wagener')
        self.reinier = Student.objects.create(student_number=2, email='reinier@avans.nl', name='Reinier Dickhout')
        self.bob = Student.objects.create(student_number=3, email='bob@avans.nl', name='Bob van der Putten')

        self.user = User.objects.create_user(username='pwagener', is_student=True, student=self.paul)
        client.login(username=self.user.username)

        self.expected = [
            {u'email': u'bob@avans.nl', u'name': u'Bob van der Putten'},
            {u'email': u'paul@avans.nl', u'name': u'Paul Wagener'},
            {u'email': u'reinier@avans.nl', u'name': u'Reinier Dickhout'},
        ]



    def test_standard(self):
        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())

    def test_someone_preferred_us(self):
        """
        Bob has chosen us as a preference,
        that should mean that he should be marked as reciprocal
        """
        Preference.objects.create(student=self.bob, preference_for=self.paul)
        self.expected[0]['reciprocal'] = True

        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())

    def test_someone_preferred_not_us(self):
        """
        Bob has chosen someone else as a preference, no-one should be marked as reciprocal
        """
        Preference.objects.create(student=self.bob, preference_for=self.reinier)

        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())

    def test_we_preferred_someone(self):
        """
        We ourselves have given a preference, again, no-one should be marked as reciprocal
        """
        Preference.objects.create(student=self.bob, preference_for=self.reinier)

        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())

    def test_multiple_students_preferred_us(self):
        """
        Multiple students preferred us, all should be marked as reciprocal
        """
        Preference.objects.create(student=self.bob, preference_for=self.paul)
        Preference.objects.create(student=self.reinier, preference_for=self.paul)
        self.expected[0]['reciprocal'] = True
        self.expected[2]['reciprocal'] = True

        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())
