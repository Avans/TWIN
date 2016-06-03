from django.conf.urls import url, include
from rest_framework import routers
from django.conf.urls.static import static
from django.views.static import serve
from twin import views, avans


router = routers.DefaultRouter()
#router.register(r'users', views.UserViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^$', views.home),
    #url(r'^api/user$', views.user),
    url(r'^oauth/callback$', avans.callback),
] + static('/', document_root='public')