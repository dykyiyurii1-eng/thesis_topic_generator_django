from django.urls import path
from . import views

app_name = 'topics'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('quiz/', views.quiz_view, name='quiz'),
      path('generate/', views.session_create_view, name='generate'),
      path('interests/suggest/', views.suggest_interests_view, name='suggest_interests'),
]