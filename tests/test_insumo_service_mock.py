from unittest.mock import MagicMock, patch
import pytest
from inventario.services import InsumoService
from core.excepciones import RecursoNoEncontrado


class TestInsumoServiceConMock:

    def test_init_repo(self):
        repo = MagicMock()
        service = InsumoService(insumo_repo=repo)
        assert service.repo == repo

    def test_obtener_por_id_valido(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = MagicMock(id=1, nombre='Harina')
        service = InsumoService(insumo_repo=repo)
        with patch('inventario.services.Insumo') as MockInsumo:
            MockInsumo.objects.get.return_value = MagicMock(
                id=1, nombre='Harina'
            )
            result = service.obtener_por_id(1)
            assert result.nombre == 'Harina'

    def test_obtener_por_id_no_encontrado(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = None
        service = InsumoService(insumo_repo=repo)
        with pytest.raises(RecursoNoEncontrado):
            service.obtener_por_id(999)
