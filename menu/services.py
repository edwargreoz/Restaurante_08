
from core.excepciones import RecursoNoEncontrado
from dominio.puertos.repositorios import (
    ICategoriaRepository, IPlatoRepository, IRecetaRepository,
)
from dominio.entidades.categoria import Categoria as CategoriaDominio
from dominio.entidades.plato import Plato as PlatoDominio


class CategoriaService:
    def __init__(self, categoria_repo: ICategoriaRepository):
        self.repo = categoria_repo

    def listar_categorias(self):
        return self.repo.listar_con_platos()

    def obtener_por_id(self, categoria_id: int):
        cat = self.repo.obtener_por_id(categoria_id)
        if not cat:
            raise RecursoNoEncontrado('Categoría no encontrada')
        return cat

    def crear(self, nombre: str, es_bebida: bool = False,
              orden_display: int = 0):
        cat = CategoriaDominio(
            id=None, nombre=nombre, es_bebida=es_bebida,
            orden_display=orden_display
        )
        return self.repo.guardar(cat)


class PlatoService:
    def __init__(self, plato_repo: IPlatoRepository,
                 categoria_repo: ICategoriaRepository,
                 receta_repo: IRecetaRepository = None):
        self.plato_repo = plato_repo
        self.categoria_repo = categoria_repo
        self.receta_repo = receta_repo

    def listar(self):
        return self.plato_repo.listar()

    def obtener_por_id(self, plato_id: int):
        plato = self.plato_repo.obtener_por_id(plato_id)
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        return plato

    def crear(self, nombre: str, precio, categoria_id: int,
              receta_id: int, descripcion: str = '',
              tiempo_preparacion: int = 15,
              disponible: bool = True, imagen=None):
        categoria = self.categoria_repo.obtener_por_id(categoria_id)
        if not categoria:
            raise RecursoNoEncontrado('Categoría no encontrada')
        if self.receta_repo:
            receta = self.receta_repo.obtener_por_id(receta_id)
        else:
            receta = None
        if not receta:
            raise RecursoNoEncontrado('Receta no encontrada')
        plato = PlatoDominio(
            id=None, nombre=nombre, precio=precio,
            categoria_id=categoria_id, receta_id=receta_id,
            descripcion=descripcion,
            tiempo_preparacion_min=tiempo_preparacion,
            disponible=disponible,
        )
        return self.plato_repo.guardar(plato)

    def verificar_disponibilidad(self, plato_id: int) -> bool:
        plato = self.plato_repo.obtener_por_id(plato_id)
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        return plato.disponible

    def actualizar(self, plato_id: int, **kwargs):
        plato = self.plato_repo.obtener_por_id(plato_id)
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        categoria_id = kwargs.pop('categoria_id', None)
        if categoria_id:
            cat = self.categoria_repo.obtener_por_id(int(categoria_id))
            if not cat:
                raise RecursoNoEncontrado('Categoría no encontrada')
        kwargs.pop('imagen', None)
        for key, value in kwargs.items():
            if hasattr(plato, key):
                setattr(plato, key, value)
        return self.plato_repo.guardar(plato)

    def eliminar(self, plato_id: int):
        plato = self.plato_repo.obtener_por_id(plato_id)
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        self.plato_repo.eliminar(plato_id)

    def toggle_disponible(self, plato_id: int):
        plato = self.plato_repo.obtener_por_id(plato_id)
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        plato.disponible = not plato.disponible
        return self.plato_repo.guardar(plato)
