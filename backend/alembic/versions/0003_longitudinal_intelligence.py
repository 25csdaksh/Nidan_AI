"""Add Longitudinal Intelligence tables

Revision ID: 0003_longitudinal_intelligence
Revises: 0002_clinical_intelligence
Create Date: 2026-10-04 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_longitudinal_intelligence'
down_revision = '0002_clinical_intelligence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. clinical_observations table
    op.create_table(
        'clinical_observations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('extraction_id', sa.String(length=36), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=True),
        sa.Column('analyte', sa.String(length=255), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('normalized_value', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('observation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observation_date_source', sa.String(length=50), nullable=False),
        sa.Column('date_confidence', sa.String(length=20), nullable=False),
        sa.Column('document_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('technical_status', sa.String(length=50), nullable=False),
        sa.Column('reference_min', sa.Float(), nullable=True),
        sa.Column('reference_max', sa.Float(), nullable=True),
        sa.Column('reference_source', sa.String(length=50), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=False),
        sa.Column('finding_confidence', sa.Float(), nullable=False),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('is_doctor_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['medical_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['document_extraction_entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['extraction_id'], ['document_extractions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clinical_observations_analyte'), 'clinical_observations', ['analyte'], unique=False)
    op.create_index(op.f('ix_clinical_observations_canonical_name'), 'clinical_observations', ['canonical_name'], unique=False)
    op.create_index(op.f('ix_clinical_observations_document_id'), 'clinical_observations', ['document_id'], unique=False)
    op.create_index(op.f('ix_clinical_observations_entity_id'), 'clinical_observations', ['entity_id'], unique=False)
    op.create_index(op.f('ix_clinical_observations_extraction_id'), 'clinical_observations', ['extraction_id'], unique=False)
    op.create_index(op.f('ix_clinical_observations_is_doctor_verified'), 'clinical_observations', ['is_doctor_verified'], unique=False)
    op.create_index(op.f('ix_clinical_observations_normalized_value'), 'clinical_observations', ['normalized_value'], unique=False)
    op.create_index(op.f('ix_clinical_observations_observation_date'), 'clinical_observations', ['observation_date'], unique=False)
    op.create_index(op.f('ix_clinical_observations_patient_id'), 'clinical_observations', ['patient_id'], unique=False)
    op.create_index(op.f('ix_clinical_observations_technical_status'), 'clinical_observations', ['technical_status'], unique=False)

    # 2. longitudinal_analyses table
    op.create_table(
        'longitudinal_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_version', sa.Integer(), nullable=False),
        sa.Column('trend_rule_version', sa.String(length=50), nullable=False),
        sa.Column('summary_version', sa.String(length=50), nullable=False),
        sa.Column('observation_count', sa.Integer(), nullable=False),
        sa.Column('visit_count', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_longitudinal_analyses_patient_id'), 'longitudinal_analyses', ['patient_id'], unique=False)

    # 3. longitudinal_trends table
    op.create_table(
        'longitudinal_trends',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('analyte', sa.String(length=255), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('direction', sa.String(length=50), nullable=False),
        sa.Column('trend_status', sa.String(length=50), nullable=False),
        sa.Column('dynamics_classification', sa.String(length=50), nullable=False),
        sa.Column('observation_count', sa.Integer(), nullable=False),
        sa.Column('first_value', sa.Float(), nullable=True),
        sa.Column('last_value', sa.Float(), nullable=True),
        sa.Column('first_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('absolute_change', sa.Float(), nullable=True),
        sa.Column('percentage_change', sa.Float(), nullable=True),
        sa.Column('persistence_count', sa.Integer(), nullable=False),
        sa.Column('history_points', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['longitudinal_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_longitudinal_trends_analysis_id'), 'longitudinal_trends', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_analyte'), 'longitudinal_trends', ['analyte'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_canonical_name'), 'longitudinal_trends', ['canonical_name'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_direction'), 'longitudinal_trends', ['direction'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_dynamics_classification'), 'longitudinal_trends', ['dynamics_classification'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_patient_id'), 'longitudinal_trends', ['patient_id'], unique=False)
    op.create_index(op.f('ix_longitudinal_trends_trend_status'), 'longitudinal_trends', ['trend_status'], unique=False)

    # 4. longitudinal_summary_sections table
    op.create_table(
        'longitudinal_summary_sections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('section_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('generated_text', sa.Text(), nullable=False),
        sa.Column('evidence_ids', sa.JSON(), nullable=False),
        sa.Column('source_documents', sa.JSON(), nullable=False),
        sa.Column('source_entities', sa.JSON(), nullable=False),
        sa.Column('generated_by', sa.String(length=50), nullable=False),
        sa.Column('generation_version', sa.String(length=50), nullable=False),
        sa.Column('safety_validation_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['longitudinal_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_longitudinal_summary_sections_analysis_id'), 'longitudinal_summary_sections', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_longitudinal_summary_sections_patient_id'), 'longitudinal_summary_sections', ['patient_id'], unique=False)
    op.create_index(op.f('ix_longitudinal_summary_sections_section_type'), 'longitudinal_summary_sections', ['section_type'], unique=False)

    # 5. longitudinal_review_notes table
    op.create_table(
        'longitudinal_review_notes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=True),
        sa.Column('author_id', sa.String(length=36), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['longitudinal_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_longitudinal_review_notes_analysis_id'), 'longitudinal_review_notes', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_longitudinal_review_notes_patient_id'), 'longitudinal_review_notes', ['patient_id'], unique=False)


def downgrade() -> None:
    op.drop_table('longitudinal_review_notes')
    op.drop_table('longitudinal_summary_sections')
    op.drop_table('longitudinal_trends')
    op.drop_table('longitudinal_analyses')
    op.drop_table('clinical_observations')
