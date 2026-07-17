from unittest.mock import MagicMock, patch
import pytest
from menu.services import PlatoService
from core.excepciones import RecursoNoEncontrado


class TestPlatoServiceConMock:

    def test_init_repos(self):
        plato_repo = MagicMock()
        categoria_repo = MagicMock()
        service = PlatoService(
            plato_repo=plato_repo, categoria_repo=categoria_repo
        )
        assert service.plato_repo == plato_repo
        assert service.categoria_repo == categoria_repo

    def test_obtener_por_id_valido(self):
        plato_repo = MagicMock()
        categoria_repo = MagicMock()
        plato_repo.obtener_por_id.return_value = MagicMock(
            id=1, nombre='Lomo Saltado'
        )
        service = PlatoService(
            plato_repo=plato_repo, categoria_repo=categoria_repo
        )
        result = service.obtener_por_id(1)
        assert result.nombre == 'Lomo Saltado'

    def test_obtener_por_id_no_encontrado(self):
        plato_repo = MagicMock()
        categoria_repo = MagicMock()
        plato_repo.obtener_por_id.return_value = None
        service = PlatoService(
            plato_repo=plato_repo, categoria_repo=categoria_repo
        )
        with pytest.raises(RecursoNoEncontrado):
            service.obtener_por_id(999)

    def test_toggle_disponible(self):
        plato_repo = MagicMock()
        categoria_repo = MagicMock()
        plato = MagicMock(id=1, disponible=True)
        plato_repo.obtener_por_id.return_value = plato
        plato_repo.guardar.return_value = plato
        service = PlatoService(
            plato_repo=plato_repo, categoria_repo=categoria_repo
        )
        result = service.toggle_disponible(1)
        assert result.disponible is False
