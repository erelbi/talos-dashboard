from django.urls import path
from .views import overview

app_name = 'dashboard'

urlpatterns = [
    path('', overview, name='overview'),
]
