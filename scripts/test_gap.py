"""Quick test for gap analysis API."""
from io import BytesIO
from pathlib import Path

from app import app

data_path = Path(__file__).parent.parent / "data" / "rental_survey.xlsx"

with app.test_client() as c:
    with data_path.open("rb") as f:
        c.post(
            "/api/upload",
            data={"survey_file": (BytesIO(f.read()), "rental_survey.xlsx")},
            content_type="multipart/form-data",
        )
    c.post(
        "/api/section-names",
        json={"names": {"1": "Service satisfaction", "2": "Managers guidance", "3": "Booking pricing"}},
    )
    meta = c.get("/api/gap-analysis/meta").get_json()
    print("meta ok:", meta.get("ok"), "sections:", len(meta.get("sections", [])))
    res = c.post(
        "/api/gap-analysis/compute",
        json={"scale": "1-5", "metric": "top2", "section": "all"},
    ).get_json()
    print("compute ok:", res.get("ok"))
    print("summary:", res.get("summary"))
    print("biplot points:", len(res.get("biplot", [])))
    print("priority:", len(res.get("priority_actions", [])))
    page = c.get("/gap-analysis")
    print("page status:", page.status_code)
