from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views # <--- Importa esto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/login/', views.obtain_auth_token), # <--- ESTA ES LA URL DE LOGIN
]