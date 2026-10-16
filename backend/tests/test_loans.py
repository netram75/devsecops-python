from conftest import days


def test_reserve_then_checkout_then_return(client, make_asset, make_loan):
    asset = make_asset("camera")
    loan = make_loan(asset["id"], start=0, due=3)
    assert loan["status"] == "reserved"
    assert loan["asset_tag"] == asset["tag"]

    r = client.post(f"/api/loans/{loan['id']}/checkout")
    assert r.status_code == 200
    assert r.json()["status"] == "checked_out" and r.json()["checked_out_at"]
    assert client.get(f"/api/assets/{asset['id']}").json()["available_now"] is False

    r = client.post(f"/api/loans/{loan['id']}/return")
    assert r.status_code == 200
    assert r.json()["status"] == "returned" and r.json()["returned_at"]
    assert r.json()["returned_late"] is False
    assert client.get(f"/api/assets/{asset['id']}").json()["available_now"] is True


def test_overlapping_reservation_is_a_conflict(client, make_asset, make_loan):
    asset = make_asset("camera")
    first = make_loan(asset["id"], start=1, due=4)
    r = client.post(
        "/api/loans",
        json={
            "asset_id": asset["id"],
            "borrower_name": "Ravi Kumar",
            "borrower_roll": "24BCS10001",
            "borrower_email": "ravi@example.edu",
            "start_date": days(3),
            "due_date": days(5),
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "asset_unavailable"
    assert f"loan #{first['id']}" in r.json()["detail"]


def test_back_to_back_loans_are_allowed(client, make_asset, make_loan):
    asset = make_asset("camera")
    make_loan(asset["id"], start=0, due=2)
    second = make_loan(asset["id"], start=2, due=4, roll="24BCS10002")
    assert second["status"] == "reserved"


def test_borrower_limit_is_enforced(client, make_asset, make_loan):
    for _ in range(3):
        make_loan(make_asset("lab_kit")["id"])
    extra = make_asset("lab_kit")
    r = client.post(
        "/api/loans",
        json={
            "asset_id": extra["id"],
            "borrower_name": "Asha Verma",
            "borrower_roll": "24bcs10329",
            "borrower_email": "asha@example.edu",
            "start_date": days(0),
            "due_date": days(2),
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "borrower_limit"


def test_loan_longer_than_category_limit_is_422(client, make_asset, make_loan):
    drone = make_asset("drone")
    r = make_loan(drone["id"], start=0, due=5, expect=422)
    assert r["code"] == "loan_too_long"


def test_start_in_the_past_is_422(client, make_asset, make_loan):
    r = make_loan(make_asset()["id"], start=-1, due=1, expect=422)
    assert r["code"] == "start_in_past"


def test_due_before_start_fails_validation(client, make_asset, make_loan):
    r = make_loan(make_asset()["id"], start=2, due=1, expect=422)
    assert "due_date must be after start_date" in r["detail"][0]["msg"]


def test_asset_in_maintenance_cannot_be_reserved(client, make_asset, make_loan):
    asset = make_asset(state="maintenance")
    r = make_loan(asset["id"], expect=409)
    assert r["code"] == "asset_not_in_service"


def test_unknown_asset_loan_is_404(client, make_loan):
    make_loan(4242, expect=404)


def test_illegal_transitions_return_409(client, make_asset, make_loan):
    loan = make_loan(make_asset()["id"])
    r = client.post(f"/api/loans/{loan['id']}/return")
    assert r.status_code == 409 and r.json()["code"] == "illegal_transition"
    assert client.post(f"/api/loans/{loan['id']}/cancel").status_code == 200
    r = client.post(f"/api/loans/{loan['id']}/checkout")
    assert r.status_code == 409
    assert "it is cancelled" in r.json()["detail"]


def test_checkout_before_start_date_is_refused(client, make_asset, make_loan):
    loan = make_loan(make_asset()["id"], start=2, due=4)
    r = client.post(f"/api/loans/{loan['id']}/checkout")
    assert r.status_code == 409 and r.json()["code"] == "too_early"


def test_unknown_action_is_422(client, make_asset, make_loan):
    loan = make_loan(make_asset()["id"])
    assert client.post(f"/api/loans/{loan['id']}/teleport").status_code == 422


def test_update_reservation_dates_rechecks_overlap(client, make_asset, make_loan):
    asset = make_asset("laptop")
    make_loan(asset["id"], start=5, due=8, roll="24BCS10002")
    mine = make_loan(asset["id"], start=0, due=3)
    r = client.put(f"/api/loans/{mine['id']}", json={"due_date": days(6)})
    assert r.status_code == 409
    r = client.put(f"/api/loans/{mine['id']}", json={"due_date": days(5), "purpose": "Hackathon"})
    assert r.status_code == 200
    assert r.json()["due_date"] == days(5) and r.json()["purpose"] == "Hackathon"


def test_checked_out_loan_cannot_be_edited_or_deleted(client, make_asset, make_loan):
    loan = make_loan(make_asset()["id"])
    client.post(f"/api/loans/{loan['id']}/checkout")
    assert client.put(f"/api/loans/{loan['id']}", json={"purpose": "x"}).status_code == 409
    r = client.delete(f"/api/loans/{loan['id']}")
    assert r.status_code == 409 and r.json()["code"] == "loan_locked"


def test_delete_reservation(client, make_asset, make_loan):
    loan = make_loan(make_asset()["id"])
    assert client.delete(f"/api/loans/{loan['id']}").status_code == 204
    assert client.get(f"/api/loans/{loan['id']}").status_code == 404


def test_overdue_loan_keeps_blocking_the_asset(client, make_asset, make_loan, shift_today):
    asset = make_asset("camera")
    loan = make_loan(asset["id"], start=0, due=2)
    client.post(f"/api/loans/{loan['id']}/checkout")

    shift_today(4)  # two days after it was due, still not returned
    body = client.get(f"/api/loans/{loan['id']}").json()
    assert body["overdue"] is True and body["days_overdue"] == 2
    assert [l["id"] for l in client.get("/api/loans", params={"overdue": True}).json()] == [loan["id"]]
    r = make_loan(asset["id"], start=4, due=6, roll="24BCS10002", expect=409)
    assert r["code"] == "asset_unavailable"

    returned = client.post(f"/api/loans/{loan['id']}/return").json()
    assert returned["returned_late"] is True


def test_list_loans_filters(client, make_asset, make_loan):
    a, b = make_asset(), make_asset("audio")
    l1 = make_loan(a["id"])
    make_loan(b["id"], roll="24BCS20002")
    client.post(f"/api/loans/{l1['id']}/checkout")
    assert len(client.get("/api/loans").json()) == 2
    assert [l["id"] for l in client.get("/api/loans", params={"status": "checked_out"}).json()] == [l1["id"]]
    assert len(client.get("/api/loans", params={"roll": "24bcs20002"}).json()) == 1
    assert len(client.get(f"/api/assets/{a['id']}/loans").json()) == 1


def test_stats_and_activity_feed(client, make_asset, make_loan):
    a, b = make_asset(), make_asset("vr")
    make_asset(state="maintenance")
    loan = make_loan(a["id"])
    client.post(f"/api/loans/{loan['id']}/checkout")
    make_loan(b["id"], start=1, due=3, roll="24BCS20002")

    s = client.get("/api/stats").json()
    assert s["assets_total"] == 3
    assert s["assets_in_service"] == 2
    assert s["on_loan_now"] == 1
    assert s["assets_available_now"] == 1
    assert s["loans_by_status"]["reserved"] == 1
    assert s["utilisation_pct"] == 50.0

    feed = client.get("/api/activity", params={"limit": 3}).json()
    assert len(feed) == 3
    assert feed[0]["action"] == "reserved"
    assert "checked out" in feed[1]["summary"]


def test_database_check_constraint_backs_up_the_api(client, make_asset):
    """Even if a bug skipped validation, the database refuses an impossible loan."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.db import engine

    asset = make_asset()
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO loans (asset_id, borrower_name, borrower_roll, borrower_email, purpose,"
            " start_date, due_date, status) VALUES (?, 'x', '24BCS1', 'x@y.z', '', '2026-01-05',"
            " '2026-01-01', 'reserved')",
            (asset["id"],),
        )
