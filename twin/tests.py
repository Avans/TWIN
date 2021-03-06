# -*- coding: utf-8 -*-

from django.test import TestCase, Client
from .models import Student, User, Preference
from .admin import GoogleDrive, get_difference, sort_by_sheet, get_pairs, array_excel_output
from .avans import get_user
import json

client = Client()

class LoginGetUserTest(TestCase):
    def setUp(self):
        self.bob = Student.objects.create(student_number=1, name='Bob van der Putten')
        self.user = User.objects.create_user(username='bacputte', is_student=True, student=self.bob)

    def test_normal_login(self):
        user = get_user('bacputte', 'Bob van der Putten', 'bac.putten@avans.nl', True, 1)
        self.assertEquals(user, self.user)
        self.assertEquals(1, Student.objects.count())
        self.assertEquals(1, User.objects.count())

    def test_new_login(self):
        user = get_user('pwagener', 'Paul Wagener', 'p.wagener@avans.nl', True, 2)
        self.assertNotEqual(user, self.user)
        self.assertIsNotNone(user.student)
        self.assertEquals(2, user.student.student_number)
        self.assertEquals('Paul Wagener', user.student.name)
        self.assertEquals('p.wagener@avans.nl', user.student.email)
        self.assertEquals(2, Student.objects.count())
        self.assertEquals(2, User.objects.count())


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
            [{'sheet': 'IN01', 'student_number': 2097174, 'name': u'Jorrit Aärts', 'email': 'gjrm.aarts@student.avans.nl'},
             {'sheet': 'IN01', 'student_number': 2113371, 'name': 'Rob van den Akker', 'email': 'rma.vandenakker@student.avans.nl'},
             {'sheet': 'IN01', 'student_number': 2098472, 'name': 'Quirijn Akkermans', 'email': 'qb.akkermans@student.avans.nl'},
             {'sheet': 'SWA13', 'student_number': 2077073, 'name': 'Bert Alderliesten', 'email': ''},
             {'sheet': 'SWA13', 'student_number': 2079014, 'name': 'Mark Arnoldussen', 'email': ''}
            ], students)

class GetDifferenceTest(TestCase):

    def setUp(self):
        Student.objects.create(student_number=1, name='Paul Wagener')
        Student.objects.create(student_number=2, name='Bart Gelens')
        Student.objects.create(student_number=4, name='Bob van der Putten', email='bob@avans.nl')

        self.students = [
            {'student_number': 1, 'name': 'Paul Wagener', 'sheet': 'IN01', 'email': ''},
            {'student_number': 2, 'name': 'Bart Gelens', 'sheet': 'IN02', 'email': ''},
            {'student_number': 4, 'name': 'Bob van der Putten', 'sheet': 'IN03', 'email': 'bob@avans.nl'},
        ]

    def test_no_change(self):
        changed, deleted = get_difference(self.students)
        self.assertEquals([], changed)
        self.assertEquals([], deleted)

    def test_change_name(self):
        self.students[0]['name'] = 'Paul Blapener'
        changed, deleted = get_difference(self.students)

        self.assertEquals([{
            'student_number': 1,
            'name': 'Paul Blapener',
            'sheet': 'IN01',
            'change': 'update',
            'email': '',
            }], changed)
        self.assertEquals([], deleted)

    def test_add_email(self):
        self.students[0]['email'] = 'p.wagener@avans.nl'
        changed, deleted = get_difference(self.students)

        self.assertEquals([{
            'student_number': 1,
            'name': 'Paul Wagener',
            'sheet': 'IN01',
            'change': 'update',
            'email': 'p.wagener@avans.nl',
            }], changed)
        self.assertEquals([], deleted)

    def test_delete(self):
        del self.students[2] # Bob
        changed, deleted = get_difference(self.students)

        self.assertEquals([], changed)
        self.assertEquals([{
            'student_number': 4,
            'name': 'Bob van der Putten'
            }], deleted)


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

