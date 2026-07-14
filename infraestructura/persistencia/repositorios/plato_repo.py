
from typing import Optional, List
from menu.models import Plato as PlatoModel
from dominio.entidades.plato import Plato


class PlatoRepository:
    def obtener_por_id(self, plato_id: int) -> Optional[Plato]:
        try:
            p = PlatoModel.objects.get(id=plato_id)
            return Plato(
                id=p.id, nombre=p.nombre, precio=p.precio,
                categoria_id=p.categoria_id, receta_id=p.receta_id,
                disponible=p.disponible,
            )
        except PlatoModel.DoesNotExist:
            return None
        

    def guardar(self, plato: Plato) -> Plato:
        p, _ = PlatoModel.objects.update_or_create(
            id=plato.id,
            defaults={
                'nombre': plato.nombre, 'precio': plato.precio,
                'categoria_id': plato.categoria_id, 'receta_id': plato.receta_id,
                'disponible': plato.disponible,
            }
        )
        return Plato(
            id=p.id, nombre=p.nombre, precio=p.precio,
            categoria_id=p.categoria_id, receta_id=p.receta_id,
            disponible=p.disponible,
        )


    def listar_disponibles(self) -> List[Plato]:
        return [
            Plato(id=p.id, nombre=p.nombre, precio=p.precio,
                  categoria_id=p.categoria_id, receta_id=p.receta_id,
                  disponible=p.disponible)
            for p in PlatoModel.objects.filter(disponible=True)
        ]
