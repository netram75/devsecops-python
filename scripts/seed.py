#!/usr/bin/env python3
"""Seed GearLoop with a realistic campus catalogue, using only the public API.

    API=http://localhost:3000 python3 scripts/seed.py
    API=http://127.0.0.1 HOST_HEADER=gearloop.local python3 scripts/seed.py   # via Ingress

Standard library only. Re-running is safe: existing tags are skipped (409).
Loans can only start today or later (an API rule), so history and overdue items
are produced afterwards by scripts/age-demo-data.sql, which shifts a few loans back.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

API = os.environ.get("API", "http://localhost:3000").rstrip("/")
HOST = os.environ.get("HOST_HEADER")

ASSETS = [
    ("CAM-101", "Sony A7 IV + 28-70mm kit", "camera", "Media Lab, Block B", "2 batteries, 128 GB card"),
    ("CAM-102", "Canon EOS R6 Mark II", "camera", "Media Lab, Block B", "Body only"),
    ("CAM-103", "Fujifilm X-T5 + 18-55mm", "camera", "Media Lab, Block B", ""),
    ("CAM-104", "GoPro HERO13 Black", "camera", "Sports Complex desk", "Chest + helmet mounts"),
    ("DRN-201", "DJI Mini 4 Pro Fly More", "drone", "Robotics Lab, Block D", "3 batteries; DGCA rules apply"),
    ("DRN-202", "DJI Air 3S", "drone", "Robotics Lab, Block D", ""),
    ("DRN-203", "DJI Avata 2 FPV", "drone", "Robotics Lab, Block D", "Goggles 3 + motion controller"),
    ("AUD-301", "Zoom H6 field recorder", "audio", "Media Lab, Block B", ""),
    ("AUD-302", "Rode Wireless PRO kit", "audio", "Media Lab, Block B", "Two transmitters"),
    ("AUD-303", "Shure SM7B podcast mic", "audio", "Podcast Room 2", "With Cloudlifter"),
    ("LAB-401", "Arduino Mega sensor kit", "lab_kit", "Electronics Lab, Block C", "37 sensors"),
    ("LAB-402", "Raspberry Pi 5 starter kit", "lab_kit", "Electronics Lab, Block C", "8 GB, case, PSU"),
    ("LAB-403", "Rigol DS1054Z oscilloscope", "lab_kit", "Electronics Lab, Block C", "4 probes"),
    ("LAB-404", "NVIDIA Jetson Orin Nano kit", "lab_kit", "AI Lab, Block A", ""),
    ("LAP-501", 'MacBook Pro 14" M4', "laptop", "IT Help Desk", "Final Cut + Xcode installed"),
    ("LAP-502", "ThinkPad P1 workstation", "laptop", "IT Help Desk", "RTX GPU, CUDA ready"),
    ("VR-601", "Meta Quest 3 512 GB", "vr", "XR Studio", ""),
    ("VR-602", "Apple Vision Pro", "vr", "XR Studio", "Staff approval needed"),
    ("VR-603", "HTC Vive XR Elite", "vr", "XR Studio", "Tracking issues"),
]
STATE = {"DRN-203": "maintenance", "VR-603": "retired"}

STUDENTS = [
    ("Asha Verma", "24BCS10329"),
    ("Rohan Mehta", "24BCS10411"),
    ("Isha Kulkarni", "23BCS10087"),
    ("Kabir Singh", "24BDS10052"),
    ("Meera Iyer", "25BCS10213"),
    ("Arjun Nair", "23BCS10166"),
    ("Zoya Khan", "24BCS10275"),
    ("Dev Patel", "25BDS10019"),
]

# (tag, student index, start offset, length in days, purpose, then-what)
LOANS = [
    ("CAM-101", 0, 0, 3, "Photography club: campus fest shoot", "checkout"),
    ("DRN-201", 1, 0, 2, "Aerial survey for civil project", "checkout"),
    ("LAB-402", 2, 0, 10, "IoT capstone prototype", "checkout"),
    ("AUD-302", 3, 0, 4, "Interview series for the college podcast", "checkout"),
    ("LAP-501", 4, 0, 7, "Editing the fest aftermovie", "checkout"),
    ("VR-601", 5, 0, 3, "HCI user study", "checkout"),
    ("CAM-104", 6, 0, 2, "Inter-college football match", "checkout"),
    ("LAB-403", 7, 0, 5, "Signals lab assignment", "checkout"),
    ("CAM-102", 2, 0, 2, "Portrait session", None),
    ("AUD-301", 6, 0, 3, "Ambient sound recording", None),
    ("LAB-404", 1, 1, 6, "Edge AI hackathon", None),
    ("DRN-202", 3, 2, 2, "Drone club practice", None),
    ("CAM-103", 4, 3, 4, "Heritage walk documentation", None),
    ("CAM-101", 7, 4, 3, "Short film project", None),
    ("LAP-502", 5, 5, 7, "Thesis model training", None),
    ("VR-602", 0, 6, 2, "XR studio demo day", None),
    ("AUD-303", 2, 0, 1, "Podcast episode 12", "checkout-return"),
    ("LAB-401", 3, 0, 1, "Sensor workshop", "checkout-return"),
    ("CAM-103", 5, 0, 1, "Club headshots", "checkout-return"),
    ("DRN-202", 6, 0, 1, "Test flight", "cancel"),
]


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Accept", "application/json")
    if HOST:
        req.add_header("Host", HOST)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=10) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def main() -> int:
    status, info = call("GET", "/api/info")
    if status != 200:
        print(f"API not reachable at {API}: {status}", file=sys.stderr)
        return 1
    today = date.fromisoformat(info["today"])
    print(f"seeding {API} (build {info['version']}, campus date {today})")

    ids = {}
    for tag, name, cat, loc, notes in ASSETS:
        status, body = call(
            "POST",
            "/api/assets",
            {"tag": tag, "name": name, "category": cat, "location": loc, "notes": notes},
        )
        if status == 201:
            ids[tag] = body["id"]
            print(f"  + asset {tag:8} {name}")
        elif status == 409:
            print(f"  = asset {tag:8} exists")
    for a in call("GET", "/api/assets")[1]:
        ids[a["tag"]] = a["id"]

    created = 0
    for tag, who, offset, length, purpose, then in LOANS:
        name, roll = STUDENTS[who]
        start = today + timedelta(days=offset)
        status, loan = call(
            "POST",
            "/api/loans",
            {
                "asset_id": ids[tag],
                "borrower_name": name,
                "borrower_roll": roll,
                "borrower_email": f"{name.split()[0].lower()}.{roll.lower()}@campus.example",
                "purpose": purpose,
                "start_date": start.isoformat(),
                "due_date": (start + timedelta(days=length)).isoformat(),
            },
        )
        if status != 201:
            print(f"  ! loan {tag} for {name}: {status} {loan.get('detail') if loan else ''}")
            continue
        created += 1
        steps = {"checkout": ["checkout"], "checkout-return": ["checkout", "return"], "cancel": ["cancel"]}
        for action in steps.get(then, []):
            call("POST", f"/api/loans/{loan['id']}/{action}")
        print(f"  + loan #{loan['id']:<3} {tag:8} {name:14} {start} +{length}d {then or 'reserved'}")

    for tag, state in STATE.items():
        call("PUT", f"/api/assets/{ids[tag]}", {"state": state})
        print(f"  ~ {tag} -> {state}")

    # Show the rules working: these two must be refused.
    status, body = call(
        "POST",
        "/api/loans",
        {
            "asset_id": ids["CAM-101"],
            "borrower_name": "Rohan Mehta",
            "borrower_roll": "24BCS10411",
            "borrower_email": "rohan@campus.example",
            "start_date": today.isoformat(),
            "due_date": (today + timedelta(days=2)).isoformat(),
        },
    )
    print(f"  overlap check  -> {status} {body.get('code')}: {body.get('detail')}")
    status, body = call(
        "POST",
        "/api/loans",
        {
            "asset_id": ids["DRN-202"],
            "borrower_name": "Asha Verma",
            "borrower_roll": "24BCS10329",
            "borrower_email": "asha@campus.example",
            "start_date": (today + timedelta(days=8)).isoformat(),
            "due_date": (today + timedelta(days=14)).isoformat(),
        },
    )
    print(f"  max-days check -> {status} {body.get('code')}: {body.get('detail')}")
    print(f"done: {len(ids)} assets, {created} new loans")
    return 0


if __name__ == "__main__":
    sys.exit(main())
