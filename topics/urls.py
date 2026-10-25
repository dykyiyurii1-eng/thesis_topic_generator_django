from django.urls import path
from . import views

app_name = 'topics'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('interests/suggest/', views.suggest_interests_view, name='suggest_interests'),
    path('interests/save-default/', views.save_default_interests_view, name='save_default_interests'),
    path('generate/', views.SessionCreateView.as_view(), name='generate'),
    path('trial/', views.trial_generate_view, name='trial'),
    path('session/<int:session_id>/', views.DebatePageView.as_view(), name='debate_page'),
    path('session/<int:session_id>/stream/', views.debate_stream_view, name='debate_stream'),
    path('topic/<int:topic_id>/pin/', views.pin_topic_view, name='pin_topic'),
    path('history/', views.SessionListView.as_view(), name='history'),
    path('history/bulk-delete/', views.bulk_delete_sessions, name='bulk_delete_sessions'),
    path('session/<int:pk>/detail/', views.SessionDetailView.as_view(), name='session_detail'),
    path('session/<int:pk>/edit/', views.SessionUpdateView.as_view(), name='session_update'),
    path('session/<int:pk>/delete/', views.SessionDeleteView.as_view(), name='session_delete'),
    path('session/<int:session_id>/email/', views.send_session_email_view, name='send_email'),
    path('sandbox/', views.sandbox_view, name='sandbox'),
]