"""Schema evolution for ClassSync V2:
- curriculum_version table
- student_curriculum_override table
- section.curriculum_version_id foreign key
- presence_log multi-year student_id check constraint update

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20 09:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. curriculum_version table
    op.create_table(
        'curriculum_version',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('curriculum_year', sa.String(length=16), nullable=False),
        sa.Column('program_code', sa.String(length=32), nullable=False),
        sa.Column('institute', sa.String(length=16), nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('curriculum_year', 'program_code', name='uq_curriculum_year_program')
    )
    op.create_index('idx_curriculum_program', 'curriculum_version', ['program_code'], unique=False)

    # 2. student_curriculum_override table
    op.create_table(
        'student_curriculum_override',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('student_id', sa.String(length=16), nullable=False),
        sa.Column('curriculum_version_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('override_reason', sa.String(length=255), server_default=sa.text("'Irregular'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['curriculum_version_id'], ['curriculum_version.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('idx_override_student_id', 'student_curriculum_override', ['student_id'], unique=False)

    # 3. Add curriculum_version_id to section
    with op.batch_alter_table('section', schema=None) as batch_op:
        batch_op.add_column(sa.Column('curriculum_version_id', sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            'fk_section_curriculum_version',
            'curriculum_version',
            ['curriculum_version_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('idx_section_curriculum', ['curriculum_version_id'], unique=False)

    # 4. Update presence_log check constraint to allow 22-99 student ID prefixes
    with op.batch_alter_table('presence_log', schema=None) as batch_op:
        batch_op.drop_constraint('chk_presence_student_id_format', type_='check')
        batch_op.create_check_constraint(
            'chk_presence_student_id_format',
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 2, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 3, 1) = '-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'"
        )


def downgrade() -> None:
    with op.batch_alter_table('presence_log', schema=None) as batch_op:
        batch_op.drop_constraint('chk_presence_student_id_format', type_='check')
        batch_op.create_check_constraint(
            'chk_presence_student_id_format',
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 3) = '24-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'"
        )

    with op.batch_alter_table('section', schema=None) as batch_op:
        batch_op.drop_index('idx_section_curriculum')
        batch_op.drop_constraint('fk_section_curriculum_version', type_='foreignkey')
        batch_op.drop_column('curriculum_version_id')

    op.drop_table('student_curriculum_override')
    op.drop_table('curriculum_version')
