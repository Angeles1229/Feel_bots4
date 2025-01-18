from django.contrib import admin
from .models import Administrador, Emociones, Paciente, RostroEmocion, VozEmocion, TextoEmocion

admin.site.register(Administrador)
admin.site.register(Emociones)
admin.site.register(Paciente)
admin.site.register(RostroEmocion)
admin.site.register(VozEmocion)
admin.site.register(TextoEmocion)
