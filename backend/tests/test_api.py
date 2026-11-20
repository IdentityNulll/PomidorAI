"""End-to-end tests for the PomidorAI API."""

from io import BytesIO

from PIL import Image

from app import session as sess
from tests.conftest import make_image, post_scan, session_cookie


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_full_result_shape(client):
    response = post_scan(client)
    assert response.status_code == 200
    body = response.json()

    assert body["id"]
    assert set(body["plant"]) == {"id", "commonName", "scientificName", "confidence"}
    assert 0.0 <= body["plant"]["confidence"] <= 1.0

    predictions = body["health"]["predictions"]
    assert 1 <= len(predictions) <= 3
    assert any(p["label"] == "Sog'lom" for p in predictions)
    assert all(0.0 <= p["confidence"] <= 1.0 for p in predictions)

    info = body["info"]
    assert set(info) == {
        "description", "howItGrows", "water", "sunlight",
        "soil", "season", "commonDiseases", "careTips",
    }
    assert isinstance(info["commonDiseases"], list)
    assert isinstance(info["careTips"], list)
    assert info["careTips"]


def test_analyze_sets_session_cookie(client):
    response = post_scan(client)
    assert sess.COOKIE_NAME in response.cookies
    assert sess.unsign(response.cookies[sess.COOKIE_NAME])


def test_analyze_writes_image_and_thumbnail(client, uploads):
    post_scan(client)
    files = sorted(p.name for p in uploads.iterdir())
    assert len(files) == 2
    assert any(name.endswith("_thumb.jpg") for name in files)


def test_analyze_strips_exif(client, uploads):
    """EXIF can carry GPS coordinates, so stored files must keep none of it."""
    source = Image.new("RGB", (100, 100), "green")
    exif = source.getexif()
    exif[0x010F] = "TestPhone"  # Make
    exif[0x0110] = "TestModel"  # Model
    buffer = BytesIO()
    source.save(buffer, format="JPEG", exif=exif)
    buffer.seek(0)

    assert dict(Image.open(buffer).getexif())  # the upload really has EXIF
    buffer.seek(0)

    response = client.post(
        "/api/analyze", files={"image": ("geo.jpg", buffer, "image/jpeg")}
    )
    assert response.status_code == 200

    for stored in uploads.iterdir():
        assert not dict(Image.open(stored).getexif())


def test_analyze_resizes_to_max_1280(client, uploads):
    big = make_image(size=(3000, 2000))
    client.post("/api/analyze", files={"image": ("big.jpg", big, "image/jpeg")})

    stored = next(p for p in uploads.iterdir() if not p.name.endswith("_thumb.jpg"))
    assert max(Image.open(stored).size) == 1280


def test_analyze_rejects_non_image(client):
    response = client.post(
        "/api/analyze", files={"image": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_analyze_ignores_client_declared_type(client):
    """A text file renamed to .jpg with an image mime type must still be rejected."""
    response = client.post(
        "/api/analyze", files={"image": ("fake.jpg", b"not really a jpeg", "image/jpeg")}
    )
    assert response.status_code == 400


def test_analyze_rejects_oversized_file(client):
    payload = b"\xff\xd8\xff" + b"0" * (9 * 1024 * 1024)
    response = client.post(
        "/api/analyze", files={"image": ("huge.jpg", payload, "image/jpeg")}
    )
    assert response.status_code == 413


def test_analyze_requires_a_file(client):
    assert client.post("/api/analyze").status_code == 422


def test_list_is_empty_without_a_session(client):
    response = client.get("/api/scans")
    assert response.status_code == 200
    assert response.json() == {"scans": [], "cursor": None}


def test_list_returns_newest_first(client):
    for _ in range(3):
        post_scan(client, "listing")

    scans = client.get("/api/scans", cookies=session_cookie("listing")).json()["scans"]
    assert len(scans) == 3
    timestamps = [s["createdAt"] for s in scans]
    assert timestamps == sorted(timestamps, reverse=True)


def test_get_scan_returns_info_card(client):
    scan_id = post_scan(client, "detail").json()["id"]

    response = client.get(f"/api/scans/{scan_id}", cookies=session_cookie("detail"))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == scan_id
    assert body["info"]["description"]
    assert body["createdAt"]


def test_get_missing_scan_is_404(client):
    response = client.get("/api/scans/nope", cookies=session_cookie("whoever"))
    assert response.status_code == 404


def test_image_and_thumb_are_served_to_owner(client):
    scan_id = post_scan(client, "owner").json()["id"]
    cookies = session_cookie("owner")

    for suffix in ("image", "thumb"):
        response = client.get(f"/api/scans/{scan_id}/{suffix}", cookies=cookies)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert Image.open(BytesIO(response.content)).format == "JPEG"


def test_delete_one_scan_removes_record_and_files(client, uploads):
    scan_id = post_scan(client, "deleter").json()["id"]
    cookies = session_cookie("deleter")

    assert client.delete(f"/api/scans/{scan_id}", cookies=cookies).status_code == 200
    assert client.get(f"/api/scans/{scan_id}", cookies=cookies).status_code == 404
    assert list(uploads.iterdir()) == []


def test_delete_all_scans(client, uploads):
    for _ in range(3):
        post_scan(client, "clearer")
    cookies = session_cookie("clearer")

    assert client.delete("/api/scans", cookies=cookies).status_code == 200
    assert client.get("/api/scans", cookies=cookies).json()["scans"] == []
    assert list(uploads.iterdir()) == []


def test_pagination_walks_every_scan_once(client):
    created = {post_scan(client, "pager").json()["id"] for _ in range(5)}
    cookies = session_cookie("pager")

    seen = []
    cursor = None
    for _ in range(10):
        url = "/api/scans?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = client.get(url, cookies=cookies).json()
        seen.extend(s["id"] for s in page["scans"])
        cursor = page["cursor"]
        if not cursor:
            break

    assert cursor is None
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == created


def test_sessions_cannot_see_each_other(client):
    mine = post_scan(client, "alice").json()["id"]
    theirs = post_scan(client, "bob").json()["id"]

    alice = session_cookie("alice")
    bob = session_cookie("bob")

    assert [s["id"] for s in client.get("/api/scans", cookies=alice).json()["scans"]] == [mine]
    assert [s["id"] for s in client.get("/api/scans", cookies=bob).json()["scans"]] == [theirs]

    assert client.get(f"/api/scans/{theirs}", cookies=alice).status_code == 404
    assert client.get(f"/api/scans/{theirs}/image", cookies=alice).status_code == 404
    assert client.delete(f"/api/scans/{theirs}", cookies=alice).status_code == 404

    # Bob's scan survived Alice's attempt to delete it.
    assert client.get(f"/api/scans/{theirs}", cookies=bob).status_code == 200


def test_forged_cookie_is_ignored(client):
    post_scan(client, "victim")
    forged = {sess.COOKIE_NAME: "victim"}  # unsigned
    assert client.get("/api/scans", cookies=forged).json()["scans"] == []


def test_history_is_capped(client, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "HISTORY_LIMIT", 3)
    for _ in range(5):
        post_scan(client, "capped")

    scans = client.get(
        "/api/scans?limit=50", cookies=session_cookie("capped")
    ).json()["scans"]
    assert len(scans) == 3
