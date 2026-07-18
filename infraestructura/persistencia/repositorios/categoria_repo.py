from typing import Optional, List
from django.db.models import Prefetch
from menu.models import Categoria as CategoriaModel
from menu.models import Plato as PlatoModel
from dominio.entidades.categoria import Categoria
from dominio.entidades.plato import Plato


class CategoriaRepository:
    def obtener_por_id(self, categoria_id: int) -> Optional[Categoria]:
        try:
            c = CategoriaModel.objects.get(id=categoria_id)
            return Categoria(
                id=c.id, nombre=c.nombre, es_bebida=c.es_bebida,
                orden_display=c.orden_display,
            )
        except CategoriaModel.DoesNotExist:
            return None

    def guardar(self, categoria: Categoria) -> Categoria:
        c, _ = CategoriaModel.objects.update_or_create(
            id=categoria.id,
            defaults={
                'nombre': categoria.nombre,
                'es_bebida': categoria.es_bebida,
                'orden_display': categoria.orden_display,
            }
        )
        return Categoria(
            id=c.id, nombre=c.nombre, es_bebida=c.es_bebida,
            orden_display=c.orden_display,
        )

    def listar(self) -> List[Categoria]:
        return [
            Categoria(id=c.id, nombre=c.nombre, es_bebida=c.es_bebida)
            for c in CategoriaModel.objects.all()
        ]

    def listar_con_platos(self) -> List[Categoria]:
        categorias_model = CategoriaModel.objects.prefetch_related(
            Prefetch('platos', queryset=PlatoModel.activos.all().select_related('receta'))
        ).all()
        resultado = []
        for c in categorias_model:
            platos = [
                Plato(
                    id=p.id, nombre=p.nombre, precio=p.precio,
                    categoria_id=p.categoria_id,
                    receta_id=p.receta_id if p.receta_id else None,
                    disponible=p.disponible,
                    tiempo_preparacion_min=p.tiempo_preparacion_min,
                    descripcion=p.descripcion or '',
                )
                for p in c.platos.all()
            ]
            resultado.append(Categoria(
                id=c.id, nombre=c.nombre, es_bebida=c.es_bebida,
                orden_display=c.orden_display, platos=platos,
            ))
        return resultado