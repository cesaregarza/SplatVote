"""Git-based category synchronization service."""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vote_api.models.database import (
    Category,
    CategoryItem,
    Comment,
    EloRating,
    Item,
    ItemGroup,
    Vote,
    VoteChoice,
)
from vote_api.models.enums import ComparisonMode

logger = logging.getLogger(__name__)


class CategorySyncService:
    """Service for synchronizing categories and items from YAML files."""

    def __init__(
        self,
        session: AsyncSession,
        data_dir: str = "data",
    ):
        self.session = session
        self.data_dir = Path(data_dir)

    async def sync_all(self) -> dict[str, Any]:
        """
        Sync all categories and item groups from YAML files.

        Returns:
            Summary of sync operation with counts of created/updated items.
        """
        results = {
            "item_groups": {"created": 0, "updated": 0},
            "items": {"created": 0, "updated": 0},
            "categories": {"created": 0, "updated": 0, "closed_removed": 0},
            "surveys": {"created": 0, "updated": 0, "closed": 0, "closed_removed": 0},
            "tournament_polls": {"created": 0, "updated": 0, "deleted": 0, "closed": 0},
            "errors": [],
        }

        # Sync item groups first (they're referenced by categories)
        groups_dir = self.data_dir / "item_groups"
        if groups_dir.exists():
            for yaml_file in groups_dir.glob("*.yaml"):
                try:
                    group_result = await self._sync_item_group(yaml_file)
                    results["item_groups"]["created"] += group_result.get("created", 0)
                    results["item_groups"]["updated"] += group_result.get("updated", 0)
                    results["items"]["created"] += group_result.get("items_created", 0)
                    results["items"]["updated"] += group_result.get("items_updated", 0)
                except Exception as e:
                    results["errors"].append(f"{yaml_file.name}: {str(e)}")
                    logger.exception(f"Error syncing {yaml_file}")

        # Sync categories
        categories_dir = self.data_dir / "categories"
        category_sync_had_errors = False
        active_category_names_on_disk: set[str] = set()
        if categories_dir.exists():
            for yaml_file in categories_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, encoding="utf-8") as f:
                        raw_data = yaml.safe_load(f) or {}
                    category_name = raw_data.get("name")
                    if isinstance(category_name, str) and category_name.strip():
                        active_category_names_on_disk.add(category_name.strip())

                    cat_result = await self._sync_category(yaml_file)
                    results["categories"]["created"] += cat_result.get("created", 0)
                    results["categories"]["updated"] += cat_result.get("updated", 0)
                except Exception as e:
                    category_sync_had_errors = True
                    results["errors"].append(f"{yaml_file.name}: {str(e)}")
                    logger.exception(f"Error syncing {yaml_file}")

        # Soft-delete categories removed from data/categories/*.yaml.
        # Excludes survey-backed and tournament-tier categories which are
        # reconciled by dedicated sync flows.
        if not category_sync_had_errors:
            closed_removed_categories = await self._close_removed_categories(
                active_category_names_on_disk
            )
            results["categories"]["closed_removed"] = closed_removed_categories

        # Sync surveys (single-file survey definitions expanded into categories)
        # Always run reconciliation, even if surveys directory is missing.
        surveys_dir = self.data_dir / "surveys"
        survey_sync_had_errors = False
        survey_keys_on_disk: set[str] = set()
        survey_files = sorted(surveys_dir.glob("*.yaml")) if surveys_dir.exists() else []

        for yaml_file in survey_files:
            try:
                survey_result = await self._sync_survey(yaml_file)
                results["surveys"]["created"] += survey_result.get("created", 0)
                results["surveys"]["updated"] += survey_result.get("updated", 0)
                results["surveys"]["closed"] += survey_result.get("closed", 0)
                survey_key = survey_result.get("survey_key")
                if isinstance(survey_key, str) and survey_key.strip():
                    survey_keys_on_disk.add(survey_key.strip())
            except Exception as e:
                survey_sync_had_errors = True
                results["errors"].append(f"{yaml_file.name}: {str(e)}")
                logger.exception(f"Error syncing survey file {yaml_file}")

        # Soft-delete categories that belong to survey keys no longer present
        # in repo.
        # Skip this reconciliation if any survey file failed to parse/sync so we do
        # not accidentally soft-delete active surveys due to a transient bad file.
        if not survey_sync_had_errors:
            closed_removed = await self._close_removed_surveys(survey_keys_on_disk)
            results["surveys"]["closed_removed"] += closed_removed

        # Sync tournament polls
        tournament_polls_file = self.data_dir / "tournament_polls.yaml"
        if tournament_polls_file.exists():
            try:
                poll_result = await self._sync_tournament_polls(tournament_polls_file)
                results["tournament_polls"]["created"] = poll_result.get("created", 0)
                results["tournament_polls"]["updated"] = poll_result.get("updated", 0)
                results["tournament_polls"]["deleted"] = poll_result.get("deleted", 0)
                results["tournament_polls"]["closed"] = poll_result.get("closed", 0)
            except Exception as e:
                results["errors"].append(f"tournament_polls.yaml: {str(e)}")
                logger.exception("Error syncing tournament polls")

        await self.session.commit()
        return results

    async def _close_removed_categories(self, active_category_names: set[str]) -> int:
        """Soft-delete non-survey, non-tournament categories removed from repo."""
        result = await self.session.execute(select(Category))
        categories = result.scalars().all()

        closed_count = 0
        for category in categories:
            if category.name in active_category_names:
                continue
            if category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value:
                continue

            settings = category.settings or {}
            if settings.get("survey_key"):
                continue

            if not category.is_soft_deleted:
                category.is_active = False
                category.is_soft_deleted = True
                closed_count += 1

        if closed_count:
            await self.session.flush()

        return closed_count

    async def _sync_item_group(self, yaml_file: Path) -> dict[str, int]:
        """Sync a single item group from YAML file."""
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        result = {"created": 0, "updated": 0, "items_created": 0, "items_updated": 0}

        # Find or create item group
        group_name = data["name"]
        existing = await self.session.execute(
            select(ItemGroup).where(ItemGroup.name == group_name)
        )
        group = existing.scalar_one_or_none()

        if group is None:
            group = ItemGroup(
                name=group_name,
                description=data.get("description"),
                icon_url=data.get("icon_url"),
            )
            self.session.add(group)
            await self.session.flush()
            result["created"] = 1
        else:
            group.description = data.get("description")
            group.icon_url = data.get("icon_url")
            result["updated"] = 1

        # Sync items in this group
        for item_data in data.get("items", []):
            item_name = item_data["name"]
            existing_item = await self.session.execute(
                select(Item).where(Item.name == item_name, Item.group_id == group.id)
            )
            item = existing_item.scalar_one_or_none()

            if item is None:
                item = Item(
                    group_id=group.id,
                    name=item_name,
                    image_url=item_data.get("image_url"),
                    metadata_=item_data.get("metadata", {}),
                )
                self.session.add(item)
                result["items_created"] += 1
            else:
                item.image_url = item_data.get("image_url")
                item.metadata_ = item_data.get("metadata", {})
                result["items_updated"] += 1

        await self.session.flush()
        return result

    async def _sync_category(self, yaml_file: Path) -> dict[str, int]:
        """Sync a single category from YAML file."""
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        result = {"created": 0, "updated": 0}

        # Validate comparison mode
        mode = data.get("comparison_mode", "single_choice")
        if mode not in [m.value for m in ComparisonMode]:
            raise ValueError(f"Invalid comparison_mode: {mode}")

        # Find or create category
        cat_name = data["name"]
        existing = await self.session.execute(
            select(Category).where(Category.name == cat_name)
        )
        category = existing.scalar_one_or_none()

        if category is None:
            category = Category(
                name=cat_name,
                description=data.get("description"),
                comparison_mode=mode,
                is_active=data.get("is_active", True),
                is_soft_deleted=False,
                settings=data.get("settings", {}),
            )
            self.session.add(category)
            await self.session.flush()
            result["created"] = 1
        else:
            category.description = data.get("description")
            category.comparison_mode = mode
            category.is_active = data.get("is_active", True)
            category.is_soft_deleted = False
            category.settings = data.get("settings", {})
            result["updated"] = 1

        # Link items to category
        await self._sync_category_items(category, data)

        return result

    async def _sync_category_items(
        self,
        category: Category,
        data: dict[str, Any],
    ) -> None:
        """Sync items linked to a category."""
        # Get items based on item_group reference or explicit items list
        item_ids: list[int] = []

        if "item_group" in data:
            # Find all items in the referenced group
            group_name = data["item_group"]
            group_result = await self.session.execute(
                select(ItemGroup).where(ItemGroup.name == group_name)
            )
            group = group_result.scalar_one_or_none()

            if group:
                # Apply filter if specified
                filter_config = data.get("filter", {})
                items = await self._get_filtered_items(group.id, filter_config)
                item_ids = [item.id for item in items]

        elif "items" in data:
            # Explicit item names
            for item_name in data["items"]:
                item_result = await self.session.execute(
                    select(Item).where(Item.name == item_name)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    item_ids.append(item.id)

        # Clear existing category items and add new ones
        await self.session.execute(
            CategoryItem.__table__.delete().where(
                CategoryItem.category_id == category.id
            )
        )
        await self.session.flush()

        for item_id in item_ids:
            cat_item = CategoryItem(category_id=category.id, item_id=item_id)
            self.session.add(cat_item)

        await self.session.flush()

    async def _get_filtered_items(
        self,
        group_id: int,
        filter_config: dict[str, Any],
    ) -> list[Item]:
        """Get items from a group with optional filtering."""
        query = select(Item).where(Item.group_id == group_id)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        # Apply metadata filters
        metadata_filters = filter_config.get("metadata", {})
        if metadata_filters:
            filtered = []
            for item in items:
                matches = True
                for key, allowed_values in metadata_filters.items():
                    item_value = item.metadata_.get(key)
                    if isinstance(allowed_values, list):
                        if item_value not in allowed_values:
                            matches = False
                            break
                    elif item_value != allowed_values:
                        matches = False
                        break
                if matches:
                    filtered.append(item)
            return filtered

        return items

    async def _sync_survey(self, yaml_file: Path) -> dict[str, int]:
        """Sync a survey definition from a single YAML file.

        Each survey question is expanded into one category plus one generated item group.
        """
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        survey_config = data.get("survey", {})
        survey_key = str(survey_config.get("key", yaml_file.stem)).strip() or yaml_file.stem
        questions = data.get("questions", [])
        if not questions:
            return {"created": 0, "updated": 0, "closed": 0, "survey_key": survey_key}

        survey_label = survey_config.get("label", survey_key)
        default_is_active = bool(survey_config.get("is_active", True))
        default_discord_required = bool(survey_config.get("discord_required", False))
        default_discord_reason = survey_config.get("discord_reason")
        default_shuffle = bool(survey_config.get("shuffle", False))
        default_private_results = bool(survey_config.get("private_results", False))
        deactivate_missing = bool(survey_config.get("deactivate_missing", True))
        default_page = survey_config.get("default_page", 1)

        page_titles: dict[str, str] = {}
        page_orders: dict[str, int] = {}
        raw_pages = survey_config.get("pages", [])
        if isinstance(raw_pages, list):
            for page_index, raw_page in enumerate(raw_pages):
                if not isinstance(raw_page, dict):
                    continue
                raw_key = (
                    raw_page.get("key")
                    or raw_page.get("id")
                    or raw_page.get("page")
                )
                if raw_key is None:
                    continue
                page_key = str(raw_key).strip()
                if not page_key:
                    continue
                page_orders[page_key] = page_index + 1
                raw_order = raw_page.get("order")
                if isinstance(raw_order, int) and not isinstance(raw_order, bool):
                    page_orders[page_key] = raw_order
                elif (
                    isinstance(raw_order, float)
                    and not isinstance(raw_order, bool)
                    and raw_order.is_integer()
                ):
                    page_orders[page_key] = int(raw_order)
                raw_title = raw_page.get("title")
                if isinstance(raw_title, str) and raw_title.strip():
                    page_titles[page_key] = raw_title.strip()

        result = {"created": 0, "updated": 0, "closed": 0, "survey_key": survey_key}
        synced_category_names: set[str] = set()

        total_questions = len(questions)
        for question_index, question in enumerate(questions):
            question_id = str(question.get("id", "")).strip()
            question_name = str(question.get("name", "")).strip()
            question_description = question.get("description")
            mode = question.get("comparison_mode", "single_choice")
            options = question.get("options", [])

            if not question_id:
                raise ValueError(f"Survey question missing id in {yaml_file.name}")
            if not question_name:
                raise ValueError(f"Survey question {question_id} missing name in {yaml_file.name}")
            if mode not in [m.value for m in ComparisonMode]:
                raise ValueError(f"Invalid comparison_mode for {question_id}: {mode}")
            if not isinstance(options, list) or len(options) == 0:
                raise ValueError(f"Survey question {question_id} must include at least one option")

            group_name = f"{survey_label} :: {question_id} options"
            group_description = question.get("group_description", question_name)

            existing_group = await self.session.execute(
                select(ItemGroup).where(ItemGroup.name == group_name)
            )
            group = existing_group.scalar_one_or_none()
            if group is None:
                group = ItemGroup(name=group_name, description=group_description)
                self.session.add(group)
                await self.session.flush()
            else:
                group.description = group_description

            item_ids: list[int] = []
            for option in options:
                if isinstance(option, str):
                    option_name = option
                    option_image_url = None
                    option_metadata: dict[str, Any] = {}
                elif isinstance(option, dict):
                    option_name = str(option.get("name", "")).strip()
                    option_image_url = option.get("image_url")
                    option_metadata = option.get("metadata", {})
                else:
                    raise ValueError(
                        f"Invalid option type for {question_id}: {type(option).__name__}"
                    )

                if not option_name:
                    raise ValueError(f"Survey question {question_id} has option with empty name")

                existing_item = await self.session.execute(
                    select(Item).where(Item.name == option_name, Item.group_id == group.id)
                )
                item = existing_item.scalar_one_or_none()
                if item is None:
                    item = Item(
                        group_id=group.id,
                        name=option_name,
                        image_url=option_image_url,
                        metadata_=option_metadata,
                    )
                    self.session.add(item)
                    await self.session.flush()
                else:
                    item.image_url = option_image_url
                    item.metadata_ = option_metadata

                item_ids.append(item.id)

            question_discord_required = bool(
                question.get("discord_required", default_discord_required)
            )
            question_discord_reason = question.get("discord_reason", default_discord_reason)
            question_shuffle = bool(question.get("shuffle", default_shuffle))
            question_private_results = bool(
                question.get("private_results", default_private_results)
            )

            raw_page = question.get("page", default_page)
            if isinstance(raw_page, bool):
                page_key = "1"
            elif isinstance(raw_page, int):
                page_key = str(raw_page)
            elif isinstance(raw_page, float) and raw_page.is_integer():
                page_key = str(int(raw_page))
            elif isinstance(raw_page, str) and raw_page.strip():
                page_key = raw_page.strip()
            else:
                page_key = "1"

            settings: dict[str, Any] = {
                "survey_key": survey_key,
                "survey_label": survey_label,
                "survey_total_questions": total_questions,
                "survey_question_id": question_id,
                "survey_question_order": question_index,
                "survey_page": page_key,
                "discord_required": question_discord_required,
                "shuffle": question_shuffle,
                "private_results": question_private_results,
            }

            page_order = page_orders.get(page_key)
            if page_order is None:
                page_order = question_index + 1
                if page_key.isdigit():
                    page_order = int(page_key)
            settings["survey_page_order"] = page_order

            if isinstance(question_discord_reason, str):
                cleaned_reason = question_discord_reason.strip()
                if cleaned_reason:
                    settings["discord_reason"] = cleaned_reason

            max_choices = question.get("max_choices")
            if isinstance(max_choices, int) and max_choices > 0:
                settings["max_choices"] = max_choices

            section = question.get("section")
            if isinstance(section, str) and section.strip():
                section_title = section.strip()
                settings["section"] = section_title
                settings["survey_section"] = section_title

            page_title = question.get("page_title")
            if isinstance(page_title, str) and page_title.strip():
                settings["survey_page_title"] = page_title.strip()
            elif page_key in page_titles:
                settings["survey_page_title"] = page_titles[page_key]

            is_active = bool(question.get("is_active", default_is_active))

            existing_category = await self.session.execute(
                select(Category).where(Category.name == question_name)
            )
            category = existing_category.scalar_one_or_none()
            if category is None:
                category = Category(
                    name=question_name,
                    description=question_description,
                    comparison_mode=mode,
                    is_active=is_active,
                    is_soft_deleted=False,
                    settings=settings,
                )
                self.session.add(category)
                await self.session.flush()
                result["created"] += 1
            else:
                category.description = question_description
                category.comparison_mode = mode
                category.is_active = is_active
                category.is_soft_deleted = False
                category.settings = settings
                result["updated"] += 1

            await self.session.execute(
                CategoryItem.__table__.delete().where(
                    CategoryItem.category_id == category.id
                )
            )
            await self.session.flush()

            for item_id in item_ids:
                self.session.add(CategoryItem(category_id=category.id, item_id=item_id))

            await self.session.flush()
            synced_category_names.add(question_name)

        if deactivate_missing:
            existing_categories_result = await self.session.execute(select(Category))
            for existing_category in existing_categories_result.scalars().all():
                settings = existing_category.settings or {}
                if settings.get("survey_key") != survey_key:
                    continue
                if existing_category.name in synced_category_names:
                    continue
                if not existing_category.is_soft_deleted:
                    existing_category.is_active = False
                    existing_category.is_soft_deleted = True
                    result["closed"] += 1

        return result

    async def _close_removed_surveys(self, active_survey_keys: set[str]) -> int:
        """Soft-delete categories for surveys that are no longer in the repo."""
        result = await self.session.execute(select(Category))
        categories = result.scalars().all()

        closed_count = 0
        for category in categories:
            settings = category.settings or {}
            survey_key = settings.get("survey_key")
            if not isinstance(survey_key, str) or not survey_key.strip():
                continue
            if survey_key in active_survey_keys:
                continue
            if not category.is_soft_deleted:
                category.is_active = False
                category.is_soft_deleted = True
                closed_count += 1

        if closed_count:
            await self.session.flush()

        return closed_count

    async def _sync_tournament_polls(self, yaml_file: Path) -> dict[str, int]:
        """Sync tournament tier poll from tournament_polls.yaml.

        Creates a single category with all tournaments as items.
        Uses tournament_tiers comparison mode for multi-item tier voting.
        """
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        result = {"created": 0, "updated": 0, "deleted": 0, "closed": 0}

        # Clean up old individual tournament poll categories
        old_polls = await self.session.execute(
            select(Category).where(Category.name.like("Tournament tier:%"))
        )
        for old_cat in old_polls.scalars().all():
            # Delete related records first (foreign key constraints)
            # Delete vote choices and comments for votes in this category
            votes_result = await self.session.execute(
                select(Vote).where(Vote.category_id == old_cat.id)
            )
            for vote in votes_result.scalars().all():
                await self.session.execute(
                    VoteChoice.__table__.delete().where(VoteChoice.vote_id == vote.id)
                )
                await self.session.execute(
                    Comment.__table__.delete().where(Comment.vote_id == vote.id)
                )

            # Delete votes, category items, and elo ratings
            await self.session.execute(
                Vote.__table__.delete().where(Vote.category_id == old_cat.id)
            )
            await self.session.execute(
                CategoryItem.__table__.delete().where(CategoryItem.category_id == old_cat.id)
            )
            await self.session.execute(
                EloRating.__table__.delete().where(EloRating.category_id == old_cat.id)
            )

            await self.session.delete(old_cat)
            result["deleted"] += 1
        await self.session.flush()

        poll_config = data.get("poll", {})
        tournaments = data.get("tournaments", [])
        if not tournaments:
            return result

        # Create or get the Tournament Polls item group
        group_result = await self.session.execute(
            select(ItemGroup).where(ItemGroup.name == "Tournament Polls")
        )
        group = group_result.scalar_one_or_none()

        if group is None:
            group = ItemGroup(
                name="Tournament Polls",
                description="Tournaments for tier calibration voting",
            )
            self.session.add(group)
            await self.session.flush()

        # Create/update items for each tournament
        tournament_item_ids = []
        for tournament in tournaments:
            tournament_id = tournament.get("id")
            item_name = f"tournament:{tournament_id}"

            item_result = await self.session.execute(
                select(Item).where(Item.name == item_name, Item.group_id == group.id)
            )
            item = item_result.scalar_one_or_none()

            # Store tournament data in item metadata
            item_metadata = {
                "tournament_id": tournament_id,
                "display_name": tournament.get("name"),
                "current_tier": tournament.get("tier"),
                "url": tournament.get("url"),
                "winners": tournament.get("winners", []),
            }

            if item is None:
                item = Item(
                    group_id=group.id,
                    name=item_name,
                    metadata_=item_metadata,
                )
                self.session.add(item)
                await self.session.flush()
            else:
                item.metadata_ = item_metadata

            tournament_item_ids.append(item.id)

        # Build category settings
        settings = {
            "tier_options": poll_config.get("tier_options", ["X", "S+", "S", "A", "B", "C", "D"]),
            "pages": poll_config.get("pages", 3),
            "private_results": poll_config.get("private_results", False),
            "discord_required": poll_config.get("discord_required", False),
            "shuffle": poll_config.get("shuffle", True),
        }
        discord_reason = poll_config.get("discord_reason")
        if isinstance(discord_reason, str):
            discord_reason = discord_reason.strip()
        if discord_reason:
            settings["discord_reason"] = discord_reason

        cat_name = poll_config.get("name", "Tournament Tier Calibration")
        is_active = bool(poll_config.get("is_active", True))
        close_previous = bool(poll_config.get("close_previous", False))

        # Optionally close previously active tournament tier polls.
        if close_previous:
            existing_polls = await self.session.execute(
                select(Category).where(
                    Category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value,
                    Category.name != cat_name,
                )
            )
            for existing_poll in existing_polls.scalars().all():
                if existing_poll.is_active:
                    existing_poll.is_active = False
                    result["closed"] += 1

        # Find or create the single category
        existing = await self.session.execute(
            select(Category).where(Category.name == cat_name)
        )
        category = existing.scalar_one_or_none()

        if category is None:
            category = Category(
                name=cat_name,
                description=poll_config.get("description"),
                comparison_mode="tournament_tiers",
                is_active=is_active,
                is_soft_deleted=False,
                settings=settings,
            )
            self.session.add(category)
            await self.session.flush()
            result["created"] = 1
        else:
            category.description = poll_config.get("description")
            category.comparison_mode = "tournament_tiers"
            category.is_active = is_active
            category.is_soft_deleted = False
            category.settings = settings
            result["updated"] = 1

        # Clear existing category items and link tournament items
        await self.session.execute(
            CategoryItem.__table__.delete().where(
                CategoryItem.category_id == category.id
            )
        )
        await self.session.flush()

        for item_id in tournament_item_ids:
            cat_item = CategoryItem(category_id=category.id, item_id=item_id)
            self.session.add(cat_item)

        await self.session.flush()
        return result
