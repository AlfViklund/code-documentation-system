import tempfile
from pathlib import Path
from docify.core.models import Feature, FeatureStatus, FeatureCheckState, SymbolAnchor
from docify.core.store import Store
from docify.checker.check import Checker

def test_checker_empty_body_validation():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(root=Path(tmpdir))
        feature = Feature(
            id="empty-feat",
            title="Empty Feature",
            status=FeatureStatus.IMPLEMENTED,
            body="## Что делает\n\n(описание фичи `empty-feat`)\n",
            anchors=[SymbolAnchor(type="symbol", path="dummy.py", symbol="dummy_func")]
        )
        store.save_feature(feature)

        checker = Checker(store)
        res, _ = checker.check_feature(feature, {})
        assert res.state == FeatureCheckState.EMPTY_BODY

def test_checker_fresh_feature():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(root=Path(tmpdir))
        feature = Feature(
            id="valid-feat",
            title="Valid Feature",
            status=FeatureStatus.IMPLEMENTED,
            body="## Overview\nThis feature is fully documented with sufficient detail to pass validation rules.",
        )
        store.save_feature(feature)

        checker = Checker(store)
        res, _ = checker.check_feature(feature, {})
        assert res.state == FeatureCheckState.UNIMPLEMENTED
