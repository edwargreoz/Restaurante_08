from unittest.mock import MagicMock, patch
import pytest
from mesas.services import MesaService
from core.excepciones import RecursoNoEncontrado


class TestMesaServiceConMock:

    def test_init_repo(self):
        repo = MagicMock()
        service = MesaService(mesa_repo=repo)
        assert service.repo == repo

    @pytest.mark.django_db
    def test_cambiar_estado_mesa_no_encontrada(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = None
        service = MesaService(mesa_repo=repo)
        with pytest.raises(RecursoNoEncontrado):
            service.cambiar_estado(mesa_id=999, nuevo_estado='OCUPADA')

    @pytest.mark.django_db
    def test_marcar_libre_mesa_no_encontrada(self):
        repo = MagicMock()
        repo.obtener_por_id.return_value = None
        service = MesaService(mesa_repo=repo)
        with pytest.raises(RecursoNoEncontrado):
            service.marcar_libre(mesa_id=999)
