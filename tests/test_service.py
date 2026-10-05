from bridge.client import BridgeClient
from freecad_addon import service as service_module
from freecad_addon.service import BridgeService


def test_service_handles_session_info(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    service = BridgeService(socket_path, lambda: {"connected": True, "active_document": None})
    service.start()
    try:
        assert BridgeClient(socket_path).call("get_session_info") == {
            "connected": True,
            "active_document": None,
        }
    finally:
        service.stop()


def test_service_reports_unknown_method(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")
    service = BridgeService(socket_path)
    service.start()
    try:
        try:
            BridgeClient(socket_path).call("unknown")
        except ConnectionError as exc:
            assert "Unsupported bridge method" in str(exc)
        else:
            raise AssertionError("Expected an unknown-method error")
    finally:
        service.stop()


def test_service_preserves_request_id_for_provider_errors(tmp_path) -> None:
    socket_path = str(tmp_path / "bridge.sock")

    def fail():
        raise RuntimeError("session unavailable")

    service = BridgeService(socket_path, fail)
    service.start()
    try:
        try:
            BridgeClient(socket_path).call("get_session_info")
        except ConnectionError as exc:
            assert "session unavailable" in str(exc)
        else:
            raise AssertionError("Expected a provider error")
    finally:
        service.stop()


def test_document_inspection_serializes_documents(monkeypatch) -> None:
    class View:
        Visibility = True

    class Child:
        Name = "Box"
        Label = "Box"
        TypeId = "Part::Box"
        ViewObject = View()
        Group = []
        Parents = []

    class Document:
        Name = "Test"
        Label = "Test document"
        Modified = False
        Objects = [Child()]

    class FreeCAD:
        ActiveDocument = Document()

        @staticmethod
        def listDocuments():
            return {"Test": FreeCAD.ActiveDocument}

        @staticmethod
        def getDocument(name):
            return FreeCAD.ActiveDocument if name == "Test" else None

    monkeypatch.setattr(service_module, "_freecad", lambda: FreeCAD)
    assert service_module.list_freecad_documents() == [
        {
            "name": "Test",
            "label": "Test document",
            "modified": False,
            "object_count": 1,
        }
    ]
    tree = service_module.get_freecad_document_tree({"document": "Test"})
    assert tree["objects"][0]["name"] == "Box"


def test_document_inspection_supports_freecad_without_modified(monkeypatch) -> None:
    class Document:
        Name = "Test"
        Label = "Test document"
        Objects = []

        def getObject(self, name):
            return None

    class FreeCAD:
        ActiveDocument = Document()

        @staticmethod
        def listDocuments():
            return {"Test": FreeCAD.ActiveDocument}

        @staticmethod
        def getDocument(name):
            return FreeCAD.ActiveDocument if name == "Test" else None

    monkeypatch.setattr(service_module, "_freecad", lambda: FreeCAD)
    assert service_module.list_freecad_documents() == [
        {
            "name": "Test",
            "label": "Test document",
            "modified": False,
            "object_count": 0,
        }
    ]
    assert service_module.get_freecad_document_tree({"document": "Test"})["modified"] is False
