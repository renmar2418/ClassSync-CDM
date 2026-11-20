"""Initial schema for ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.

Revision ID: 0001
Revises: 
Create Date: 2026-11-19 07:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. academic_period
    op.create_table(
        'academic_period',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('academic_year', sa.String(length=16), nullable=False),
        sa.Column('semester', sa.SmallInteger(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('semester IN (1, 2, 3)', name='chk_academic_period_semester'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('academic_year', 'semester', name='uq_academic_period_year_sem')
    )

    # 2. room
    op.create_table(
        'room',
        sa.Column('room_code', sa.String(length=32), nullable=False),
        sa.Column('building_name', sa.String(length=64), nullable=False),
        sa.Column('floor_level', sa.SmallInteger(), nullable=False),
        sa.Column('room_type', sa.String(length=32), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('is_schedulable', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('has_aircon', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('has_projector', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('exclusive_program', sa.String(length=64), nullable=True),
        sa.CheckConstraint('capacity > 0', name='chk_room_capacity_positive'),
        sa.PrimaryKeyConstraint('room_code')
    )
    op.create_index('idx_room_schedulable', 'room', ['is_schedulable'], unique=False)
    op.create_index('idx_room_building_floor', 'room', ['building_name', 'floor_level'], unique=False)

    # 3. curriculum_subject
    op.create_table(
        'curriculum_subject',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('subject_code', sa.String(length=32), nullable=False),
        sa.Column('descriptive_title', sa.String(length=255), nullable=False),
        sa.Column('lecture_hours', sa.SmallInteger(), server_default=sa.text('3'), nullable=False),
        sa.Column('lab_hours', sa.SmallInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('units', sa.SmallInteger(), server_default=sa.text('3'), nullable=False),
        sa.Column('required_room_type', sa.String(length=32), nullable=False),
        sa.CheckConstraint('lecture_hours >= 0', name='chk_subj_lecture_non_neg'),
        sa.CheckConstraint('lab_hours >= 0', name='chk_subj_lab_non_neg'),
        sa.CheckConstraint('units > 0', name='chk_subj_units_positive'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subject_code')
    )

    # 4. faculty_profile
    op.create_table(
        'faculty_profile',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('institutional_email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('employment_tier', sa.String(length=32), server_default=sa.text("'FULL_TIME'"), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('requires_password_change', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('role', sa.String(length=32), server_default=sa.text("'FACULTY'"), nullable=False),
        sa.CheckConstraint("employment_tier = 'FULL_TIME'", name='chk_faculty_100_percent_full_time'),
        sa.CheckConstraint("role IN ('ADMIN', 'FACULTY')", name='chk_faculty_valid_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('institutional_email')
    )
    op.create_index('idx_faculty_email', 'faculty_profile', ['institutional_email'], unique=False)

    # 5. section
    op.create_table(
        'section',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('academic_period_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('section_code', sa.String(length=64), nullable=False),
        sa.Column('year_level', sa.SmallInteger(), nullable=False),
        sa.Column('enrolled_student_count', sa.Integer(), nullable=False),
        sa.CheckConstraint('year_level BETWEEN 1 AND 5', name='chk_section_year_level'),
        sa.CheckConstraint('enrolled_student_count > 0', name='chk_section_enrollment_positive'),
        sa.ForeignKeyConstraint(['academic_period_id'], ['academic_period.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('section_code')
    )
    op.create_index('idx_section_academic_period', 'section', ['academic_period_id'], unique=False)

    # 6. course_offering
    op.create_table(
        'course_offering',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('academic_period_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('subject_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('section_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('faculty_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['academic_period_id'], ['academic_period.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faculty_id'], ['faculty_profile.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['section_id'], ['section.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['curriculum_subject.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('academic_period_id', 'subject_id', 'section_id', name='uq_course_offering_period_subj_section')
    )
    op.create_index('idx_offering_faculty', 'course_offering', ['faculty_id'], unique=False)
    op.create_index('idx_offering_section', 'course_offering', ['section_id'], unique=False)

    # 7. timetable_entry
    op.create_table(
        'timetable_entry',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('offering_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('room_code', sa.String(length=32), nullable=False),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
        sa.Column('start_slot', sa.SmallInteger(), nullable=False),
        sa.Column('duration_slots', sa.SmallInteger(), nullable=False),
        sa.Column('cohort_mode', sa.String(length=32), server_default=sa.text("'UNIFIED'"), nullable=False),
        sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('revision_hash', sa.String(length=64), nullable=False),
        sa.CheckConstraint('day_of_week BETWEEN 0 AND 6', name='chk_timetable_day_range'),
        sa.CheckConstraint('start_slot BETWEEN 0 AND 23', name='chk_timetable_start_slot_range'),
        sa.CheckConstraint('duration_slots >= 1', name='chk_timetable_duration_min'),
        sa.CheckConstraint('start_slot + duration_slots <= 24', name='chk_timetable_slot_boundary'),
        sa.CheckConstraint("cohort_mode = 'UNIFIED'", name='chk_timetable_unified_cohort_only'),
        sa.ForeignKeyConstraint(['offering_id'], ['course_offering.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_code'], ['room.room_code'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_timetable_offering_day_slot', 'timetable_entry', ['offering_id', 'day_of_week', 'start_slot'], unique=False)
    op.create_index('idx_timetable_room_day_slot', 'timetable_entry', ['room_code', 'day_of_week', 'start_slot'], unique=False)

    # 8. workstation
    op.create_table(
        'workstation',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('room_code', sa.String(length=32), nullable=False),
        sa.Column('workstation_number', sa.Integer(), nullable=False),
        sa.Column('is_operational', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.CheckConstraint('workstation_number > 0', name='chk_workstation_number_positive'),
        sa.ForeignKeyConstraint(['room_code'], ['room.room_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_code', 'workstation_number', name='uq_room_workstation_number')
    )
    op.create_index('idx_workstation_room', 'workstation', ['room_code'], unique=False)

    # 9. presence_log
    op.create_table(
        'presence_log',
        sa.Column('id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('room_code', sa.String(length=32), nullable=False),
        sa.Column('workstation_number', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(length=16), nullable=False),
        sa.Column('session_id', sa.Uuid(as_uuid=True), nullable=False),
        sa.Column('check_in_time', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('check_out_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('totp_verified', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.CheckConstraint('workstation_number > 0', name='chk_presence_workstation_positive'),
        sa.CheckConstraint(
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 3) = '24-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'",
            name='chk_presence_student_id_format'
        ),
        sa.ForeignKeyConstraint(['room_code', 'workstation_number'], ['workstation.room_code', 'workstation.workstation_number'], name='fk_presence_workstation', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_code'], ['room.room_code'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_presence_session_room', 'presence_log', ['session_id', 'room_code'], unique=False)
    op.create_index('idx_presence_student_checkin', 'presence_log', ['student_id', 'check_in_time'], unique=False)


def downgrade() -> None:
    op.drop_table('presence_log')
    op.drop_table('workstation')
    op.drop_table('timetable_entry')
    op.drop_table('course_offering')
    op.drop_table('section')
    op.drop_table('faculty_profile')
    op.drop_table('curriculum_subject')
    op.drop_table('room')
    op.drop_table('academic_period')
