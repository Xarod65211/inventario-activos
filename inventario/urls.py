from django.urls import path

from . import views

urlpatterns = [
    path('', views.panel, name='panel'),
    path('activos/', views.activos, name='activos'),
    path('activos/nuevo/', views.activo_form, name='activo_nuevo'),
    path('activos/<int:pk>/', views.activo, name='activo'),
    path('activos/<int:pk>/editar/', views.activo_form, name='activo_editar'),
    path('activos/<int:pk>/movimiento/', views.movimiento, name='movimiento'),
    path('activos/<int:pk>/mantenimiento/', views.mantenimiento, name='mantenimiento'),
    path('activos/<int:pk>/qr.png', views.qr, name='qr'),
    path('etiquetas/', views.etiquetas, name='etiquetas'),
    path('movimientos/<int:pk>/acta.pdf', views.acta, name='acta'),
    path('mantenimientos/', views.mantenimientos, name='mantenimientos'),
    path('mantenimientos/<int:pk>/realizado/', views.mantenimiento_realizado, name='mantenimiento_realizado'),
    path('responsables/', views.responsables, name='responsables'),
    path('importar/', views.importar, name='importar'),
    path('a/<uuid:token>/', views.ficha_publica, name='ficha_publica'),
]
