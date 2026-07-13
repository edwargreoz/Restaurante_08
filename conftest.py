import pytest
from django.test import override_settings

CHANNEL_LAYERS_TEST = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


@pytest.fixture(autouse=True)
def _channel_layer_override():
    with override_settings(CHANNEL_LAYERS=CHANNEL_LAYERS_TEST):
        yield
