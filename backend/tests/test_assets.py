def test_create_asset_returns_what_was_stored(client):
    r = client.post(
        "/api/assets",
        json={"tag": "cam-101", "name": "  Sony A7 IV  ", "category": "camera", "location": "Media Lab"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["tag"] == "CAM-101"
    assert body["name"] == "Sony A7 IV"
    assert body["state"] == "in_service"
    assert body["available_now"] is True
    assert body["id"] > 0 and body["created_at"]


def test_duplicate_tag_is_a_conflict(client, make_asset):
    make_asset(tag="CAM-200")
    r = client.post("/api/assets", json={"tag": "CAM-200", "name": "Other", "category": "camera"})
    assert r.status_code == 409
    assert r.json()["code"] == "duplicate_tag"


def test_invalid_asset_is_rejected_with_422(client):
    r = client.post("/api/assets", json={"tag": "bad tag", "name": "x", "category": "spaceship"})
    assert r.status_code == 422
    fields = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"tag", "name", "category"} <= fields


def test_list_assets_filters_by_category_and_search(client, make_asset):
    make_asset("camera", name="Canon R6")
    make_asset("drone", name="DJI Mini 4")
    make_asset("drone", name="DJI Air 3", location="Robotics Lab")
    assert len(client.get("/api/assets").json()) == 3
    assert len(client.get("/api/assets", params={"category": "drone"}).json()) == 2
    found = client.get("/api/assets", params={"q": "robotics"}).json()
    assert [a["name"] for a in found] == ["DJI Air 3"]


def test_get_unknown_asset_is_404(client):
    r = client.get("/api/assets/9999")
    assert r.status_code == 404
    assert r.json()["detail"] == "asset 9999 not found"


def test_update_asset_changes_only_sent_fields(client, make_asset):
    asset = make_asset(location="Media Lab")
    r = client.put(f"/api/assets/{asset['id']}", json={"location": "Block C, Room 204"})
    assert r.status_code == 200
    assert r.json()["location"] == "Block C, Room 204"
    assert r.json()["name"] == asset["name"]


def test_asset_with_active_loan_cannot_go_to_maintenance(client, make_asset, make_loan):
    asset = make_asset()
    make_loan(asset["id"])
    r = client.put(f"/api/assets/{asset['id']}", json={"state": "maintenance"})
    assert r.status_code == 409
    assert r.json()["code"] == "asset_has_active_loans"


def test_delete_asset_without_history(client, make_asset):
    asset = make_asset()
    assert client.delete(f"/api/assets/{asset['id']}").status_code == 204
    assert client.get(f"/api/assets/{asset['id']}").status_code == 404


def test_delete_asset_with_loan_history_is_refused(client, make_asset, make_loan):
    asset = make_asset()
    loan = make_loan(asset["id"])
    client.post(f"/api/loans/{loan['id']}/cancel")
    r = client.delete(f"/api/assets/{asset['id']}")
    assert r.status_code == 409
    assert r.json()["code"] == "asset_has_history"
