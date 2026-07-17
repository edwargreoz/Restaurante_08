from unittest.mock import MagicMock, patch
import pytest
from caja.services import CajaService
from core.excepciones import CajaNoAbierta


class TestCajaServiceConMock:

    def test_init_repo(self):
        repo = MagicMock()
        service = CajaService(caja_repo=repo)
        assert service.repo == repo

    def test_obtener_activa_valida(self):
        repo = MagicMock()
        repo.obtener_abierta.return_value = MagicMock(id=1, estado='ABIERTA')
        service = CajaService(caja_repo=repo)
        with patch('caja.services.Caja') as MockCaja:
            MockCaja.objects.filter.return_value.first.return_value = MagicMock(
                id=1, estado='ABIERTA'
            )
            result = service.obtener_activa()
            assert result.estado == 'ABIERTA'

    def test_obtener_activa_no_encontrada(self):
        repo = MagicMock()
        repo.obtener_abierta.return_value = None
        service = CajaService(caja_repo=repo)
        with pytest.raises(CajaNoAbierta):
            service.obtener_activa()
