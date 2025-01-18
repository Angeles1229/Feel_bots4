from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Ruta para la vista index
    path('register/', views.register, name='register'), 
    path('register_paciente/', views.register_paciente, name='register_paciente'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('modulos/', views.modulos, name='modulos'),
    path('bienvenido/', views.bienvenido, name='bienvenido'),
    path('escaneo_voz/', views.escaneo_voz, name='escaneo_voz'),
    path('buscar_paciente/', views.render_buscar_paciente, name='buscar_paciente'),
    path('buscar_paciente/ajax/', views.buscar_paciente_ajax, name='buscar_paciente_ajax'),
    path('escaneo_texto/', views.escaneo_texto, name='escaneo_texto'),
    path('eliminar_paciente/<int:id_paciente>/', views.eliminar_paciente, name='eliminar_paciente'),
    path('editar_paciente/<int:id_paciente>/', views.editar_paciente, name='editar_paciente'),
    path('scan-emotion/', views.escaneo_emociones, name='emotion_scan'),
    path('analizar_emocion_voz/', views.analizar_emocion_voz, name='analizar_emocion_voz'),
    path('analizar_emocion_texto/', views.analizar_emocion_texto, name='analizar_emocion_texto'),
    path('informe/', views.informe_emocional, name='informe_emocional'),
    path("detectar/", views.capturar_emocion, name="capturar_emocion"),
    path('guardar_emocion/', views.guardar_emocion, name='guardar_emocion'),

]
