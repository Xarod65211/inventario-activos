from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path('acceso/', auth_views.LoginView.as_view(template_name='acceso.html'), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('inventario.urls')),
]
