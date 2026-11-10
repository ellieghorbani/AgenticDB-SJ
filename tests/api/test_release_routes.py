"""Tests for the v1.0 release and demo routes."""

from app.release_metrics import METRICS_PATH


def test_demo_page_is_available(client):
    response = client.get("/demo")
    assert response.status_code == 200
    assert "AgenticDB-SJ" in response.text
    assert "Run the copilot" in response.text


def test_release_metrics_returns_typed_not_built_response(client, monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr("app.release_metrics.METRICS_PATH", missing)

    response = client.get("/api/v1/release/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_built"
    assert payload["version"] == "1.0.0"


def test_release_metrics_reads_generated_artifact(client, monkeypatch, tmp_path):
    metrics = tmp_path / "final_evaluation.json"
    metrics.write_text(
        """
        {
          "status": "ready",
          "project": "AgenticDB-SJ",
          "version": "1.0.0",
          "generated_at": "2026-11-10T00:00:00+00:00",
          "all_benchmarks_passed": true,
          "benchmark_count": 8,
          "aggregate_passed": 100,
          "aggregate_total": 100,
          "aggregate_pass_rate": 1.0,
          "benchmarks": [],
          "data_snapshot": null,
          "database": null,
          "llm": null,
          "embedding_comparison": null,
          "artifacts": {},
          "notes": [],
          "extra_metrics": {}
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.release_metrics.METRICS_PATH", metrics)

    response = client.get("/api/v1/release/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["aggregate_pass_rate"] == 1.0
