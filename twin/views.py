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
                'name': request.user.student.first_name + ' ' + request.user.student.last_name
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
        print request.user.student
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
    student_number = request.user.student.student_number

    students = Student.objects.raw('SELECT student_number, name, email, EXISTS(SELECT 1 FROM twin_preference WHERE student_id=student_number AND preference_for_id=%s) AS reciprocal FROM twin_student ORDER BY name', [student_number])

    def make_json(student):
        data = {'name': student.name, 'email': student.email}
        if student.reciprocal:
            data['reciprocal'] = True
        return data

    students = [make_json(student) for student in students]

    return HttpResponse(json.dumps(students), content_type='application/json')

def debug_quickswitch(request, student_id):
    try:
        user = User.objects.get(student_id=student_id)
    except:
        user = User()
        user.username = student_id
        user.student_id = student_id
        user.is_student = True
        user.save()

    user = authenticate(username=user.username)
    login(request, user)
    return HttpResponseRedirect('/')
