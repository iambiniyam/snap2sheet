from fastapi.testclient import TestClient

from snap2sheet import server
from snap2sheet.models import Receipt


def test_scan_api_marks_duplicates_and_keeps_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "OUTPUT_DIR", tmp_path)

    def fake_extract(path, order="mdy", source=None, ocr_backend="auto"):
        name = source or path.name
        return Receipt(source=name, merchant="Cafe", date="2026-03-12", total=10.0)

    monkeypatch.setattr(server, "extract_file", fake_extract)

    client = TestClient(server.app)
    response = client.post(
        "/api/scan",
        files=[
            ("files", ("one.png", b"one", "image/png")),
            ("files", ("two.png", b"two", "image/png")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["duplicate_count"] == 1
    assert len(payload["receipts"]) == 2

    first, second = payload["receipts"]
    assert first["file"] == "one.png"
    assert first["duplicate"] is False
    assert first["duplicate_of"] is None
    assert second["file"] == "two.png"
    assert second["duplicate"] is True
    assert second["duplicate_of"] == "one.png"
