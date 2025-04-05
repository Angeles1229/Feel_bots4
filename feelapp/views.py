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
import openai
import json
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

emociones = ['Tristeza', 'Alegria', 'Calma', 'Miedo']

@csrf_exempt
def capturar_emocion(request):
    return JsonResponse({"error": "El reconocimiento de emociones por imagen está deshabilitado."}, status=501)


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
            openai.api_key = config('OPENAI_API_KEY')

            data = json.loads(request.body)
            texto = data.get('texto', '').strip()

            if not texto:
                return JsonResponse({'error': 'El texto no puede estar vacío'}, status=400)

            # Enviar la consulta a OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un analizador de emociones. Solo responde en JSON y nada más."},
                    {"role": "user", "content": f"Analiza el siguiente texto y responde ÚNICAMENTE con un JSON en este formato: "
                                                f'{{"ALEGRÍA": 30, "CALMA": 20, "MIEDO": 25, "TRISTEZA": 25}}. '
                                                f"No incluyas ningún otro texto antes o después del JSON.\n\nTexto: {texto}"}
                ],
                temperature=0.7
            )

            # Depuración: Imprimir la respuesta de OpenAI
            print("Respuesta de OpenAI:", response['choices'][0]['message']['content'])

            # Procesar la respuesta JSON de OpenAI
            try:
                resultado = json.loads(response['choices'][0]['message']['content'])
            except (json.JSONDecodeError, TypeError) as e:
                print("Error al decodificar JSON:", str(e))
                return JsonResponse({'error': 'Error al procesar la respuesta de OpenAI'}, status=500)

            # Asegurar que las emociones tienen valores enteros correctos
            emociones_dict = {
                'ALEGRÍA': max(0, int(resultado.get('ALEGRÍA', 0))),
                'CALMA': max(0, int(resultado.get('CALMA', 0))),
                'MIEDO': max(0, int(resultado.get('MIEDO', 0))),
                'TRISTEZA': max(0, int(resultado.get('TRISTEZA', 0)))
            }

            # Normalizar los valores si no suman 100
            suma_total = sum(emociones_dict.values())
            if suma_total == 0:
                return JsonResponse({'error': 'OpenAI devolvió todos los valores en 0, no se puede analizar.'}, status=400)

            if suma_total != 100:
                factor = 100 / suma_total
                emociones_dict = {k: round(v * factor) for k, v in emociones_dict.items()}  # Redondear para evitar errores

            # Obtener la emoción con mayor porcentaje
            emocion_detectada = max(emociones_dict, key=emociones_dict.get)
            porcentaje_real = emociones_dict[emocion_detectada]

            print(f"Emoción detectada: {emocion_detectada}, Porcentaje real: {porcentaje_real}")

            # Normalizar el nombre de la emoción antes de buscar en la BD
            emocion_normalizada = quitar_tildes(emocion_detectada).upper()

            # Buscar la emoción en la base de datos
            try:
                emocion_obj = Emociones.objects.get(Nombre__iexact=emocion_normalizada)
            except Emociones.DoesNotExist:
                print(f"Emoción '{emocion_normalizada}' no encontrada en la BD.")
                return JsonResponse({'error': 'Emoción no encontrada en la base de datos'}, status=400)

            # Verificar que el paciente está en la sesión
            paciente_id = request.session.get('paciente_id')
            if not paciente_id:
                return JsonResponse({'error': 'Paciente no encontrado en la sesión'}, status=400)

            try:
                paciente = Paciente.objects.get(idPaciente=paciente_id)
            except Paciente.DoesNotExist:
                return JsonResponse({'error': 'Paciente no encontrado en la BD'}, status=400)

            # Guardar emoción en la base de datos
            VozEmocion.objects.create(
                idEmociones=emocion_obj,
                idPaciente=paciente,
                porcentaje=porcentaje_real
            )

            return JsonResponse({'emocion': emocion_detectada, 'confianza': porcentaje_real, 'mensaje': 'Emoción registrada correctamente'})

        except Exception as e:
            import traceback
            print("Error en analizar_emocion_voz:", traceback.format_exc())
            return JsonResponse({'error': f'Error interno en el servidor: {str(e)}'}, status=500)

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

            # Petición a OpenAI solicitando la distribución de emociones con sus porcentajes
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un analizador de emociones. Solo responde en JSON y nada más."},
                    {"role": "user", "content": f"Analiza el siguiente texto y responde ÚNICAMENTE con un JSON en este formato: "
                                                f'{{"ALEGRÍA": 30, "CALMA": 20, "MIEDO": 25, "TRISTEZA": 25}}. '
                                                f"No incluyas ningún otro texto antes o después del JSON.\n\nTexto: {texto}"}
                ],
                temperature=0.7
            )

            # Depuración: Imprimir la respuesta de OpenAI
            print("Respuesta de OpenAI:", response['choices'][0]['message']['content'])

            # Procesar la respuesta JSON de OpenAI
            try:
                resultado = json.loads(response['choices'][0]['message']['content'])
            except (json.JSONDecodeError, TypeError) as e:
                print("Error al decodificar JSON:", str(e))
                return JsonResponse({'error': 'Error al procesar la respuesta de OpenAI'}, status=500)

            # Asegurar que las emociones tienen valores enteros correctos
            emociones_dict = {
                'ALEGRÍA': max(0, int(resultado.get('ALEGRÍA', 0))),
                'CALMA': max(0, int(resultado.get('CALMA', 0))),
                'MIEDO': max(0, int(resultado.get('MIEDO', 0))),
                'TRISTEZA': max(0, int(resultado.get('TRISTEZA', 0)))
            }

            # Normalizar los valores si no suman 100
            suma_total = sum(emociones_dict.values())
            if suma_total == 0:
                return JsonResponse({'error': 'OpenAI devolvió todos los valores en 0, no se puede analizar.'}, status=400)

            if suma_total != 100:
                factor = 100 / suma_total
                emociones_dict = {k: round(v * factor) for k, v in emociones_dict.items()}  # Redondear para evitar errores

            # Obtener la emoción con mayor porcentaje
            emocion_detectada = max(emociones_dict, key=emociones_dict.get)
            porcentaje_real = emociones_dict[emocion_detectada]

            print(f"Emoción detectada: {emocion_detectada}, Porcentaje real: {porcentaje_real}")

            # Normalizar el nombre de la emoción antes de buscar en la BD
            emocion_normalizada = quitar_tildes(emocion_detectada).upper()

            # Buscar la emoción en la base de datos
            try:
                emocion_obj = Emociones.objects.get(Nombre__iexact=emocion_normalizada)
            except Emociones.DoesNotExist:
                print(f"Emoción '{emocion_normalizada}' no encontrada en la BD.")
                return JsonResponse({'error': 'Emoción no encontrada en la base de datos'}, status=400)

            # Verificar que el paciente está en la sesión
            paciente_id = request.session.get('paciente_id')
            if not paciente_id:
                return JsonResponse({'error': 'Paciente no encontrado en la sesión'}, status=400)

            try:
                paciente = Paciente.objects.get(idPaciente=paciente_id)
            except Paciente.DoesNotExist:
                return JsonResponse({'error': 'Paciente no encontrado en la BD'}, status=400)

            # Guardar emoción en la base de datos
            TextoEmocion.objects.create(
                idEmociones=emocion_obj,
                idPaciente=paciente,
                porcentaje=porcentaje_real
            )

            return JsonResponse({
                'emocion': emocion_detectada,
                'confianza': porcentaje_real,
                'mensaje': 'Emoción registrada correctamente'
            })

        except Exception as e:
            import traceback
            print("Error en analizar_emocion_texto:", traceback.format_exc())
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

        # Verificar que todos los campos estén completos
        if not all([usuario, correo, contraseña, confirmar_contraseña]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'register.html')

        # Verificar si las contraseñas coinciden
        if contraseña != confirmar_contraseña:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'register.html')

        # Verificar si el usuario o correo ya existen
        if Administrador.objects.filter(usuario=usuario).exists():
            messages.error(request, 'El usuario ya existe.')
        elif Administrador.objects.filter(correo=correo).exists():
            messages.error(request, 'El correo ya está registrado.')
        else:
            # Crear el usuario
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

        # Crear el paciente asociado al administrador logueado
        try:
            Paciente.objects.create(
                Nombre=nombre,
                Apellido=apellido,
                Cedula=cedula,
                idAdministrador=request.user  # Asociar con el administrador logueado
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
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        # Obtener los valores del formulario
        username = request.POST.get('usuario')
        password = request.POST.get('contraseña')

        # Verificar si los campos están vacíos
        if not username or not password:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return render(request, 'login.html')

        # Autenticación manual
        user = authenticate(request, username=username, password=password)  # Usa 'username' en lugar de 'usuario'
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('index')  # Redirigir a la página de inicio
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
    pacientes = Paciente.objects.filter(idAdministrador=request.user)  # Solo pacientes del admin logueado
    if request.method == "POST":
        paciente_id = request.POST.get("paciente_id")
        if paciente_id:
            request.session['paciente_id'] = paciente_id
            return redirect('escaneo_voz')
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
    resultados = Paciente.objects.filter(idAdministrador=request.user)  # Filtrar por administrador

    if query:
        resultados = resultados.filter(
            Q(Nombre__icontains=query) |
            Q(Apellido__icontains=query) |
            Q(idPaciente__icontains=query)
        )

    return render(request, 'buscar_paciente.html', {
        'resultados': resultados,
        'query': query,
    })


from django.http import JsonResponse
@login_required
def buscar_paciente_ajax(request):
    query = request.GET.get('query', '')
    resultados = Paciente.objects.filter(idAdministrador=request.user)  # Filtrar por admin

    if query:
        resultados = resultados.filter(
            Q(Nombre__icontains=query) |
            Q(Apellido__icontains=query) |
            Q(idPaciente__icontains=query)
        )

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


def informe_emocional(request):
    registros = []
    query_paciente = request.GET.get('paciente', '').strip()
    query_fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    query_fecha_fin = request.GET.get('fecha_fin', '').strip()

    # Solo pacientes del administrador logueado
    pacientes = Paciente.objects.filter(idAdministrador=request.user)

    # Filtrar por nombre o apellido
    if query_paciente:
        pacientes = pacientes.filter(
            Q(Nombre__icontains=query_paciente) | Q(Apellido__icontains=query_paciente)
        )

    # Parsear fechas si están presentes
    fecha_inicio = None
    fecha_fin = None
    try:
        if query_fecha_inicio:
            fecha_inicio = datetime.strptime(query_fecha_inicio, "%Y-%m-%d").date()
        if query_fecha_fin:
            fecha_fin = datetime.strptime(query_fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return render(request, 'informe.html', {
            'error': 'Formato de fecha inválido. Usa YYYY-MM-DD.',
            'query_paciente': query_paciente,
            'query_fecha_inicio': query_fecha_inicio,
            'query_fecha_fin': query_fecha_fin,
        })

    for paciente in pacientes:
        # Filtrar registros por paciente y fechas
        voz_emociones = VozEmocion.objects.filter(idPaciente=paciente).order_by('fecha_creacion')
        texto_emociones = TextoEmocion.objects.filter(idPaciente=paciente).order_by('fecha_creacion')

        if fecha_inicio:
            voz_emociones = voz_emociones.filter(fecha_creacion__gte=fecha_inicio)
            texto_emociones = texto_emociones.filter(fecha_creacion__gte=fecha_inicio)

        if fecha_fin:
            voz_emociones = voz_emociones.filter(fecha_creacion__lte=fecha_fin)
            texto_emociones = texto_emociones.filter(fecha_creacion__lte=fecha_fin)

        # Agrupar registros por fecha
        fechas_unicas = sorted(set(voz.fecha_creacion.date() for voz in voz_emociones) | 
                               set(texto.fecha_creacion.date() for texto in texto_emociones))

        # Unir registros de voz y texto por fecha
        for fecha in fechas_unicas:
            voz_registros = [voz for voz in voz_emociones if voz.fecha_creacion.date() == fecha]
            texto_registros = [texto for texto in texto_emociones if texto.fecha_creacion.date() == fecha]

            # Emparejar registros de voz y texto en la misma fecha
            for voz, texto in zip_longest(voz_registros, texto_registros, fillvalue=None):
                registros.append({
                    "fecha": fecha,
                    "paciente": paciente,
                    "voz": {
                        "emocion": voz.idEmociones.Nombre if voz else "N/A",
                        "porcentaje": voz.porcentaje if voz else "N/A",
                    },
                    "texto": {
                        "emocion": texto.idEmociones.Nombre if texto else "N/A",
                        "porcentaje": texto.porcentaje if texto else "N/A",
                    },
                    "emocion_predominante": max(
                        [voz.idEmociones.Nombre if voz else "N/A",
                         texto.idEmociones.Nombre if texto else "N/A"],
                        key=lambda x: (voz.porcentaje if voz and x == voz.idEmociones.Nombre else 0) +
                                      (texto.porcentaje if texto and x == texto.idEmociones.Nombre else 0)
                    )
                })

    return render(request, 'informe.html', {
        "registros": registros,
        "query_paciente": query_paciente,
        "query_fecha_inicio": query_fecha_inicio,
        "query_fecha_fin": query_fecha_fin,
    })
