from conftest import days


def test_health_does_not_need_the_database(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_checks_the_migrated_schema(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_info_publishes_the_lending_rules(client):
    body = client.get("/api/info").json()
    assert body["app"] == "GearLoop"
    assert body["version"] == "test"
    assert body["rules"]["max_active_loans"] == 3
    assert body["rules"]["max_loan_days"]["drone"] == 3
    assert "lab_kit" in body["categories"]


def test_metrics_expose_http_and_business_series(client, make_asset, make_loan):
    asset = make_asset("drone")
    loan = make_loan(asset["id"], start=0, due=2)
    client.post(f"/api/loans/{loan['id']}/checkout")
    client.post("/api/loans", json={**_loan_body(asset["id"]), "borrower_roll": "24BCS99999"})

    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'http_request_duration_seconds_bucket{handler="/api/loans",le="0.005"' in text or (
        'le="0.005"' in text
    )
    assert 'gearloop_loans{status="checked_out"} 1.0' in text
    assert 'gearloop_assets{state="in_service"} 1.0' in text
    assert "gearloop_assets_available_now 0.0" in text
    assert 'gearloop_loan_transitions_total{action="checkout"}' in text
    assert 'gearloop_rule_rejections_total{rule="asset_unavailable"}' in text
    assert "gearloop_db_up 1.0" in text


def _loan_body(asset_id):
    return {
        "asset_id": asset_id,
        "borrower_name": "Ravi Kumar",
        "borrower_roll": "24BCS10001",
        "borrower_email": "ravi@example.edu",
        "start_date": days(0),
        "due_date": days(1),
    }
