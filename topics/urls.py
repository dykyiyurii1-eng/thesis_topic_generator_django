from django.urls import path
from . import views

app_name = 'topics'

urlpatterns = [
    path('', views.home_view, name='home'),
]