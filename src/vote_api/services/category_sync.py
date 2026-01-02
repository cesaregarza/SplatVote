"""Git-based category synchronization service."""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vote_api.models.database import Category, CategoryItem, Item, ItemGroup
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
            "categories": {"created": 0, "updated": 0},
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
        if categories_dir.exists():
            for yaml_file in categories_dir.glob("*.yaml"):
                try:
                    cat_result = await self._sync_category(yaml_file)
                    results["categories"]["created"] += cat_result.get("created", 0)
                    results["categories"]["updated"] += cat_result.get("updated", 0)
                except Exception as e:
                    results["errors"].append(f"{yaml_file.name}: {str(e)}")
                    logger.exception(f"Error syncing {yaml_file}")

        await self.session.commit()
        return results

    async def _sync_item_group(self, yaml_file: Path) -> dict[str, int]:
        """Sync a single item group from YAML file."""
        with open(yaml_file) as f:
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
        with open(yaml_file) as f:
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
                settings=data.get("settings", {}),
            )
            self.session.add(category)
            await self.session.flush()
            result["created"] = 1
        else:
            category.description = data.get("description")
            category.comparison_mode = mode
            category.is_active = data.get("is_active", True)
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