class GetPairsTest(TestCase):
    def setUp(self):
        s1 = Student.objects.create(student_number=1, name='Paul Wagener')
        s2 = Student.objects.create(student_number=2, name='Bart Gelens')
        s3 = Student.objects.create(student_number=3, name='Reinier Dickhout')
        s4 = Student.objects.create(student_number=4, name='Bob van der Putten')
        s5 = Student.objects.create(student_number=5, name='Andre Gehring')

        self.p1a = Preference.objects.create(student=s1, preference_for=s2)
        self.p1b = Preference.objects.create(student=s2, preference_for=s1)
        self.p2a = Preference.objects.create(student=s3, preference_for=s4)
        self.p2b = Preference.objects.create(student=s4, preference_for=s3)
        self.p3 = Preference.objects.create(student=s5, preference_for=s1)

        self.j1 = {'student_number': 1, 'name': 'Paul Wagener'}
        self.j2 = {'student_number': 2, 'name': 'Bart Gelens'}
        self.j3 = {'student_number': 3, 'name': 'Reinier Dickhout'}
        self.j4 = {'student_number': 4, 'name': 'Bob van der Putten'}
        self.j5 = {'student_number': 5, 'name': 'Andre Gehring'}


    def test_simple_pair(self):
        pairs = get_pairs([self.j1, self.j2])

        self.assertEquals(1, len(pairs))
        self.assertEquals(self.p1a, pairs[0])

    def test_multiple_pairs(self):
        pairs = get_pairs([self.j1, self.j2, self.j3, self.j4])

        self.assertEquals(2, len(pairs))
        self.assertEquals(self.p1a, pairs[0])
        self.assertEquals(self.p2a, pairs[1])

    def test_pairs_not_in_given_students(self):
        pairs = get_pairs([self.j1, self.j3, self.j5])

        self.assertEquals(0, len(pairs))

class ArrayExcelOutputTest(TestCase):

    def setUp(self):
        s1 = Student.objects.create(student_number=1, name='Paul Wagener', email='p.wagener@avans.nl')
        s2 = Student.objects.create(student_number=2, name='Bart Gelens')
        s3 = Student.objects.create(student_number=3, name='Reinier Dickhout')
        s4 = Student.objects.create(student_number=4, name='Bob van der Putten')
        s5 = Student.objects.create(student_number=5, name='André Gehring')

        self.p1a = Preference.objects.create(student=s1, preference_for=s2)
        self.p1b = Preference.objects.create(student=s2, preference_for=s1)
        self.p2a = Preference.objects.create(student=s3, preference_for=s4)
        self.p2b = Preference.objects.create(student=s4, preference_for=s3)

        self.students = [
            {'student_number': 1, 'name': 'Paul Wagener', 'email': 'p.wagener@avans.nl', 'sheet': 'IN01'},
            {'student_number': 2, 'name': 'Bart Gelens', 'email': '', 'sheet': 'IN01'},
            {'student_number': 3, 'name': 'Reinier Dickhout', 'email': '', 'sheet': 'IN01'},
            {'student_number': 4, 'name': 'Bob van der Putten', 'email': '', 'sheet': 'SWA13'},
            {'student_number': 5, 'name': 'Stijn Smulders', 'email': '', 'sheet': 'IN01'},
            {'student_number': 6, 'name': 'Andre Gehring', 'email': '', 'sheet': 'Zwervers'}
        ]

        # Students not in sheet, but in database
        s6 = Student.objects.create(student_number=6, name='Martin Rodenburg')
        s7 = Student.objects.create(student_number=7, name='Han van Osch')
        Preference.objects.create(student=s6, preference_for=s7)
        Preference.objects.create(student=s7, preference_for=s6)

    def test_normal(self):

        output = array_excel_output(self.students, 'IN01')

        self.assertEquals(
            [
                ['1a', 1, 'Paul Wagener',       'p.wagener@avans.nl', 'IN01', 'koppel'],
                ['1b', 2, 'Bart Gelens',        '',                   'IN01', 'koppel'],
                ['2a', 3, 'Reinier Dickhout',   '',                   'IN01', 'mismatch'],
                ['2b', 4, 'Bob van der Putten', '',                   'SWA13', 'mismatch'],
                ['3',  5, 'Stijn Smulders',     '',                   'IN01', 'single']
            ], output)

    def test_just_mismatch(self):
        output = array_excel_output(self.students, 'SWA13')
        self.assertEquals(
            [
                ['1a', 3, 'Reinier Dickhout',   '', 'IN01', 'mismatch'],
                ['1b', 4, 'Bob van der Putten', '', 'SWA13', 'mismatch'],
            ], output)

