from typing import Optional, List
from menu.models import Categoria as CategoriaModel
from dominio.entidades.categoria import Categoria


class CategoriaRepository:
    def obtener_por_id(self, categoria_id: int) -> Optional[Categoria]:
        try:
            c = CategoriaModel.objects.get(id=categoria_id)
            return Categoria(id=c.id, nombre=c.nombre, es_bebida=c.es_bebida)
        except CategoriaModel.DoesNotExist:
            return None

    def guardar(self, categoria: Categoria) -> Categoria:
        c, _ = CategoriaModel.objects.update_or_create(
            id=categoria.id,
            defaults={'nombre': categoria.nombre, 'es_bebida': categoria.es_bebida}
        )
        return Categoria(id=c.id, nombre=c.nombre, es_bebida=c.es_bebida)

    def listar(self) -> List[Categoria]:
        return [
            Categoria(id=c.id, nombre=c.nombre, es_bebida=c.es_bebida)
            for c in CategoriaModel.objects.all()
        ]