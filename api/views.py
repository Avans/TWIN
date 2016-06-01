from django.contrib.auth.models import User, Group
from rest_framework import viewsets
#from api.serializers import UserSerializer
import oauth2 as oauth
import cgi, json
import twin.secrets as secrets
from django.http import HttpResponse
from django.http import HttpResponseRedirect


"""
class UserViewSet(viewsets.ModelViewSet):

    API endpoint that allows users to be viewed or edited.

    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
"""

REQUEST_TOKEN_URL = 'https://publicapi.avans.nl/oauth/request_token?oauth_callback=http://%s/oauth/callback'
ACCESS_TOKEN_URL = 'https://publicapi.avans.nl/oauth/access_token'
AUTHORIZE_URL = 'https://publicapi.avans.nl/oauth/saml.php?oauth_token=%s'

consumer = oauth.Consumer(secrets.AVANS_KEY, secrets.AVANS_SECRET)
client = oauth.Client(consumer)

def avans_login(request):
    resp, content = client.request(REQUEST_TOKEN_URL % request.get_host(), "GET")

    if resp['status'] != '200':
        raise Exception("Invalid response from oauth")

    request.session['request_token'] = dict(cgi.parse_qsl(content))

    url = AUTHORIZE_URL % (request.session['request_token']['oauth_token'])
    return HttpResponseRedirect(url)

def avans_callback(request):
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
    isEmployee = data['employee'] == 'true'

    resp, content = client.request('https://publicapi.avans.nl/oauth/studentnummer/', 'GET')
    data = json.loads(content)
    username = data['inlognaam']
    student_number = data['studentnummer']
    return HttpResponse('hoi')

    studentnummer = data['studentnummer']
    inlognaam = data['inlognaam']

    try:
        user = User.objects.get(username=inlognaam)
    except User.DoesNotExist:
        user = User.objects.create_user(inlognaam, studentnummer, 'secret')

    user = authenticate(username=inlognaam, password='secret')
    login(request, user)

    return HttpResponseRedirect('/')


def home(request):
    if not request.user.is_authenticated():
        return avans_login(request)
    else:
        return HttpResponse('YEAHYEAH')