"""Add Clinical Intelligence and Reference Range tables

Revision ID: 0002_clinical_intelligence
Revises: 0001_initial
Create Date: 2026-10-04 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_clinical_intelligence'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. reference_ranges table
    op.create_table(
        'reference_ranges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analyte', sa.String(length=255), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('panel', sa.String(length=100), nullable=False),
        sa.Column('sex', sa.String(length=20), nullable=False),
        sa.Column('age_min', sa.Float(), nullable=False),
        sa.Column('age_max', sa.Float(), nullable=False),
        sa.Column('pregnancy_status', sa.String(length=30), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('lower_bound', sa.Float(), nullable=True),
        sa.Column('upper_bound', sa.Float(), nullable=True),
        sa.Column('lower_operator', sa.String(length=10), nullable=False),
        sa.Column('upper_operator', sa.String(length=10), nullable=False),
        sa.Column('critical_low', sa.Float(), nullable=True),
        sa.Column('critical_high', sa.Float(), nullable=True),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_version', sa.String(length=50), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('effective_from', sa.String(length=50), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reference_ranges_analyte', 'reference_ranges', ['analyte'])
    op.create_index('ix_reference_ranges_canonical_name', 'reference_ranges', ['canonical_name'])
    op.create_index('ix_reference_ranges_panel', 'reference_ranges', ['panel'])
    op.create_index('ix_reference_ranges_sex', 'reference_ranges', ['sex'])
    op.create_index('ix_reference_ranges_unit', 'reference_ranges', ['unit'])
    op.create_index('ix_reference_ranges_is_active', 'reference_ranges', ['is_active'])

    # 2. clinical_analyses table
    op.create_table(
        'clinical_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('extraction_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_version', sa.Integer(), nullable=False),
        sa.Column('rule_set_version', sa.String(length=50), nullable=False),
        sa.Column('reference_range_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('findings_count', sa.Integer(), nullable=False),
        sa.Column('abnormal_count', sa.Integer(), nullable=False),
        sa.Column('critical_count', sa.Integer(), nullable=False),
        sa.Column('pattern_count', sa.Integer(), nullable=False),
        sa.Column('summary_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['medical_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['extraction_id'], ['document_extractions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clinical_analyses_document_id', 'clinical_analyses', ['document_id'])
    op.create_index('ix_clinical_analyses_extraction_id', 'clinical_analyses', ['extraction_id'])
    op.create_index('ix_clinical_analyses_patient_id', 'clinical_analyses', ['patient_id'])
    op.create_index('ix_clinical_analyses_status', 'clinical_analyses', ['status'])

    # 3. clinical_findings table
    op.create_table(
        'clinical_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('extraction_id', sa.String(length=36), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=True),
        sa.Column('finding_type', sa.String(length=50), nullable=False),
        sa.Column('analyte', sa.String(length=255), nullable=True),
        sa.Column('value', sa.String(length=100), nullable=True),
        sa.Column('normalized_value', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('clinical_association', sa.Text(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=False),
        sa.Column('rule_version', sa.String(length=50), nullable=False),
        sa.Column('reference_source', sa.String(length=50), nullable=False),
        sa.Column('reference_source_version', sa.String(length=100), nullable=True),
        sa.Column('requires_review', sa.Boolean(), nullable=False),
        sa.Column('review_status', sa.String(length=50), nullable=False),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['clinical_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['medical_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['document_extraction_entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['extraction_id'], ['document_extractions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clinical_findings_analysis_id', 'clinical_findings', ['analysis_id'])
    op.create_index('ix_clinical_findings_analyte', 'clinical_findings', ['analyte'])
    op.create_index('ix_clinical_findings_document_id', 'clinical_findings', ['document_id'])
    op.create_index('ix_clinical_findings_entity_id', 'clinical_findings', ['entity_id'])
    op.create_index('ix_clinical_findings_extraction_id', 'clinical_findings', ['extraction_id'])
    op.create_index('ix_clinical_findings_finding_type', 'clinical_findings', ['finding_type'])
    op.create_index('ix_clinical_findings_patient_id', 'clinical_findings', ['patient_id'])
    op.create_index('ix_clinical_findings_requires_review', 'clinical_findings', ['requires_review'])
    op.create_index('ix_clinical_findings_review_status', 'clinical_findings', ['review_status'])
    op.create_index('ix_clinical_findings_rule_id', 'clinical_findings', ['rule_id'])
    op.create_index('ix_clinical_findings_severity', 'clinical_findings', ['severity'])
    op.create_index('ix_clinical_findings_status', 'clinical_findings', ['status'])


def downgrade() -> None:
    op.drop_table('clinical_findings')
    op.drop_table('clinical_analyses')
    op.drop_table('reference_ranges')
