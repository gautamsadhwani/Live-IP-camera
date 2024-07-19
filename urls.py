from django.urls import path
from .views import Home, capture_image

urlpatterns= [
    path('', Home, name='home'),
    path('capture_image/', capture_image, name='capture_image'),
]