from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login, logout as django_logout
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.core import serializers
import oauth2 as oauth
import cgi, json, secrets, avans
from models import Preference, Student
User = get_user_model()

def home(request):
    if not request.user.is_authenticated():
        return avans.login(request)
    else:
        return HttpResponse(open('public/index.html').read())

def logout(request):
    django_logout(request)
    return HttpResponseRedirect('/')

@login_required
def api_user(request):
    user = {'username': request.user.username}

    if request.user.student <> None:
            user['student'] = {
                'email': request.user.student.email,
                'name': request.user.student.name
            }
    return HttpResponse(json.dumps(user), content_type='application/json')

@login_required
@csrf_exempt
def api_preference(request):

    if request.method == 'POST':
        # Save a new preference
        student_number = json.loads(request.body)['student_number']

        preference = Preference()
        preference.student = request.user.student
        preference.preference_for_id = student_number#Student.objects.get(student_number=student_number)
        preference.save()
        return HttpResponse(json.dumps(None), content_type='application/json')
    else:
        if request.user.student == None:
            return HttpResponse(json.dumps(None), content_type='application/json')

        try:
            preference_for = Preference.objects.get(student=request.user.student)
        except Preference.DoesNotExist:
            print 'doesnotexist'
            return HttpResponse(json.dumps(None), content_type='application/json')

        preference_for = {
            'student_number': preference_for.student_number,
            'name': preference_for.first_name + ' ' + preference_for.last_name
        }

        return HttpResponse(json.dumps(preference_for), content_type='application/json')

"""
Returns a list of students that the logged in student can
"""
@login_required
def api_students(request):
    if request.user.student:
        student_number = request.user.student.student_number
        term_id = request.user.student.term.id

        students = Student.objects.raw('SELECT student_number, name, email, EXISTS(SELECT 1 FROM twin_preference WHERE student_id=student_number AND preference_for_id=%s) AS reciprocal FROM twin_student WHERE term_id=%s AND student_number<>%s ORDER BY name', [student_number, term_id, student_number])
    else:
        students = Student.objects.all()

    def make_json(student):
        data = {'name': student.name, 'email': student.email}
        if hasattr(student, 'reciprocal') and student.reciprocal:
            data['reciprocal'] = True
        return data

    students = [make_json(student) for student in students]

    return HttpResponse(json.dumps(students), content_type='application/json')

import random
def debug_quickswitch(request, email):
    student = Student.objects.get(email=email)
    try:
        user = User.objects.get(student=student)
    except:
        user = User()
        user.username = email
        user.student = student
        user.is_student = True
        user.save()

    user = authenticate(username=user.username)
    login(request, user)
    return HttpResponseRedirect('/')
