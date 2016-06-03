from django.contrib.auth import get_user_model, authenticate, login as django_login
User = get_user_model()
from django.http import HttpResponse
from django.http import HttpResponseRedirect
import oauth2 as oauth
import cgi, json
import twin.secrets as secrets
from twin.models import Student

REQUEST_TOKEN_URL = 'https://publicapi.avans.nl/oauth/request_token?oauth_callback=http://%s/oauth/callback'
ACCESS_TOKEN_URL = 'https://publicapi.avans.nl/oauth/access_token'
AUTHORIZE_URL = 'https://publicapi.avans.nl/oauth/saml.php?oauth_token=%s'

consumer = oauth.Consumer(secrets.AVANS_KEY, secrets.AVANS_SECRET)
client = oauth.Client(consumer)

def login(request):
    resp, content = client.request(REQUEST_TOKEN_URL % request.get_host(), "GET")

    if resp['status'] != '200':
        raise Exception("Invalid response from oauth")

    request.session['request_token'] = dict(cgi.parse_qsl(content))

    url = AUTHORIZE_URL % (request.session['request_token']['oauth_token'])
    return HttpResponseRedirect(url)

def callback(request):
    token = oauth.Token(request.session['request_token']['oauth_token'], request.session['request_token']['oauth_token_secret'])
    token.set_verifier(request.GET['oauth_verifier'])

    client = oauth.Client(consumer, token)

    resp, content = client.request(ACCESS_TOKEN_URL, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response from Avans.")

    access_token = dict(cgi.parse_qsl(content))
    token = oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret'])
    client = oauth.Client(consumer, token)

    # Check if the user is an employee or not
    resp, content = client.request('https://publicapi.avans.nl/oauth/people/@me', 'GET')
    data = json.loads(content)
    is_student = data['employee'] <> 'true'
    first_name = data['name']['givenName']
    last_name = data['name']['familyName']

    # Get the username and student number
    resp, content = client.request('https://publicapi.avans.nl/oauth/studentnummer/', 'GET')
    data = json.loads(content)[0]

    username = data['inlognaam'].lower()
    student_number = int(data['studentnummer'])

    # Create or retrieve the corresponding user entry
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username,
                                        is_student=is_student,
                                        student=None)

    # Create a new Student entry if it is not yet preloaded into the database
    if student_number > 0 and user.student == None:
        student, created = Student.objects.get_or_create(student_number=student_number,
                                                defaults={'first_name': first_name,
                                                          'last_name': last_name})
        user.student = student
        user.save()

    # Log the user in
    user = authenticate(username=username)
    django_login(request, user)

    # Redirect to the main site
    return HttpResponseRedirect('/')