from django.conf.urls import url, include
from django.conf.urls.static import static
from django.views.static import serve
from twin import views, avans

from django.contrib import admin
admin.autodiscover()

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^$', views.home),
    url(r'^logout$', views.logout),
    url(r'^api/user$', views.api_user),
    url(r'^api/preference$', views.api_preference),
    url(r'^api/students$', views.api_students),
    url(r'^oauth/callback$', avans.callback),
    url(r'^admin/login/', avans.login),
    url(r'^admin/', admin.site.urls),
] + static('/static', document_root='static')
