"""Module-level registry for the public ``gateway_media_proxy`` wrapper.

Implementation submodules (``_helpers``, ``_resolution``, ``_proxy``)
read monkeypatchable attributes (``azure_default_model``,
``azure_word_voice``, ``word_tts_cache_path``,
``resolve_normal_word_audio_identity``, ``phonetic_identity``,
``httpx``) from the wrapper at call time so legacy tests that
``monkeypatch.setattr`` them on the wrapper continue to work after
the split. A ``sys.modules`` lookup is not enough because some tests
load the wrapper via
``importlib.util.spec_from_file_location`` and never register it
under its dotted name; this registry sidesteps that by binding the
wrapper's namespace dict directly.
"""

from __future__ import annotations


class _WrapperNS:
    """Attribute-access view over a bound module namespace.

    ``bind`` accepts either a module object (production imports
    register it via ``sys.modules[name]``) or a ``globals()`` dict
    (used by the wrapper itself and by tests that load the wrapper
    via ``importlib.util.spec_from_file_location`` without registering
    it in ``sys.modules``). Both expose their attributes through a
    shared ``__dict__``, so the binding logic is identical.
    """

    def __init__(self) -> None:
        self._ns: dict | None = None

    def bind(self, target) -> None:
        self._ns = target.__dict__ if hasattr(target, '__dict__') and not isinstance(target, dict) else target

    def __getattr__(self, name: str):
        if name == '_ns':
            raise AttributeError(name)
        if self._ns is None:
            raise AttributeError(
                'gateway_media_proxy wrapper has not been bound yet; '
                'import platform_sdk.gateway_media_proxy before calling helpers.'
            )
        try:
            return self._ns[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


_INSTANCE = _WrapperNS()


def set_wrapper(target) -> None:
    """Bind ``target`` (a module or a namespace dict) as the live wrapper."""
    _INSTANCE.bind(target)


def get_wrapper() -> _WrapperNS:
    """Return the live wrapper view; attributes mirror the bound namespace."""
    return _INSTANCE