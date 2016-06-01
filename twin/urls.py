from django.conf.urls import url, include
from rest_framework import routers
from api import views
from django.conf.urls.static import static
from django.views.static import serve
from api import views

router = routers.DefaultRouter()
#router.register(r'users', views.UserViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^oauth/callback$', views.avans_callback, name='home'),
    #url(r'^$', serve, kwargs={'path': 'index.html', 'document_root': 'public'}),
    #url(r'^', include(router.urls)),
    url(r'^api/', include('rest_framework.urls', namespace='rest_framework'))
] + static('/', document_root='public')