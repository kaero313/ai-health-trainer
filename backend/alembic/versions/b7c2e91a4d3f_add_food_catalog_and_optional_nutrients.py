"""add food catalog and optional diet nutrients

Revision ID: b7c2e91a4d3f
Revises: a3811b7dab02
Create Date: 2026-04-26 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7c2e91a4d3f"
down_revision: Union[str, Sequence[str], None] = "a3811b7dab02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FOOD_ROWS: list[dict[str, object]] = [
    {"name": "닭가슴살", "aliases": ["chicken breast", "닭가슴"], "category": "protein", "calories": 165.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "sugar_g": 0.0, "saturated_fat_g": 1.0, "unsaturated_fat_g": 2.0},
    {"name": "닭다리살", "aliases": ["chicken thigh"], "category": "protein", "calories": 209.0, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 10.9, "sugar_g": 0.0, "saturated_fat_g": 3.0, "unsaturated_fat_g": 6.8},
    {"name": "삶은 계란", "aliases": ["계란", "달걀", "egg"], "category": "protein", "calories": 155.0, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "sugar_g": 1.1, "saturated_fat_g": 3.3, "unsaturated_fat_g": 6.2},
    {"name": "쌀밥", "aliases": ["흰쌀밥", "밥", "white rice"], "category": "carb", "calories": 130.0, "protein_g": 2.7, "carbs_g": 28.0, "fat_g": 0.3, "sugar_g": 0.1, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.2},
    {"name": "현미밥", "aliases": ["brown rice"], "category": "carb", "calories": 112.0, "protein_g": 2.6, "carbs_g": 23.0, "fat_g": 0.9, "sugar_g": 0.4, "saturated_fat_g": 0.2, "unsaturated_fat_g": 0.6},
    {"name": "잡곡밥", "aliases": ["mixed grain rice"], "category": "carb", "calories": 125.0, "protein_g": 3.0, "carbs_g": 26.0, "fat_g": 0.8, "sugar_g": 0.4, "saturated_fat_g": 0.2, "unsaturated_fat_g": 0.5},
    {"name": "고구마", "aliases": ["sweet potato"], "category": "carb", "calories": 86.0, "protein_g": 1.6, "carbs_g": 20.1, "fat_g": 0.1, "sugar_g": 4.2, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.1},
    {"name": "감자", "aliases": ["potato"], "category": "carb", "calories": 77.0, "protein_g": 2.0, "carbs_g": 17.0, "fat_g": 0.1, "sugar_g": 0.8, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.1},
    {"name": "오트밀", "aliases": ["귀리", "oatmeal"], "category": "carb", "calories": 389.0, "protein_g": 16.9, "carbs_g": 66.3, "fat_g": 6.9, "sugar_g": 0.9, "saturated_fat_g": 1.2, "unsaturated_fat_g": 5.0},
    {"name": "통밀빵", "aliases": ["whole wheat bread"], "category": "carb", "calories": 247.0, "protein_g": 13.0, "carbs_g": 41.0, "fat_g": 4.2, "sugar_g": 6.0, "saturated_fat_g": 0.9, "unsaturated_fat_g": 2.7},
    {"name": "바나나", "aliases": ["banana"], "category": "fruit", "calories": 89.0, "protein_g": 1.1, "carbs_g": 22.8, "fat_g": 0.3, "sugar_g": 12.2, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.1},
    {"name": "사과", "aliases": ["apple"], "category": "fruit", "calories": 52.0, "protein_g": 0.3, "carbs_g": 13.8, "fat_g": 0.2, "sugar_g": 10.4, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.1},
    {"name": "블루베리", "aliases": ["blueberry"], "category": "fruit", "calories": 57.0, "protein_g": 0.7, "carbs_g": 14.5, "fat_g": 0.3, "sugar_g": 10.0, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.2},
    {"name": "그릭요거트", "aliases": ["greek yogurt", "요거트"], "category": "dairy", "calories": 97.0, "protein_g": 9.0, "carbs_g": 3.6, "fat_g": 5.0, "sugar_g": 3.2, "saturated_fat_g": 3.0, "unsaturated_fat_g": 1.7},
    {"name": "저지방 우유", "aliases": ["우유", "milk"], "category": "dairy", "calories": 42.0, "protein_g": 3.4, "carbs_g": 5.0, "fat_g": 1.0, "sugar_g": 5.0, "saturated_fat_g": 0.6, "unsaturated_fat_g": 0.3},
    {"name": "두부", "aliases": ["tofu"], "category": "protein", "calories": 76.0, "protein_g": 8.1, "carbs_g": 1.9, "fat_g": 4.8, "sugar_g": 0.6, "saturated_fat_g": 0.7, "unsaturated_fat_g": 3.6},
    {"name": "연어", "aliases": ["salmon"], "category": "protein", "calories": 208.0, "protein_g": 20.0, "carbs_g": 0.0, "fat_g": 13.0, "sugar_g": 0.0, "saturated_fat_g": 3.1, "unsaturated_fat_g": 8.9},
    {"name": "대구살", "aliases": ["cod"], "category": "protein", "calories": 82.0, "protein_g": 18.0, "carbs_g": 0.0, "fat_g": 0.7, "sugar_g": 0.0, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.4},
    {"name": "참치", "aliases": ["tuna"], "category": "protein", "calories": 132.0, "protein_g": 28.0, "carbs_g": 0.0, "fat_g": 1.3, "sugar_g": 0.0, "saturated_fat_g": 0.3, "unsaturated_fat_g": 0.7},
    {"name": "소고기 등심", "aliases": ["beef sirloin", "소고기"], "category": "protein", "calories": 217.0, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 12.0, "sugar_g": 0.0, "saturated_fat_g": 4.8, "unsaturated_fat_g": 6.0},
    {"name": "돼지안심", "aliases": ["pork tenderloin"], "category": "protein", "calories": 143.0, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 3.5, "sugar_g": 0.0, "saturated_fat_g": 1.2, "unsaturated_fat_g": 1.8},
    {"name": "김치", "aliases": ["kimchi"], "category": "side", "calories": 15.0, "protein_g": 1.1, "carbs_g": 2.4, "fat_g": 0.5, "sugar_g": 1.1, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.2},
    {"name": "미역국", "aliases": ["seaweed soup"], "category": "soup", "calories": 35.0, "protein_g": 2.0, "carbs_g": 3.5, "fat_g": 1.5, "sugar_g": 0.5, "saturated_fat_g": 0.4, "unsaturated_fat_g": 0.8},
    {"name": "된장국", "aliases": ["soybean paste soup"], "category": "soup", "calories": 45.0, "protein_g": 3.5, "carbs_g": 5.0, "fat_g": 1.6, "sugar_g": 1.0, "saturated_fat_g": 0.3, "unsaturated_fat_g": 1.0},
    {"name": "샐러드 채소", "aliases": ["salad greens", "샐러드"], "category": "vegetable", "calories": 20.0, "protein_g": 1.5, "carbs_g": 3.5, "fat_g": 0.2, "sugar_g": 1.8, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.1},
    {"name": "브로콜리", "aliases": ["broccoli"], "category": "vegetable", "calories": 34.0, "protein_g": 2.8, "carbs_g": 6.6, "fat_g": 0.4, "sugar_g": 1.7, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.2},
    {"name": "방울토마토", "aliases": ["cherry tomato", "토마토"], "category": "vegetable", "calories": 18.0, "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2, "sugar_g": 2.6, "saturated_fat_g": 0.0, "unsaturated_fat_g": 0.1},
    {"name": "아보카도", "aliases": ["avocado"], "category": "fat", "calories": 160.0, "protein_g": 2.0, "carbs_g": 8.5, "fat_g": 14.7, "sugar_g": 0.7, "saturated_fat_g": 2.1, "unsaturated_fat_g": 11.6},
    {"name": "아몬드", "aliases": ["almond"], "category": "fat", "calories": 579.0, "protein_g": 21.2, "carbs_g": 21.6, "fat_g": 49.9, "sugar_g": 4.4, "saturated_fat_g": 3.8, "unsaturated_fat_g": 44.0},
    {"name": "땅콩버터", "aliases": ["peanut butter"], "category": "fat", "calories": 588.0, "protein_g": 25.0, "carbs_g": 20.0, "fat_g": 50.0, "sugar_g": 9.0, "saturated_fat_g": 10.0, "unsaturated_fat_g": 36.0},
    {"name": "올리브오일", "aliases": ["olive oil"], "category": "fat", "calories": 884.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "sugar_g": 0.0, "saturated_fat_g": 14.0, "unsaturated_fat_g": 84.0},
    {"name": "프로틴 쉐이크", "aliases": ["protein shake", "단백질 쉐이크"], "category": "supplement", "calories": 120.0, "protein_g": 24.0, "carbs_g": 3.0, "fat_g": 1.5, "sugar_g": 1.5, "saturated_fat_g": 0.5, "unsaturated_fat_g": 0.8},
    {"name": "프로틴 바", "aliases": ["protein bar"], "category": "supplement", "calories": 350.0, "protein_g": 30.0, "carbs_g": 35.0, "fat_g": 10.0, "sugar_g": 8.0, "saturated_fat_g": 4.0, "unsaturated_fat_g": 5.0},
    {"name": "닭갈비", "aliases": ["dakgalbi"], "category": "meal", "calories": 165.0, "protein_g": 16.0, "carbs_g": 8.0, "fat_g": 8.0, "sugar_g": 3.0, "saturated_fat_g": 2.0, "unsaturated_fat_g": 5.0},
    {"name": "불고기", "aliases": ["bulgogi"], "category": "meal", "calories": 220.0, "protein_g": 18.0, "carbs_g": 10.0, "fat_g": 12.0, "sugar_g": 6.0, "saturated_fat_g": 4.5, "unsaturated_fat_g": 6.0},
    {"name": "제육볶음", "aliases": ["spicy pork"], "category": "meal", "calories": 250.0, "protein_g": 18.0, "carbs_g": 8.0, "fat_g": 16.0, "sugar_g": 4.5, "saturated_fat_g": 5.5, "unsaturated_fat_g": 8.0},
    {"name": "참치마요", "aliases": ["tuna mayo"], "category": "meal", "calories": 230.0, "protein_g": 12.0, "carbs_g": 18.0, "fat_g": 12.0, "sugar_g": 2.0, "saturated_fat_g": 2.0, "unsaturated_fat_g": 8.0},
    {"name": "카레", "aliases": ["curry"], "category": "meal", "calories": 110.0, "protein_g": 3.0, "carbs_g": 13.0, "fat_g": 5.0, "sugar_g": 3.0, "saturated_fat_g": 1.5, "unsaturated_fat_g": 2.5},
    {"name": "파스타면", "aliases": ["pasta"], "category": "carb", "calories": 158.0, "protein_g": 5.8, "carbs_g": 30.9, "fat_g": 0.9, "sugar_g": 0.6, "saturated_fat_g": 0.2, "unsaturated_fat_g": 0.5},
    {"name": "새우", "aliases": ["shrimp"], "category": "protein", "calories": 99.0, "protein_g": 24.0, "carbs_g": 0.2, "fat_g": 0.3, "sugar_g": 0.0, "saturated_fat_g": 0.1, "unsaturated_fat_g": 0.1},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "food_catalog_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("serving_basis_g", sa.Numeric(precision=6, scale=1), server_default=sa.text("100.0"), nullable=False),
        sa.Column("calories", sa.Numeric(precision=7, scale=1), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=6, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=6, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=6, scale=1), server_default=sa.text("0"), nullable=False),
        sa.Column("sugar_g", sa.Numeric(precision=6, scale=1), nullable=True),
        sa.Column("saturated_fat_g", sa.Numeric(precision=6, scale=1), nullable=True),
        sa.Column("unsaturated_fat_g", sa.Numeric(precision=6, scale=1), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_food_catalog_items")),
    )
    op.create_index("ix_food_catalog_items_active", "food_catalog_items", ["is_active"], unique=False)
    op.create_index("ix_food_catalog_items_name", "food_catalog_items", ["name"], unique=False)

    food_catalog_table = sa.table(
        "food_catalog_items",
        sa.column("name", sa.String),
        sa.column("aliases", postgresql.JSONB),
        sa.column("category", sa.String),
        sa.column("serving_basis_g", sa.Numeric),
        sa.column("calories", sa.Numeric),
        sa.column("protein_g", sa.Numeric),
        sa.column("carbs_g", sa.Numeric),
        sa.column("fat_g", sa.Numeric),
        sa.column("sugar_g", sa.Numeric),
        sa.column("saturated_fat_g", sa.Numeric),
        sa.column("unsaturated_fat_g", sa.Numeric),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        food_catalog_table,
        [dict(row, serving_basis_g=100.0, is_active=True) for row in FOOD_ROWS],
    )

    op.add_column("diet_log_items", sa.Column("food_catalog_item_id", sa.Integer(), nullable=True))
    op.add_column("diet_log_items", sa.Column("serving_grams", sa.Numeric(precision=6, scale=1), nullable=True))
    op.add_column("diet_log_items", sa.Column("sugar_g", sa.Numeric(precision=6, scale=1), nullable=True))
    op.add_column("diet_log_items", sa.Column("saturated_fat_g", sa.Numeric(precision=6, scale=1), nullable=True))
    op.add_column("diet_log_items", sa.Column("unsaturated_fat_g", sa.Numeric(precision=6, scale=1), nullable=True))
    op.create_foreign_key(
        op.f("fk_diet_log_items_food_catalog_item_id_food_catalog_items"),
        "diet_log_items",
        "food_catalog_items",
        ["food_catalog_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_diet_log_items_food_catalog_item_id", "diet_log_items", ["food_catalog_item_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_diet_log_items_food_catalog_item_id", table_name="diet_log_items")
    op.drop_constraint(
        op.f("fk_diet_log_items_food_catalog_item_id_food_catalog_items"),
        "diet_log_items",
        type_="foreignkey",
    )
    op.drop_column("diet_log_items", "unsaturated_fat_g")
    op.drop_column("diet_log_items", "saturated_fat_g")
    op.drop_column("diet_log_items", "sugar_g")
    op.drop_column("diet_log_items", "serving_grams")
    op.drop_column("diet_log_items", "food_catalog_item_id")
    op.drop_index("ix_food_catalog_items_name", table_name="food_catalog_items")
    op.drop_index("ix_food_catalog_items_active", table_name="food_catalog_items")
    op.drop_table("food_catalog_items")
