from unittest.mock import MagicMock
import pytest
from menu.services import CategoriaService
from core.excepciones import RecursoNoEncontrado


class TestCategoriaServiceConMock:

    def test_listar_categorias(self):
        repo = MagicMock()
        repo.listar_con_platos.return_value = [
            MagicMock(id=1, nombre='Pizzas'),
            MagicMock(id=2, nombre='Bebidas'),
        ]
        service = CategoriaService(categoria_repo=repo)
        result = service.listar_categorias()
        assert len(result) == 2
        repo.listar_con_platos.assert_called_once()

    def test_obtener_por_id_valido(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = MagicMock(id=1, nombre='Pizzas')
        service = CategoriaService(categoria_repo=repo)
        result = service.obtener_por_id(1)
        assert result.nombre == 'Pizzas'

    def test_obtener_por_id_no_encontrado(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = None
        service = CategoriaService(categoria_repo=repo)
        with pytest.raises(RecursoNoEncontrado):
            service.obtener_por_id(999)

    def test_crear_categoria(self):
        repo = MagicMock()
        repo.guardar.return_value = MagicMock(id=1, nombre='Nueva')
        service = CategoriaService(categoria_repo=repo)
        result = service.crear(nombre='Nueva', es_bebida=False)
        repo.guardar.assert_called_once()
        assert result.id == 1
