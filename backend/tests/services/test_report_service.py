"""Report numbers: RV-ENC-YYYY-NNNNNN, sequential and never duplicated."""

import threading

import pytest

from app.db.database import SessionLocal
from app.db.models.encroachment import Report
from app.services.report_service import format_report_no, issue_report, next_report_no


def test_format():
    assert format_report_no("encroachment", 2026, 1) == "RV-ENC-2026-000001"
    assert format_report_no("intrusion", 2026, 42) == "RV-INT-2026-000042"


def test_numbers_are_sequential_per_kind_and_year():
    db = SessionLocal()
    try:
        assert next_report_no(db, "encroachment", 2026) == "RV-ENC-2026-000001"
        assert next_report_no(db, "encroachment", 2026) == "RV-ENC-2026-000002"
        assert next_report_no(db, "intrusion", 2026) == "RV-INT-2026-000001"
        assert next_report_no(db, "encroachment", 2027) == "RV-ENC-2027-000001"
        db.commit()
    finally:
        db.close()


def test_rolled_back_number_is_reused():
    db = SessionLocal()
    try:
        assert next_report_no(db, "encroachment", 2030) == "RV-ENC-2030-000001"
        db.rollback()
        assert next_report_no(db, "encroachment", 2030) == "RV-ENC-2030-000001"
        db.commit()
    finally:
        db.close()


def test_unknown_kind_or_reason_is_rejected():
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            next_report_no(db, "parking")
        with pytest.raises(ValueError):
            issue_report(db, "because")
    finally:
        db.rollback()
        db.close()


def test_issue_report_creates_a_row():
    db = SessionLocal()
    try:
        report = issue_report(db, "new_site")
        db.commit()
        assert db.get(Report, report.id).report_no.startswith("RV-ENC-")
        assert report.reason == "new_site"
    finally:
        db.close()


def test_concurrent_jobs_never_get_the_same_number():
    numbers, errors = [], []
    lock = threading.Lock()

    def worker():
        for _ in range(5):
            db = SessionLocal()
            try:
                no = next_report_no(db, "encroachment", 2031)
                db.commit()
                with lock:
                    numbers.append(no)
            except Exception as exc:  # noqa: BLE001 -- collected and asserted below
                errors.append(exc)
            finally:
                db.close()

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(numbers) == 30
    assert len(set(numbers)) == 30
    assert sorted(numbers) == [format_report_no("encroachment", 2031, i) for i in range(1, 31)]
