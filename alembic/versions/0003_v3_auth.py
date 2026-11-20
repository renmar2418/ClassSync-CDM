"""Schema evolution for ClassSync V3:
- student_profile table for real database-backed authentication and roster management

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20 12:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. student_profile table
    op.create_table(
        'student_profile',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('student_id', sa.String(length=16), nullable=False),
        sa.Column('institutional_email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('section_code', sa.String(length=64), nullable=True),
        sa.Column('curriculum_version_id', sa.Uuid(as_uuid=True), nullable=True),
        sa.Column('year_level', sa.SmallInteger(), server_default='1', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('requires_password_change', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('year_level BETWEEN 1 AND 5', name='chk_student_year_level'),
        sa.CheckConstraint(
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 1) BETWEEN '2' AND '9' AND "
            "substr(student_id, 2, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 3, 1) = '-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'",
            name='chk_student_id_format'
        ),
        sa.ForeignKeyConstraint(['section_code'], ['section.section_code'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['curriculum_version_id'], ['curriculum_version.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id'),
        sa.UniqueConstraint('institutional_email')
    )
    op.create_index('idx_student_profile_id', 'student_profile', ['student_id'], unique=False)
    op.create_index('idx_student_profile_email', 'student_profile', ['institutional_email'], unique=False)
    op.create_index('idx_student_profile_section', 'student_profile', ['section_code'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_student_profile_section', table_name='student_profile')
    op.drop_index('idx_student_profile_email', table_name='student_profile')
    op.drop_index('idx_student_profile_id', table_name='student_profile')
    op.drop_table('student_profile')
