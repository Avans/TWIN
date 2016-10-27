# -*- coding: utf-8 -*-

from django.test import TestCase, Client
from .models import Student, Term, User, Preference
from .admin import GoogleDrive, get_difference, sort_by_sheet
import json

client = Client()

"""
Tests the /api/students list that should return a list of all the students
"""
class ApiStudentsTest(TestCase):
    def setUp(self):
        self.paul = Student.objects.create(student_number=1, name='Paul Wagener')
        self.reinier = Student.objects.create(student_number=2, name='Reinier Dickhout')
        self.bob = Student.objects.create(student_number=3, name=u'Bõb van der PUTTEN') # test unicode

        self.user = User.objects.create_user(username='pwagener', is_student=True, student=self.paul)
        client.login(username=self.user.username)

        """
        The result should be the other two students
        Paul is excluded because that is the logged in user
        Bob should be firsed because it is alphabetical
        """
        self.expected = [
            {'student_number': 3, 'name': u'Bõb van der PUTTEN'},
            {'student_number': 2, 'name': 'Reinier Dickhout'},
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

        student = Student.objects.create(student_number=1, name='Paul Wagener')

        self.user_student = User.objects.create_user(username='pwagener', is_student=True, student=student)
        self.user_teacher = User.objects.create_user(username='agehring', is_student=False)

    def test_student(self):
        client.login(username=self.user_student.username)

        expected = {'username': 'pwagener', 'student': {'student_number': 1, 'name': 'Paul Wagener'}}

        response = client.get('/api/user')
        self.assertEqual(expected, response.json())

    def test_teacher(self):
        client.login(username=self.user_teacher.username)

        expected = {'username': 'agehring'}

        response = client.get('/api/user')
        self.assertEqual(expected, response.json())

"""
Tests the /api/preference url
Should return information about the current preference and be able to POST new preference information
"""
class ApiPreferenceTest(TestCase):
    def setUp(self):
        self.paul = Student.objects.create(student_number=1, name='Paul Wagener')
        self.bart = Student.objects.create(student_number=2, name='Bart Gelens')
        self.stijn = Student.objects.create(student_number=3, name='Stijn Smulders')
        self.user = User.objects.create_user(username='pwagener', is_student=True, student=self.paul)

        client.login(username=self.user.username)

    def test_no_preference(self):
        response = client.get('/api/preference')
        self.assertEqual(None, response.json())

    def test_has_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        expected = {
            'student_number': 2,
            'name': 'Bart Gelens'
        }

        response = client.get('/api/preference')
        self.assertEqual(expected, response.json())

    def test_has_reciprocal_preference(self):
        Preference.objects.create(student=self.bart, preference_for=self.paul)
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        expected = {
            'student_number': 2,
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
        response = client.post('/api/preference', json.dumps({'student_number': 2}), content_type='application/json')

        self.assertTrue(Preference.objects.filter(student=self.paul, preference_for=self.bart).exists())

        # Check that the POST response behaves like a GET
        expected = {
            'student_number': 2,
            'name': 'Bart Gelens'
        }
        self.assertEqual(expected, response.json())

    def test_post_overrides_previous_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.stijn)

        client.post('/api/preference', json.dumps({'student_number': 2}), content_type='application/json')

        self.assertEquals(1, Preference.objects.all().count())
        self.assertTrue(Preference.objects.filter(student=self.paul, preference_for=self.bart).exists())

    def test_post_remove_previous_preference(self):
        Preference.objects.create(student=self.paul, preference_for=self.bart)

        client.post('/api/preference', json.dumps(None), content_type='application/json')

        self.assertEquals(0, Preference.objects.all().count())

    def test_post_no_self_preference(self):
        client.post('/api/preference', json.dumps({'student_number': 1}), content_type='application/json')

        self.assertEquals(0, Preference.objects.all().count())

class GoogleDriveTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.googledrive = GoogleDrive()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_get_students(self):
        students = self.googledrive.get_students('1VSPpEuiSAfmAEhzpR11T6qRr6Dm32HWx3k9fW1hlSJw')
        self.assertEquals(
            [{'sheet': 'IN01', 'student_number': 2097174, 'name': u'Jorrit Aärts'},
             {'sheet': 'IN01', 'student_number': 2113371, 'name': 'Rob van den Akker'},
             {'sheet': 'IN01', 'student_number': 2098472, 'name': 'Quirijn Akkermans'},
             {'sheet': 'SWA13', 'student_number': 2077073, 'name': 'Bert Alderliesten'},
             {'sheet': 'SWA13', 'student_number': 2079014, 'name': 'Mark Arnoldussen'}
            ], students)

class GetDifferenceTest(TestCase):

    def setUp(self):
        Student.objects.create(student_number=1, name='Paul Wagener')
        Student.objects.create(student_number=2, name='Bart Gelens')
        Student.objects.create(student_number=4, name='Bob van der Putten')

    def test_get_difference(self):

        changed, deleted = get_difference([
            {'student_number': 1, 'name': 'Paul Blapener', 'sheet': 'IN01'},
            {'student_number': 2, 'name': 'Bart Gelens', 'sheet': 'IN02'},
            {'student_number': 3, 'name': 'Stijn Smulders', 'sheet': 'IN03'},
        ])

        self.assertEquals([
            {'student_number': 1, 'name': 'Paul Blapener', 'sheet': 'IN01', 'change': 'update'},
            {'student_number': 3, 'name': 'Stijn Smulders', 'sheet': 'IN03', 'change': 'insert'},
        ], changed)

        self.assertEquals([{'student_number': 4, 'name': 'Bob van der Putten'}],
            deleted)


class SortBySheetTest(TestCase):
    def test_sort_by_sheet(self):
        students = sort_by_sheet([
            {'student_number': 1, 'name': 'Paul Wagener', 'sheet': 'IN01'},
            {'student_number': 2, 'name': 'Bart Gelens', 'sheet': 'IN01'},
            {'student_number': 3, 'name': 'Stijn Smulders', 'sheet': 'IN02'}])

        self.assertEquals(students,
            [{'sheet': 'IN01', 'students': [
                {'student_number': 1, 'name': 'Paul Wagener'},
                {'student_number': 2, 'name': 'Bart Gelens'}
                ]},
            {'sheet': 'IN02', 'students': [
                {'student_number': 3, 'name': 'Stijn Smulders'}
                ]}
            ])
