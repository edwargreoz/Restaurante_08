
from django.db import transaction
from core.excepciones import RecursoNoEncontrado
from dominio.puertos.repositorios import ICategoriaRepository
from menu.models import Categoria, Plato
from inventario.models import Receta


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
        from dominio.entidades.categoria import Categoria as CatDominio
        cat = CatDominio(
            id=None, nombre=nombre, es_bebida=es_bebida,
            orden_display=orden_display
        )
        return self.repo.guardar(cat)


class PlatoService:
    @staticmethod
    def obtener_por_id(plato_id: int) -> Plato:
        plato = Plato.objects.filter(id=plato_id).first()
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        return plato
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
    @transaction.atomic
    def actualizar(plato_id: int, **kwargs) -> Plato:
        plato = PlatoService.obtener_por_id(plato_id)
        categoria_id = kwargs.pop('categoria_id', None)
        if categoria_id:
            cat = Categoria.objects.filter(id=int(categoria_id)).first()
            if not cat:
                raise RecursoNoEncontrado('Categoría no encontrada')
            kwargs['categoria'] = cat
        for attr, value in kwargs.items():
            if attr == 'imagen' and not value:
                continue
            setattr(plato, attr, value)
        plato.save(update_fields=[
            'nombre', 'descripcion', 'precio', 'categoria',
            'receta', 'tiempo_preparacion_min', 'disponible', 'actualizado_en',
        ])
        return plato

    @staticmethod
    def eliminar(plato_id: int):
        plato = Plato.objects.filter(id=plato_id).first()
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        plato.eliminar()

    @staticmethod
    def toggle_disponible(plato_id: int) -> Plato:
        plato = Plato.objects.filter(id=plato_id).first()
        if not plato:
            raise RecursoNoEncontrado('Plato no encontrado')
        plato.disponible = not plato.disponible
        plato.save(update_fields=['disponible'])
        return plato
