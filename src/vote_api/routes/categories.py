"""Category listing and detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vote_api.connections import get_db_session
from vote_api.models.database import Category, CategoryItem, Item
from vote_api.models.schemas import CategoryListResponse, CategoryResponse, ItemResponse

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    active_only: bool = True,
    include_items: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> CategoryListResponse:
    """List all voting categories."""
    query = select(Category).where(Category.is_soft_deleted == False)
    if active_only:
        query = query.where(Category.is_active == True)
    if include_items:
        query = query.options(
            selectinload(Category.category_items)
            .selectinload(CategoryItem.item)
            .selectinload(Item.group)
        )
    query = query.order_by(Category.created_at.desc())

    result = await session.execute(query)
    categories = list(result.scalars().all())

    # Build response, optionally including category items.
    category_responses = [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            comparison_mode=cat.comparison_mode,
            is_active=cat.is_active,
            settings=cat.settings or {},
            items=(
                [
                    ItemResponse(
                        id=cat_item.item.id,
                        name=cat_item.item.name,
                        image_url=cat_item.item.image_url,
                        group_name=(
                            None
                            if (cat.settings or {}).get("survey_key")
                            else (
                                cat_item.item.group.name
                                if cat_item.item.group
                                else None
                            )
                        ),
                        metadata=cat_item.item.metadata_,
                    )
                    for cat_item in cat.category_items
                ]
                if include_items
                else []
            ),
        )
        for cat in categories
    ]

    return CategoryListResponse(categories=category_responses, total=len(categories))


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """Get a category with its items."""
    result = await session.execute(
        select(Category)
        .options(
            selectinload(Category.category_items)
            .selectinload(CategoryItem.item)
            .selectinload(Item.group)
        )
        .where(Category.id == category_id, Category.is_soft_deleted == False)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Build items list
    is_survey = bool((category.settings or {}).get("survey_key"))
    items = []
    for cat_item in category.category_items:
        item = cat_item.item
        items.append(
            ItemResponse(
                id=item.id,
                name=item.name,
                image_url=item.image_url,
                group_name=None if is_survey else (item.group.name if item.group else None),
                metadata=item.metadata_,
            )
        )

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        comparison_mode=category.comparison_mode,
        is_active=category.is_active,
        settings=category.settings or {},
        items=items,
    )


@router.get("/{category_id}/items", response_model=list[ItemResponse])
async def get_category_items(
    category_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> list[ItemResponse]:
    """Get items for a specific category."""
    category_result = await session.execute(
        select(Category).where(
            Category.id == category_id,
            Category.is_soft_deleted == False,
        )
    )
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    is_survey = bool((category.settings or {}).get("survey_key"))

    result = await session.execute(
        select(Item)
        .join(CategoryItem)
        .options(selectinload(Item.group))
        .where(CategoryItem.category_id == category_id)
    )
    items = list(result.scalars().all())

    return [
        ItemResponse(
            id=item.id,
            name=item.name,
            image_url=item.image_url,
            group_name=None if is_survey else (item.group.name if item.group else None),
            metadata=item.metadata_,
        )
        for item in items
    ]
