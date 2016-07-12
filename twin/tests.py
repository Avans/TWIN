# -*- coding: utf-8 -*-

from django.test import TestCase, Client
from .models import Student, Term, User, Preference
import json

client = Client()

"""
Tests the /api/students list that should return a list of all the students
"""
class ApiStudentsTest(TestCase):
    def setUp(self):
        """
        Set up a test scenario with two terms, one that contains the first three students
        and the other containing the fourth one.

        """
        self.term1 = Term.objects.create(year=2016, quarter=1)
        self.term2 = Term.objects.create(year=2016, quarter=2)

        self.paul = Student.objects.create(student_number=1, email='paul@avans.nl', name='Paul Wagener', term=self.term1)
        self.reinier = Student.objects.create(student_number=2, email='reinier@avans.nl', name='Reinier Dickhout', term=self.term1)
        self.bob = Student.objects.create(student_number=3, email='bob@avans.nl', name=u'Bõb van der PUTTEN', term=self.term1) # test unicode
        self.andre = Student.objects.create(student_number=4, email='andre@avans.nl', name=u'André Gehring', term=self.term2)

        self.user = User.objects.create_user(username='pwagener', is_student=True, student=self.paul)
        client.login(username=self.user.username)

        """
        The result should be the other two students from our term
        Paul is excluded because that is the logged in user
        and Andre is excluded because he is in another term
        """
        self.expected = [
            {u'email': u'bob@avans.nl', u'name': u'Bõb van der PUTTEN'},
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
        self.expected[1]['reciprocal'] = True

        response = client.get('/api/students')
        self.assertEqual(self.expected, response.json())

    def test_teacher(self):
        admin = User.objects.create_user(username='admin', is_student=False)
        client.login(username=admin.username)

        # Undefined behaviour, but it shouldn't crash
        client.get('/api/students')

"""
Tests the /api/user url, should return information about the current logged in user
"""
class ApiUserTest(TestCase):
    def setUp(self):

        student = Student.objects.create(student_number=1, email='paul@avans.nl', name=u'Paul Wagener', term=Term.objects.create(year=2016, quarter=1))

        self.user_student = User.objects.create_user(username='pwagener', is_student=True, student=student)

        self.user_teacher = User.objects.create_user(username='agehring', is_student=False)

    def test_student(self):
        client.login(username=self.user_student.username)

        expected = {"username": "pwagener", "student": {'email': 'paul@avans.nl', 'name': 'Paul Wagener'}}

        response = client.get('/api/user')
        self.assertEqual(expected, response.json())

    def test_teacher(self):
        client.login(username=self.user_teacher.username)

        expected = {"username": "agehring"}

        response = client.get('/api/user')
        self.assertEqual(expected, response.json())

"""
Tests the /api/preference url
Should return information about the current preference and be able to POST new preference information
"""
class ApiPreferenceTest(TestCase):
    def setUp(self):
        term = Term.objects.create(year=2016, quarter=1)

        self.paul = Student.objects.create(student_number=1, email='paul@avans.nl', name=u'Paul Wagener', term=term)
        self.bart = Student.objects.create(student_number=2, email='bart@avans.nl', name=u'Bart Gelens', term=term)
        self.stijn = Student.objects.create(student_number=3, email='stijn@avans.nl', name=u'Stijn Smulders', term=term)
        self.user = User.objects.create_user(username='pwagener', is_student=True, student=self.paul)

        client.login(username=self.user.username)

    def test_no_preference(self):
        response = client.get('/api/preference')
        self.assertEqual(None, response.json())

    def test_has_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        expected = {
            'email': 'bart@avans.nl',
            'name': 'Bart Gelens'
        }

        response = client.get('/api/preference')
        self.assertEqual(expected, response.json())

    def test_has_reciprocal_preference(self):
        Preference.objects.create(student=self.bart, preference_for=self.paul)
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        expected = {
            'email': 'bart@avans.nl',
            'name': 'Bart Gelens',
            'reciprocal': True
        }

        response = client.get('/api/preference')
        self.assertEqual(expected, response.json())

    def test_teacher(self):
        teacher = User.objects.create(username='teacher', is_student=False)
        client.login(username=teacher.username)

        # Undefined behaviour, but shouldn't crash
        client.get('/api/preference')

    def test_post_preference(self):
        response = client.post('/api/preference', json.dumps({'email': 'bart@avans.nl'}), content_type='application/json')

        self.assertTrue(Preference.objects.filter(student=self.paul, preference_for=self.bart).exists())

        # Check that the POST response behaves like a GET
        expected = {
            'email': 'bart@avans.nl',
            'name': 'Bart Gelens'
        }
        self.assertEqual(expected, response.json())

    def test_post_overrides_previous_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.stijn)

        client.post('/api/preference', json.dumps({'email': 'bart@avans.nl'}), content_type='application/json')

        self.assertEquals(1, Preference.objects.all().count())
        self.assertTrue(Preference.objects.filter(student=self.paul, preference_for=self.bart).exists())

    def test_post_remove_previous_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        client.post('/api/preference', json.dumps(None), content_type='application/json')

        self.assertEquals(0, Preference.objects.all().count())

    def test_post_no_self_preference(self):
        client.post('/api/preference', json.dumps({'email': 'paul@avans.nl'}), content_type='application/json')

        self.assertEquals(0, Preference.objects.all().count())




