from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class AdministradorManager(BaseUserManager):
    def create_user(self, usuario, correo, contraseña=None, **extra_fields):
        if not usuario:
            raise ValueError('El campo usuario es obligatorio.')
        if not correo:
            raise ValueError('El campo correo es obligatorio.')

        extra_fields.setdefault('is_active', True)

        user = self.model(usuario=usuario, correo=self.normalize_email(correo), **extra_fields)
        user.set_password(contraseña)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, correo, contraseña=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(usuario, correo, contraseña, **extra_fields)

class Administrador(AbstractBaseUser, PermissionsMixin):
    usuario = models.CharField(max_length=150, unique=True)
    correo = models.EmailField(max_length=200, unique=True)
    Nombre = models.CharField(max_length=200)
    Apellido = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = AdministradorManager()

    USERNAME_FIELD = 'usuario'  # Campo utilizado como identificador único
    REQUIRED_FIELDS = ['correo']  # Campos obligatorios al crear un superusuario

    def __str__(self):
        return f"{self.Nombre} {self.Apellido}"
    
    
class Emociones(models.Model):
    idEmociones = models.AutoField(primary_key=True)
    Nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.Nombre

class Paciente(models.Model):
    idPaciente = models.AutoField(primary_key=True)
    idAdministrador = models.ForeignKey(
        Administrador,
        on_delete=models.SET_NULL,
        null=True,  # Permitir valores nulos en la base de datos
        blank=True  # Permitir que los formularios lo dejen en blanco
    )
    Cedula = models.CharField(max_length=10)
    Nombre = models.CharField(max_length=200)
    Apellido = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.Nombre} {self.Apellido}"


# Relacionar emociones con pacientes para el análisis de rostro
class RostroEmocion(models.Model):
    idRostroEmocion = models.AutoField(primary_key=True)
    idEmociones = models.ForeignKey(Emociones, on_delete=models.CASCADE)
    idPaciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación

    def __str__(self):
        return f"{self.idPaciente.Nombre} - {self.idEmociones.Nombre} (Rostro) ({self.porcentaje}%) - {self.fecha_creacion}"

# Relacionar emociones con pacientes para el análisis de voz
class VozEmocion(models.Model):
    idVozEmocion = models.AutoField(primary_key=True)
    idEmociones = models.ForeignKey(Emociones, on_delete=models.CASCADE)
    idPaciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación

    def __str__(self):
        return f"{self.idPaciente.Nombre} - {self.idEmociones.Nombre} (Voz) ({self.porcentaje}%) - {self.fecha_creacion}"

# Relacionar emociones con pacientes para el análisis de texto
class TextoEmocion(models.Model):
    idTextoEmocion = models.AutoField(primary_key=True)
    idEmociones = models.ForeignKey(Emociones, on_delete=models.CASCADE)
    idPaciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación

    def __str__(self):
        return f"{self.idPaciente.Nombre} - {self.idEmociones.Nombre} (Texto) ({self.porcentaje}%) - {self.fecha_creacion}"
