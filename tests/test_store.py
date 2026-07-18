import tempfile
from pathlib import Path
from docify.core.models import Feature, Spec, BacklogItem, Priority, FeatureStatus
from docify.core.store import Store

def test_store_feature_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(root=Path(tmpdir))
        feature = Feature(
            id="test-feat",
            title="Test Feature",
            status=FeatureStatus.IMPLEMENTED,
            priority=Priority.P0,
            tags=["test", "unit"],
            body="## Overview\nThis is a real feature body with enough content to pass empty body validation."
        )
        store.save_feature(feature)

        loaded = store.get_feature("test-feat")
        assert loaded is not None
        assert loaded.id == "test-feat"
        assert loaded.title == "Test Feature"
        assert loaded.status == FeatureStatus.IMPLEMENTED
        assert loaded.priority == Priority.P0
        assert loaded.tags == ["test", "unit"]
        assert "real feature body" in loaded.body

def test_store_spec_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(root=Path(tmpdir))
        spec = Spec(
            id="spec-001",
            title="User Auth Spec",
            source="Product Team",
            features=[{"id": "auth-login", "action": "create"}]
        )
        store.save_spec(spec)

        loaded = store.get_spec("spec-001")
        assert loaded is not None
        assert loaded.id == "spec-001"
        assert loaded.title == "User Auth Spec"
        assert len(loaded.features) == 1
        assert loaded.features[0].id == "auth-login"

def test_store_backlog_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(root=Path(tmpdir))
        item = BacklogItem(
            id="debt-01",
            title="Refactor Store class",
            type="debt",
            status="open",
            priority=Priority.P1,
            body="Technical debt details."
        )
        store.save_backlog_item(item)

        loaded = store.get_backlog_item("debt-01")
        assert loaded is not None
        assert loaded.id == "debt-01"
        assert loaded.title == "Refactor Store class"
        assert loaded.type == "debt"
