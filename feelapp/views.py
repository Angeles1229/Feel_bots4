from decouple import config
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Administrador, Paciente, Emociones, RostroEmocion, VozEmocion, TextoEmocion
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from itertools import zip_longest
import base64
import numpy as np
import cv2
import tensorflow as tf
import openai
import json
import tensorflow as tf
from django.shortcuts import render
from django.http import JsonResponse
from PIL import Image
import numpy as np
from io import BytesIO
import unidecode
from django.contrib.auth.decorators import login_required
from .models import Paciente, RostroEmocion, VozEmocion, TextoEmocion
from django.db.models import Q
from datetime import datetime

# Cargar el modelo Keras
modelo  = tf.keras.models.load_model('modelo_xception_emociones_v2.keras')

emociones = ['Tristeza', 'Alegria', 'Calma', 'Miedo']

@csrf_exempt
def capturar_emocion(request):
    if request.method == "POST":
        try:
            # Decodificar la imagen enviada por el cliente
            data = json.loads(request.body)
            imagen_base64 = data["imagen"].split(",")[1]
            imagen_decodificada = Image.open(BytesIO(base64.b64decode(imagen_base64)))
            imagen_array = np.array(imagen_decodificada)

            # Preprocesar la imagen
            imagen_preprocesada = preprocesar_imagen(imagen_array)

            # Hacer la predicción
            prediccion = modelo.predict(imagen_preprocesada)
            emocion_detectada = emociones[np.argmax(prediccion)]

            # Obtener el porcentaje de confianza
            porcentaje_confianza = float(np.max(prediccion) * 100)

            return JsonResponse({
                "emocion": emocion_detectada,
                "porcentaje": porcentaje_confianza,
                "mensaje": "Emoción detectada correctamente."
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)



@csrf_exempt
def guardar_emocion(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            emocion_detectada = data.get("emocion")
            if not emocion_detectada:
                return JsonResponse({"error": "Emoción no detectada"}, status=400)

            # Obtener el paciente
            paciente_id = request.session.get("paciente_id")
            if not paciente_id:
                return JsonResponse({"error": "ID del paciente no disponible en la sesión."}, status=400)

            paciente_obj = get_object_or_404(Paciente, idPaciente=paciente_id)

            # Buscar la emoción en la base de datos
            emocion_obj = Emociones.objects.filter(Nombre=emocion_detectada).first()
            if not emocion_obj:
                return JsonResponse({"error": "Emoción no encontrada en la base de datos."}, status=404)

            # Guardar la emoción en la base de datos
            registro = RostroEmocion.objects.create(
                idEmociones=emocion_obj,
                idPaciente=paciente_obj,
                porcentaje=100  # Por ejemplo, guardar el 100% de confianza si solo se detecta una emoción
            )
            registro.save()

            return JsonResponse({"mensaje": "Emoción guardada correctamente."})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def preprocesar_imagen(imagen):
    """
    Preprocesa la imagen para que sea compatible con el modelo.
    - Convierte a RGB (si no está ya en ese formato)
    - Redimensiona al tamaño requerido por el modelo
    - Normaliza los valores
    """
    # Asegúrate de que la imagen esté en formato RGB
    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)

    # Redimensionar la imagen al tamaño esperado por el modelo
    imagen_redimensionada = cv2.resize(imagen_rgb, (224, 224))

    # Normalizar los valores al rango [0, 1]
    imagen_normalizada = imagen_redimensionada / 255.0

    # Expandir dimensiones para que sea compatible con el modelo
    return np.expand_dims(imagen_normalizada, axis=0)





# Configura tu clave de API de OpenAI
openai.api_key = config('OPENAI_API_KEY')




# Función para eliminar tildes
def quitar_tildes(texto):
    return unidecode.unidecode(texto)

@login_required
@csrf_exempt
def analizar_emocion_voz(request):
    if request.method == 'POST':
        try:
            # Configura la clave API de OpenAI
            openai.api_key = config('OPENAI_API_KEY')

            # Lee y decodifica el cuerpo de la solicitud
            data = json.loads(request.body)
            texto = data.get('texto', '').strip()  # Elimina espacios al inicio y al final
            print(f"Texto recibido: {texto}")  # Log para depuración
            
            if not texto:
                return JsonResponse({'error': 'El texto no puede estar vacío'}, status=400)

            # Llama a la API de OpenAI usando el endpoint de chat
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[ 
                    {"role": "system", "content": "Eres un analizador de emociones."},
                    {"role": "user", "content": f"Analiza el siguiente texto, solo responde con una palabra, sin más explicación y determina la emoción dominante entre ALEGRÍA, CALMA, MIEDO, TRISTEZA: {texto}, recuerda que solamente quiero la palabra de la emocion, nada mas, SI DA ALGUNA OTRA EMOCION QUE NO SEA ALEGRÍA, CALMA, MIEDO, TRISTEZA PON UNO RELACIONADO A ALEGRÍA, CALMA, MIEDO, TRISTEZA"}
                ],
                temperature=0.7
            )

            # Ver la respuesta de la API de OpenAI para depuración
            print(f"Respuesta de OpenAI: {response}")

            # Limpieza y normalización de la emoción detectada
            emocion = response['choices'][0]['message']['content'].strip().rstrip('.').upper()  # Elimina puntos y convierte a mayúsculas
            emocion_normalizada = quitar_tildes(emocion)  # Elimina tildes
            print(f"Emoción detectada (normalizada): {emocion_normalizada}")  # Log para depuración

            # Buscar la emoción en la tabla Emociones, sin importar tildes o mayúsculas
            try:
                emocion_obj = Emociones.objects.get(Nombre__iexact=emocion_normalizada)  # Comparación insensible a mayúsculas y tildes
                print(f"Emoción encontrada: {emocion_obj.Nombre}")  # Log para depuración
            except Emociones.DoesNotExist:
                print(f"No se encontró la emoción: {emocion_normalizada}")  # Log para depuración
                return JsonResponse({'error': 'Emoción no válida o no encontrada en la base de datos'}, status=400)

            # Obtener el paciente
            paciente_id = request.session.get('paciente_id')
            if not paciente_id:
                print("Error: Paciente no encontrado en la sesión.")  # Log para depuración
                return JsonResponse({'error': 'Paciente no encontrado en la sesión'}, status=400)

            paciente = Paciente.objects.get(idPaciente=paciente_id)
            print(f"Paciente encontrado: {paciente.Nombre} {paciente.Apellido}")  # Log para depuración

            # Crear el registro en la tabla VozEmocion
            print(f"Registrando emoción en VozEmocion con: Emoción: {emocion_obj.Nombre}, Paciente: {paciente.Nombre}, Porcentaje: 100")  # Log para depuración
            voz_emocion = VozEmocion.objects.create(
                idEmociones=emocion_obj,
                idPaciente=paciente,
                porcentaje=100  # Aquí puedes calcular el porcentaje si es necesario
            )

            return JsonResponse({'emocion': emocion, 'mensaje': 'Emoción registrada correctamente'})

        except json.JSONDecodeError:
            print("Error: JSON no válido.")  # Log para depuración
            return JsonResponse({'error': 'Error al decodificar el JSON enviado.'}, status=400)
        except Exception as e:
            import traceback
            print("Error inesperado:", traceback.format_exc())  # Log para depuración
            return JsonResponse({'error': f'Error interno en el servidor: {str(e)}'}, status=500)
    else:
        print("Error: Método no permitido.")  # Log para depuración
        return JsonResponse({'error': 'Método no permitido. Usa POST.'}, status=405)


