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
                'student_number': request.user.student.student_number,
                'name': request.user.student.name
            }
    return HttpResponse(json.dumps(user), content_type='application/json')

"""
GET:  Returns which other student the (student)user has as preference.
      It does so with the following JSON:
      {
         'student_number': <student number>
         'name': <full name>
         'reciprocal': True (only if that other student has you as a preference)
      }
      or `null` if the student has no preference

POST: Allows a student to set a new preference, the request body has to have the following format:
      {
          'student_number': <student number>
      }
      or `null`
      It returns the new preference as described in GET in the response
"""
@login_required
@csrf_exempt
def api_preference(request):
    # For teachers this API has undefined behaviour, simply return null
    if not request.user.student:
        return HttpResponse(json.dumps(None), content_type='application/json')

    # Save the preference
    if request.method == 'POST':
        # Remove any previous preference
        Preference.objects.filter(student=request.user.student).delete()

        content = json.loads(request.body)

        if isinstance(content, dict) and 'student_number' in content:
            student_number = int(content['student_number'])

            if student_number <> request.user.student.student_number:
                preference = Preference()
                preference.student = request.user.student
                preference.preference_for = Student.objects.get(student_number=student_number)
                preference.save()

    # Find the preference
    try:
        preference = Preference.objects.get(student=request.user.student)
    except Preference.DoesNotExist:
        return HttpResponse(json.dumps(None), content_type='application/json')

    # Output to user
    preference_json = {
        'student_number': preference.preference_for.student_number,
        'name': preference.preference_for.name
    }

    if Preference.objects.filter(student=preference.preference_for, preference_for=request.user.student):
        preference_json['reciprocal'] = True

    return HttpResponse(json.dumps(preference_json), content_type='application/json')



"""
Returns a list of students that the logged in student can
"""
@login_required
def api_students(request):
    if request.user.student:
        student_number = request.user.student.student_number
        students = Student.objects.raw('SELECT student_number, name, EXISTS(SELECT 1 FROM twin_preference WHERE student_id=student_number AND preference_for_id=%s) AS reciprocal FROM twin_student WHERE student_number<>%s ORDER BY name', [student_number, student_number])
    else:
        students = Student.objects.all().order_by('name')

    def make_json(student):
        data = {'name': student.name, 'student_number': student.student_number}
        if hasattr(student, 'reciprocal') and student.reciprocal:
            data['reciprocal'] = True
        return data

    students = [make_json(student) for student in students]

    return HttpResponse(json.dumps(students), content_type='application/json')

import random
def debug_quickswitch(request, student_number):
    student = Student.objects.get(student_number=student_number)
    try:
        user = User.objects.get(student=student)
    except:
        user = User()
        user.username = student_number
        user.student = student
        user.is_student = True
        user.save()

    user = authenticate(username=user.username)
    login(request, user)
    return HttpResponseRedirect('/')
