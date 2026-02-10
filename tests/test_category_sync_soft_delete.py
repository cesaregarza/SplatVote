"""Tests for survey soft-delete reconciliation in category sync."""

from __future__ import annotations

import pytest

from vote_api.models.database import Category
from vote_api.services.category_sync import CategorySyncService


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ExecuteResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)


class _FakeSession:
    def __init__(self, categories):
        self._categories = categories
        self.flush_calls = 0

    async def execute(self, _statement):
        return _ExecuteResult(self._categories)

    async def flush(self):
        self.flush_calls += 1


@pytest.mark.asyncio
async def test_close_removed_surveys_soft_deletes_missing_keys():
    removed = Category(
        name="Removed Survey Question",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "old_survey"},
    )
    still_present = Category(
        name="Current Survey Question",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "survey_v1"},
    )
    not_survey = Category(
        name="Regular Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={},
    )

    session = _FakeSession([removed, still_present, not_survey])
    service = CategorySyncService(session)

    closed_count = await service._close_removed_surveys({"survey_v1"})

    assert closed_count == 1
    assert removed.is_active is False
    assert removed.is_soft_deleted is True
    assert still_present.is_active is True
    assert still_present.is_soft_deleted is False
    assert not_survey.is_active is True
    assert not_survey.is_soft_deleted is False
    assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_close_removed_surveys_no_changes_skips_flush():
    already_soft_deleted = Category(
        name="Already Deleted",
        comparison_mode="single_choice",
        is_active=False,
        is_soft_deleted=True,
        settings={"survey_key": "old_survey"},
    )
    still_present = Category(
        name="Current Survey Question",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "survey_v1"},
    )

    session = _FakeSession([already_soft_deleted, still_present])
    service = CategorySyncService(session)

    closed_count = await service._close_removed_surveys({"survey_v1"})

    assert closed_count == 0
    assert session.flush_calls == 0


@pytest.mark.asyncio
async def test_sync_all_soft_deletes_when_surveys_dir_missing(tmp_path):
    removed = Category(
        name="Removed Survey Question",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "old_survey"},
    )
    session = _FakeSession([removed])
    service = CategorySyncService(session, data_dir=str(tmp_path))

    async def _commit():
        return None

    session.commit = _commit  # type: ignore[attr-defined]

    results = await service.sync_all()

    assert results["surveys"]["closed_removed"] == 1
    assert removed.is_active is False
    assert removed.is_soft_deleted is True


@pytest.mark.asyncio
async def test_close_removed_categories_soft_deletes_non_survey_non_tournament():
    removed_regular = Category(
        name="Legacy Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={},
    )
    active_regular = Category(
        name="Kept Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={},
    )
    survey_category = Category(
        name="Survey Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "survey_v1"},
    )
    tournament_category = Category(
        name="Tournament Category",
        comparison_mode="tournament_tiers",
        is_active=True,
        is_soft_deleted=False,
        settings={},
    )

    session = _FakeSession(
        [removed_regular, active_regular, survey_category, tournament_category]
    )
    service = CategorySyncService(session)

    closed_count = await service._close_removed_categories({"Kept Category"})

    assert closed_count == 1
    assert removed_regular.is_active is False
    assert removed_regular.is_soft_deleted is True
    assert active_regular.is_soft_deleted is False
    assert survey_category.is_soft_deleted is False
    assert tournament_category.is_soft_deleted is False


@pytest.mark.asyncio
async def test_sync_all_soft_deletes_removed_category_files_when_dir_missing(tmp_path):
    removed_regular = Category(
        name="Legacy Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={},
    )
    survey_category = Category(
        name="Survey Category",
        comparison_mode="single_choice",
        is_active=True,
        is_soft_deleted=False,
        settings={"survey_key": "survey_v1"},
    )
    session = _FakeSession([removed_regular, survey_category])
    service = CategorySyncService(session, data_dir=str(tmp_path))

    async def _commit():
        return None

    session.commit = _commit  # type: ignore[attr-defined]

    results = await service.sync_all()

    assert results["categories"]["closed_removed"] == 1
    assert removed_regular.is_soft_deleted is True
    assert survey_category.is_soft_deleted is False