@login_required
@csrf_exempt
def analizar_emocion_texto(request):
    if request.method == 'POST':
        try:
            openai.api_key = config('OPENAI_API_KEY')

            data = json.loads(request.body)
            texto = data.get('texto', '').strip()

            if not texto:
                return JsonResponse({'error': 'El texto no puede estar vacío'}, status=400)

            # Llama a OpenAI para analizar la emoción
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un analizador de emociones."},
                    {"role": "user", "content": f"Analiza el siguiente texto, solo responde con una palabra, sin más explicación y determina la emoción dominante entre ALEGRÍA, CALMA, MIEDO, TRISTEZA: {texto}"}
                ],
                temperature=0.7
            )

            emocion = response['choices'][0]['message']['content'].strip().rstrip('.').upper()
            emocion_normalizada = quitar_tildes(emocion)

            # Buscar la emoción en la base de datos
            try:
                emocion_obj = Emociones.objects.get(Nombre__iexact=emocion_normalizada)
            except Emociones.DoesNotExist:
                return JsonResponse({'error': 'Emoción no válida o no encontrada en la base de datos'}, status=400)

            # Verificar el paciente
            paciente_id = request.session.get('paciente_id')
            if not paciente_id:
                return JsonResponse({'error': 'Paciente no encontrado en la sesión'}, status=400)

            paciente = Paciente.objects.get(idPaciente=paciente_id)

            # Registrar la emoción
            TextoEmocion.objects.create(
                idEmociones=emocion_obj,
                idPaciente=paciente,
                porcentaje=100
            )

            return JsonResponse({'emocion': emocion, 'mensaje': 'Emoción registrada correctamente'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Error al decodificar el JSON enviado.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error interno en el servidor: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Método no permitido. Usa POST.'}, status=405)




def index(request):
    return render(request, 'index.html')

from django.contrib.auth.hashers import make_password


def register(request):
    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        correo = request.POST.get('correo')
        contraseña = request.POST.get('contraseña')
        confirmar_contraseña = request.POST.get('confirmar_contraseña')

        if not all([usuario, correo, contraseña, confirmar_contraseña]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'register.html')

        if contraseña != confirmar_contraseña:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'register.html')

        # Crear un nuevo usuario
        if Administrador.objects.filter(usuario=usuario).exists():
            messages.error(request, 'El usuario ya existe.')
        elif Administrador.objects.filter(correo=correo).exists():
            messages.error(request, 'El correo ya está registrado.')
        else:
            Administrador.objects.create_user(
                usuario=usuario,
                correo=correo,
                contraseña=contraseña,
                Nombre=request.POST.get('nombre'),
                Apellido=request.POST.get('apellido')
            )
            messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect('login')

    return render(request, 'register.html')
from django.contrib.messages import get_messages

@login_required
def register_paciente(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        cedula = request.POST.get('cedula')

        # Validar los campos obligatorios
        if not all([nombre, apellido, cedula]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'registro_paciente.html')

        # Crear el paciente
        try:
            Paciente.objects.create(
                Nombre=nombre,
                Apellido=apellido,
                Cedula=cedula,
            )
            messages.success(request, '¡Paciente registrado exitosamente!')
            return redirect('buscar_paciente')
        except Exception as e:
            messages.error(request, f'Error al registrar el paciente: {str(e)}')

    # Limpieza de mensajes al renderizar nuevamente
    storage = get_messages(request)
    for _ in storage:  # Consume todos los mensajes existentes
        pass

    return render(request, 'registro_paciente.html')

@login_required
def bienvenido(request):
    # Obtén el usuario autenticado
    usuario = request.user

    # Busca al administrador por el usuario
    try:
        administrador = Administrador.objects.get(usuario=usuario.usuario)  # Cambiar username a usuario
    except Administrador.DoesNotExist:
        administrador = None

    return render(request, 'bienvenido.html', {
        'administrador': administrador,  # Pasamos los datos del administrador a la plantilla
    })



from django.contrib.auth.hashers import check_password

from .models import Administrador


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('usuario')
        password = request.POST.get('contraseña')

        if not username or not password:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return render(request, 'login.html')

        # Autenticación manual
        user = authenticate(request, usuario=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.Nombre}!')
                return redirect('index')
            else:
                messages.error(request, 'Cuenta desactivada. Contacta al administrador.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')






@login_required
def modulos(request):
    pacientes = Paciente.objects.all()  # Obtener todos los pacientes
    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        if paciente_id:
            request.session['paciente_id'] = paciente_id  # Guardar el id del paciente en la sesión
            return redirect('emotion_scan')  # Redirigir al escaneo de emociones
    return render(request, 'modulos.html', {'pacientes': pacientes})

from django.shortcuts import render, get_object_or_404

@login_required
def escaneo_emociones(request):
    paciente_id = request.session.get('paciente_id')  # Obtener el id del paciente desde la sesión
    if paciente_id:
        paciente = get_object_or_404(Paciente, idPaciente=paciente_id)  # Buscar al paciente
        return render(request, "escaneo_emociones.html", {'paciente': paciente})
    else:
        return redirect('modulos')  # Si no hay paciente_id en la sesión, redirigir a módulos
    
@login_required
def escaneo_voz(request):
    paciente_id = request.session.get('paciente_id')  # Obtener el id del paciente desde la sesión
    if paciente_id:
        paciente = get_object_or_404(Paciente, idPaciente=paciente_id)  # Buscar al paciente
        return render(request, 'escaneo_voz.html', {'paciente': paciente})
    else:
        return redirect('modulos')  # Si no hay paciente_id en la sesión, redirigir a módulos
    


@login_required
def escaneo_texto(request):
    paciente_id = request.session.get('paciente_id')  # Obtener el id del paciente desde la sesión
    if paciente_id:
        paciente = get_object_or_404(Paciente, idPaciente=paciente_id)  # Buscar al paciente
        return render(request, 'escaneo_texto.html', {'paciente': paciente})
    else:
        return redirect('modulos')  # Si no hay paciente_id en la sesión, redirigir a módulos



@login_required
def render_buscar_paciente(request):
    query = request.GET.get('query', '')
    resultados = None

    if query:
        # Filtrar pacientes por Nombre, Apellido o ID (idPaciente)
        resultados = Paciente.objects.filter(
            Nombre__icontains=query
        ) | Paciente.objects.filter(
            Apellido__icontains=query
        ) | Paciente.objects.filter(
            idPaciente__icontains=query
        )
    else:
        # Si no hay query, mostramos todos los pacientes
        resultados = Paciente.objects.all()

    return render(request, 'buscar_paciente.html', {
        'resultados': resultados,
        'query': query,
    })



from django.http import JsonResponse
@login_required
def buscar_paciente_ajax(request):
    query = request.GET.get('query', '')
    resultados = None

    if query:
        # Filtrar pacientes por Nombre, Apellido o ID (idPaciente)
        resultados = Paciente.objects.filter(
            Nombre__icontains=query
        ) | Paciente.objects.filter(
            Apellido__icontains=query
        ) | Paciente.objects.filter(
            idPaciente__icontains=query
        )
    else:
        # Si no hay query, mostramos todos los pacientes
        resultados = Paciente.objects.all()

    pacientes_data = [
        {
            'id': paciente.idPaciente,
            'nombre': paciente.Nombre,
            'apellido': paciente.Apellido,
            'cedula': paciente.Cedula,
        }
        for paciente in resultados
    ]

    return JsonResponse({'resultados': pacientes_data})


# Vista para editar un paciente
@require_POST
def editar_paciente(request, id_paciente):
    try:
        # Obtén el paciente por id
        paciente = Paciente.objects.get(idPaciente=id_paciente)
        
        # Obtén los valores del formulario
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        cedula = request.POST.get('cedula')

        # Actualiza el paciente
        paciente.Nombre = nombre
        paciente.Apellido = apellido
        paciente.Cedula = cedula
        paciente.save()

        return JsonResponse({'success': True})
    except Paciente.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paciente no encontrado'}, status=404)
    except Exception as e:
        # En caso de error, devolvemos un mensaje más detallado
        return JsonResponse({'success': False, 'error': str(e)}, status=500)




# Vista para eliminar un paciente
@csrf_exempt
def eliminar_paciente(request, id_paciente):
    if request.method == 'DELETE':
        try:
            paciente = Paciente.objects.get(idPaciente=id_paciente)
            paciente.delete()
            return JsonResponse({'success': True})
        except Paciente.DoesNotExist:
            return JsonResponse({'success': False}, status=404)
    return JsonResponse({'error': 'Método no permitido'}, status=405)




@login_required
def informe_emocional(request):
    registros = []
    query_paciente = request.GET.get('paciente', '').strip()
    query_fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    query_fecha_fin = request.GET.get('fecha_fin', '').strip()

    pacientes = Paciente.objects.all()
    if query_paciente:
        pacientes = pacientes.filter(
            Q(Nombre__icontains=query_paciente) |
            Q(Apellido__icontains=query_paciente)
        )

    fecha_inicio = datetime.strptime(query_fecha_inicio, "%Y-%m-%d") if query_fecha_inicio else None
    fecha_fin = datetime.strptime(query_fecha_fin, "%Y-%m-%d") if query_fecha_fin else None

    for paciente in pacientes:
        rostro_emociones = RostroEmocion.objects.filter(idPaciente=paciente)
        voz_emociones = VozEmocion.objects.filter(idPaciente=paciente)
        texto_emociones = TextoEmocion.objects.filter(idPaciente=paciente)

        if fecha_inicio:
            rostro_emociones = rostro_emociones.filter(fecha_creacion__gte=fecha_inicio)
            voz_emociones = voz_emociones.filter(fecha_creacion__gte=fecha_inicio)
            texto_emociones = texto_emociones.filter(fecha_creacion__gte=fecha_inicio)

        if fecha_fin:
            rostro_emociones = rostro_emociones.filter(fecha_creacion__lte=fecha_fin)
            voz_emociones = voz_emociones.filter(fecha_creacion__lte=fecha_fin)
            texto_emociones = texto_emociones.filter(fecha_creacion__lte=fecha_fin)

        emociones_combinadas = zip_longest(rostro_emociones, voz_emociones, texto_emociones, fillvalue=None)

        for rostro_emocion, voz_emocion, texto_emocion in emociones_combinadas:
            emociones = [
                (em.idEmociones.Nombre, em.porcentaje)
                for em in [rostro_emocion, voz_emocion, texto_emocion]
                if em and em.porcentaje is not None
            ]

            emocion_predominante = max(emociones, key=lambda x: x[1], default=("Sin datos", 0))[0]

            registros.append({
                'fecha': rostro_emocion.fecha_creacion if rostro_emocion else "N/A",
                'paciente': paciente,
                'rostro': {
                    'emocion': rostro_emocion.idEmociones.Nombre if rostro_emocion else "N/A",
                    'porcentaje': rostro_emocion.porcentaje if rostro_emocion else "N/A",
                },
                'voz': {
                    'emocion': voz_emocion.idEmociones.Nombre if voz_emocion else "N/A",
                    'porcentaje': voz_emocion.porcentaje if voz_emocion else "N/A",
                },
                'texto': {
                    'emocion': texto_emocion.idEmociones.Nombre if texto_emocion else "N/A",
                    'porcentaje': texto_emocion.porcentaje if texto_emocion else "N/A",
                },
                'emocion_predominante': emocion_predominante,
            })

    return render(request, 'informe.html', {
        'registros': registros,
        'query_paciente': query_paciente,
        'query_fecha_inicio': query_fecha_inicio,
        'query_fecha_fin': query_fecha_fin,
    })