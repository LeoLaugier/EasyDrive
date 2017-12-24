from django.conf.urls import url
from objRequests import views

urlpatterns = [
    url(r'^$', views.index_view, name='index'),
    url(r'login$', views.login_view, name='login_view'),
    url(r'logout/$', views.logout_view, name='logout_view'),
    url(r'push', views.message_reception, name="message_reception"),
    url(r'trajets/(?P<device_id>\d+)/(?P<page>\d+)?$', views.trajets_index, name="trajets"),
    url(r'devices', views.devices_index, name="devices"),
    url(r'trajet/(?P<trajet_id>\d+)/(?P<page>\d+)?$', views.trajet, name="trajet"),

]
