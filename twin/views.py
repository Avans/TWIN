from django.contrib.auth import get_user_model, authenticate

User = get_user_model()

from rest_framework import viewsets
#from api.serializers import UserSerializer
import oauth2 as oauth
import cgi, json
import secrets, avans

from django.http import HttpResponse
from django.http import HttpResponseRedirect

REQUEST_TOKEN_URL = 'https://publicapi.avans.nl/oauth/request_token?oauth_callback=http://%s/oauth/callback'
ACCESS_TOKEN_URL = 'https://publicapi.avans.nl/oauth/access_token'
AUTHORIZE_URL = 'https://publicapi.avans.nl/oauth/saml.php?oauth_token=%s'

consumer = oauth.Consumer(secrets.AVANS_KEY, secrets.AVANS_SECRET)
client = oauth.Client(consumer)


def home(request):
    if not request.user.is_authenticated():
        return avans.login(request)
    else:
        return HttpResponse('YEAHYEAH<xmp>' + repr(request.user))