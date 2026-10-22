"""Grouping findings into sites and the review workflow. These run on the
suite's database: the haversine path on SQLite, the PostGIS path when the
suite runs on PostgreSQL (scripts/test_postgres.ps1, CI)."""

import uuid

import pytest
from sqlalchemy import text

from app.db.database import SessionLocal
from app.db.models.encroachment import EncroachmentFinding, Media
from app.services import site_service
from app.services.geo_service import Location
from app.services.site_service import InvalidTransition, assign_site, change_site_status

BASE = (12.9784, 77.5702)            # near Bengaluru City station
METRES_PER_DEG_LAT = 111_320.0


def north_of(metres: float) -> Location:
    return Location(BASE[0] + metres / METRES_PER_DEG_LAT, BASE[1], "pin")


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _finding(db, cls="structure_temporary", severity="high"):
    media = Media(sha256=uuid.uuid4().hex * 2, location_source="pin")
    db.add(media)
    db.flush()
    finding = EncroachmentFinding(
        media_id=media.id, cls=cls, label="hut", confidence=0.6,
        bbox_x1=0, bbox_y1=0, bbox_x2=10, bbox_y2=10, zone_hit="Z3",
        overlap_ratio=1.0, overlap_area_px=100.0, severity_score=0.9, severity=severity,
    )
    db.add(finding)
    db.flush()
    return finding


def test_photo_without_location_gets_no_site(db):
    assert assign_site(db, _finding(db), None) is None


def test_first_finding_creates_a_site_with_history(db):
    result = assign_site(db, _finding(db), north_of(0))
    db.flush()
    site = result.site
    assert result.created and not result.reopened
    assert (site.status, site.finding_count, site.max_severity) == ("reported", 1, "high")
    assert [h.to_status for h in site.history] == ["reported"]


def test_finding_10m_away_joins_the_same_site(db):
    first = assign_site(db, _finding(db, severity="medium"), north_of(0)).site
    db.flush()
    second = assign_site(db, _finding(db, severity="critical"), north_of(10))
    assert second.site.id == first.id and not second.created
    assert first.finding_count == 2
    assert first.max_severity == "critical"


def test_finding_60m_away_starts_a_new_site(db):
    first = assign_site(db, _finding(db), north_of(0)).site
    db.flush()
    far = assign_site(db, _finding(db), north_of(60))
    assert far.created and far.site.id != first.id


def test_different_class_at_the_same_spot_is_a_different_site(db):
    hut = assign_site(db, _finding(db, cls="structure_temporary"), north_of(0)).site
    db.flush()
    tree = assign_site(db, _finding(db, cls="vegetation"), north_of(0))
    assert tree.created and tree.site.id != hut.id


def test_nearest_site_wins_when_two_are_in_range(db):
    a = assign_site(db, _finding(db), north_of(0)).site
    db.flush()
    b = assign_site(db, _finding(db), north_of(30)).site      # 30 m: its own site
    db.flush()
    assert a.id != b.id
    joined = assign_site(db, _finding(db), north_of(22))       # 22 m from a, 8 m from b
    assert joined.site.id == b.id


def test_resolved_site_found_again_is_reopened(db):
    site = assign_site(db, _finding(db), north_of(0)).site
    db.flush()
    for status in ("under_review", "verified", "resolved"):
        change_site_status(db, site, status, actor="officer")
    db.flush()
    again = assign_site(db, _finding(db), north_of(5))
    db.flush()
    assert again.reopened and again.site.id == site.id
    assert site.status == "reported"
    assert site.history[-1].from_status == "resolved"
    assert "re-encroached" in site.history[-1].note


def test_false_positive_site_is_not_reopened_but_keeps_the_finding(db):
    site = assign_site(db, _finding(db), north_of(0)).site
    db.flush()
    change_site_status(db, site, "false_positive", note="signal relay hut, railway property")
    db.flush()
    again = assign_site(db, _finding(db), north_of(5))
    assert not again.reopened and site.status == "false_positive"
    assert site.finding_count == 2


def test_workflow_rejects_invalid_moves(db):
    site = assign_site(db, _finding(db), north_of(0)).site
    db.flush()
    with pytest.raises(InvalidTransition):
        change_site_status(db, site, "resolved")          # reported cannot jump to resolved
    with pytest.raises(Exception, match="Unknown status"):
        change_site_status(db, site, "deleted")
    entry = change_site_status(db, site, "under_review", note="checking", actor="officer")
    assert (entry.from_status, entry.to_status, entry.actor) == ("reported", "under_review", "officer")


def test_postgis_spatial_index_exists_on_postgresql(db):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL only")
    found = db.execute(text(
        "SELECT 1 FROM pg_indexes WHERE tablename = 'encroachment_sites' AND indexname = 'ix_encroachment_sites_geog'"
    )).scalar()
    assert found == 1
    assert site_service.find_nearby_site(db, "structure_temporary", *BASE) is None
