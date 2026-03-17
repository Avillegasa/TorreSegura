# viviendas/api.py - APIs para integración con módulo financiero
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError
from .models import Vivienda, Edificio, Residente
import json

@login_required
@require_GET
def viviendas_por_edificio(request, edificio_id):
    """
    API para obtener viviendas por edificio
    Usado por el módulo financiero para filtros dinámicos
    """
    try:
        edificio_id = int(edificio_id)
        
        # Verificar que el edificio existe
        try:
            edificio = Edificio.objects.get(pk=edificio_id)
        except Edificio.DoesNotExist:
            return JsonResponse({
                'error': 'Edificio no encontrado'
            }, status=404)
        
        # Obtener viviendas activas del edificio
        viviendas = Vivienda.objects.filter(
            edificio_id=edificio_id,
            activo=True
        ).values('id', 'numero', 'piso', 'estado').order_by('piso', 'numero')
        
        # Convertir a lista para JSON
        viviendas_list = list(viviendas)
        
        # Agregar información adicional
        for vivienda in viviendas_list:
            vivienda['nombre'] = f"Vivienda {vivienda['numero']} - Piso {vivienda['piso']}"
            vivienda['disponible'] = vivienda['estado'] != 'BAJA'
        
        return JsonResponse(viviendas_list, safe=False)
        
    except ValueError:
        return JsonResponse({
            'error': 'ID de edificio inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

@login_required
@require_GET
def pisos_por_edificio(request, edificio_id):
    """
    API para obtener pisos únicos por edificio
    Usado para filtros de pisos
    """
    try:
        edificio_id = int(edificio_id)
        
        # Obtener pisos únicos del edificio
        pisos = Vivienda.objects.filter(
            edificio_id=edificio_id,
            activo=True
        ).values_list('piso', flat=True).distinct().order_by('piso')
        
        return JsonResponse(list(pisos), safe=False)
        
    except ValueError:
        return JsonResponse({
            'error': 'ID de edificio inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

@login_required
@require_GET
def residentes_por_vivienda(request, vivienda_id):
    """
    API para obtener residentes activos por vivienda
    Usado por módulo de accesos y financiero
    """
    try:
        vivienda_id = int(vivienda_id)
        
        # Verificar que la vivienda existe
        try:
            vivienda = Vivienda.objects.get(pk=vivienda_id)
        except Vivienda.DoesNotExist:
            return JsonResponse({
                'error': 'Vivienda no encontrada'
            }, status=404)
        
        # Obtener residentes activos
        residentes = Residente.objects.filter(
            vivienda_id=vivienda_id,
            activo=True
        ).select_related('usuario').values(
            'id',
            'usuario__first_name',
            'usuario__last_name',
            'es_propietario',
            'activo'
        )
        
        # Formatear datos para JSON
        residentes_list = []
        for residente in residentes:
            residentes_list.append({
                'id': residente['id'],
                'nombre': f"{residente['usuario__first_name']} {residente['usuario__last_name']}",
                'es_propietario': residente['es_propietario'],
                'tipo': 'Propietario' if residente['es_propietario'] else 'Inquilino',
                'activo': residente['activo']
            })
        
        return JsonResponse(residentes_list, safe=False)
        
    except ValueError:
        return JsonResponse({
            'error': 'ID de vivienda inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

@login_required
@require_GET
def vivienda_info(request, vivienda_id):
    """
    API para obtener información completa de una vivienda
    Usado por módulo financiero para validaciones
    """
    try:
        vivienda_id = int(vivienda_id)
        
        try:
            vivienda = Vivienda.objects.select_related('edificio').get(pk=vivienda_id)
        except Vivienda.DoesNotExist:
            return JsonResponse({
                'error': 'Vivienda no encontrada'
            }, status=404)
        
        # Obtener información de residentes
        residentes_activos = vivienda.get_residentes_activos()
        propietarios = vivienda.get_propietarios()
        inquilinos = vivienda.get_inquilinos()
        
        data = {
            'id': vivienda.id,
            'numero': vivienda.numero,
            'piso': vivienda.piso,
            'estado': vivienda.estado,
            'estado_display': vivienda.get_estado_display(),
            'activo': vivienda.activo,
            'metros_cuadrados': float(vivienda.metros_cuadrados),
            'habitaciones': vivienda.habitaciones,
            'baños': vivienda.baños,
            'edificio': {
                'id': vivienda.edificio.id,
                'nombre': vivienda.edificio.nombre,
                'direccion': vivienda.edificio.direccion
            },
            'residentes': {
                'total_activos': residentes_activos.count(),
                'propietarios': propietarios.count(),
                'inquilinos': inquilinos.count(),
            },
            'puede_usar_financiero': vivienda.activo and vivienda.estado != 'BAJA',
            'nombre_completo': vivienda.nombre_completo
        }
        
        return JsonResponse(data)
        
    except ValueError:
        return JsonResponse({
            'error': 'ID de vivienda inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

@login_required
@require_GET
def edificios_list(request):
    """
    API para listar todos los edificios
    Usado por múltiples módulos para selects dinámicos
    """
    try:
        edificios = Edificio.objects.all().values(
            'id', 'nombre', 'direccion', 'pisos'
        ).order_by('nombre')
        
        # Agregar información adicional
        edificios_list = []
        for edificio in edificios:
            edificio_obj = Edificio.objects.get(pk=edificio['id'])
            edificios_list.append({
                **edificio,
                'total_viviendas': edificio_obj.get_total_viviendas(),
                'viviendas_ocupadas': edificio_obj.get_viviendas_ocupadas(),
                'porcentaje_ocupacion': edificio_obj.get_porcentaje_ocupacion()
            })
        
        return JsonResponse(edificios_list, safe=False)
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

@login_required
def validate_vivienda_for_operation(request):
    """
    API para validar si una vivienda puede ser usada en operaciones específicas
    POST: {'vivienda_id': int, 'operation': str}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        vivienda_id = data.get('vivienda_id')
        operation = data.get('operation', 'general')
        
        if not vivienda_id:
            return JsonResponse({'error': 'vivienda_id es requerido'}, status=400)
        
        try:
            vivienda = Vivienda.objects.get(pk=vivienda_id)
        except Vivienda.DoesNotExist:
            return JsonResponse({'error': 'Vivienda no encontrada'}, status=404)
        
        # Validaciones específicas por operación
        validations = {
            'financial': lambda v: v.activo and v.estado != 'BAJA',
            'assignment': lambda v: v.activo and v.estado in ['DESOCUPADO', 'MANTENIMIENTO'],
            'access': lambda v: v.activo,
            'general': lambda v: v.activo
        }
        
        validation_func = validations.get(operation, validations['general'])
        is_valid = validation_func(vivienda)
        
        response_data = {
            'valid': is_valid,
            'vivienda_id': vivienda.id,
            'estado': vivienda.estado,
            'activo': vivienda.activo,
            'operation': operation
        }
        
        if not is_valid:
            if not vivienda.activo:
                response_data['reason'] = 'La vivienda está dada de baja'
            elif vivienda.estado == 'BAJA':
                response_data['reason'] = 'La vivienda está en estado de baja'
            elif operation == 'assignment' and vivienda.estado == 'OCUPADO':
                response_data['reason'] = 'La vivienda ya está ocupada'
            else:
                response_data['reason'] = 'La vivienda no cumple los requisitos para esta operación'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)

# ===== HELPERS PARA OTROS MÓDULOS =====

def get_available_viviendas_for_assignment():
    """
    Helper function para obtener viviendas disponibles para asignación
    Usado por el módulo de usuarios/residentes
    """
    return Vivienda.objects.filter(
        activo=True,
        estado__in=['DESOCUPADO', 'MANTENIMIENTO']
    ).select_related('edificio').order_by('edificio__nombre', 'piso', 'numero')

def get_viviendas_for_financial_operations():
    """
    Helper function para obtener viviendas para operaciones financieras
    Usado por el módulo financiero
    """
    return Vivienda.objects.filter(
        activo=True
    ).exclude(
        estado='BAJA'
    ).select_related('edificio').order_by('edificio__nombre', 'piso', 'numero')

def get_vivienda_residents(vivienda_id):
    """
    Helper function para obtener residentes de una vivienda
    """
    try:
        vivienda = Vivienda.objects.get(pk=vivienda_id)
        return vivienda.get_residentes_activos()
    except Vivienda.DoesNotExist:
        return Residente.objects.none()