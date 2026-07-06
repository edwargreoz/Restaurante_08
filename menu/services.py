
from django.db import transaction
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from menu.models import Categoria, Plato
from inventario.models import Receta


class CategoriaService:
    @staticmethod
    def crear(nombre: str, es_bebida: bool = False,
              orden_display: int = 0) -> Categoria:
        return Categoria.objects.create(
            nombre=nombre, es_bebida=es_bebida,
            orden_display=orden_display
        )


class PlatoService:
    @staticmethod
    @transaction.atomic
    def crear(nombre: str, precio, categoria_id: int,
              receta_id: int, descripcion: str = '',
              tiempo_preparacion: int = 15,
              disponible: bool = True, imagen=None) -> Plato:
        categoria = Categoria.objects.filter(id=categoria_id).first()
        if not categoria:
            raise RecursoNoEncontrado('Categoría no encontrada')
        receta = Receta.objects.filter(id=receta_id).first()
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')

        return Plato.objects.create(
            nombre=nombre, precio=precio,
            categoria=categoria, receta=receta,
            descripcion=descripcion,
            tiempo_preparacion_min=tiempo_preparacion,
            disponible=disponible, imagen=imagen,
        )

    @staticmethod
    def verificar_disponibilidad(plato_id: int) -> bool:
        plato = Plato.objects.filter(id=plato_id).first()
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        return plato.disponible

    @staticmethod
    def toggle_disponible(plato_id: int) -> Plato:
        plato = Plato.objects.filter(id=plato_id).first()
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        plato.disponible = not plato.disponible
        plato.save(update_fields=['disponible'])
        return plato
