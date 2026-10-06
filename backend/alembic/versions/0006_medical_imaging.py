"""Add Medical Imaging Intelligence (Chest X-Ray) tables

Revision ID: 0006_medical_imaging
Revises: 0005_doctor_copilot
Create Date: 2026-10-06 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_medical_imaging'
down_revision = '0005_doctor_copilot'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if imaging_studies already exists (from Phase 0 scaffold) and drop/recreate or migrate cleanly
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'imaging_studies' in tables:
        op.drop_table('imaging_studies')

    # 1. Create imaging_studies table
    op.create_table(
        'imaging_studies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('medical_document_id', sa.String(length=36), nullable=True),
        sa.Column('modality', sa.String(length=50), nullable=False, server_default='XRAY'),
        sa.Column('body_part', sa.String(length=100), nullable=False, server_default='CHEST'),
        sa.Column('view_position', sa.String(length=50), nullable=True, server_default='PA'),
        sa.Column('study_date', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('acquisition_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('image_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('image_quality_status', sa.String(length=50), nullable=False, server_default='QUALITY_ACCEPTED'),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='QUEUED'),
        sa.Column('current_analysis_id', sa.String(length=36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['medical_document_id'], ['medical_documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_imaging_studies_patient_id', 'imaging_studies', ['patient_id'])
    op.create_index('ix_imaging_studies_medical_document_id', 'imaging_studies', ['medical_document_id'])
    op.create_index('ix_imaging_studies_modality', 'imaging_studies', ['modality'])
    op.create_index('ix_imaging_studies_study_date', 'imaging_studies', ['study_date'])
    op.create_index('ix_imaging_studies_processing_status', 'imaging_studies', ['processing_status'])

    # 2. Create imaging_images table
    op.create_table(
        'imaging_images',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('imaging_study_id', sa.String(length=36), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('height', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bit_depth', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('color_space', sa.String(length=50), nullable=False, server_default='GRAYSCALE'),
        sa.Column('orientation', sa.String(length=50), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['imaging_study_id'], ['imaging_studies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_imaging_images_imaging_study_id', 'imaging_images', ['imaging_study_id'])
    op.create_index('ix_imaging_images_sha256_hash', 'imaging_images', ['sha256_hash'])

    # 3. Create imaging_analyses table
    op.create_table(
        'imaging_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('imaging_study_id', sa.String(length=36), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('preprocessing_version', sa.String(length=50), nullable=False),
        sa.Column('inference_version', sa.String(length=50), nullable=False),
        sa.Column('threshold_version', sa.String(length=50), nullable=False),
        sa.Column('calibration_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='QUEUED'),
        sa.Column('image_quality_status', sa.String(length=50), nullable=False, server_default='QUALITY_ACCEPTED'),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('output_json', sa.JSON(), nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['imaging_study_id'], ['imaging_studies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_imaging_analyses_imaging_study_id', 'imaging_analyses', ['imaging_study_id'])
    op.create_index('ix_imaging_analyses_status', 'imaging_analyses', ['status'])

    # 4. Create imaging_findings table
    op.create_table(
        'imaging_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('imaging_analysis_id', sa.String(length=36), nullable=False),
        sa.Column('finding_code', sa.String(length=100), nullable=False),
        sa.Column('finding_name', sa.String(length=255), nullable=False),
        sa.Column('anatomical_region', sa.String(length=100), nullable=False, server_default='LUNG'),
        sa.Column('probability', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='MODERATE'),
        sa.Column('model_threshold', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('localization_json', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clinician_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['imaging_analysis_id'], ['imaging_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_imaging_findings_imaging_analysis_id', 'imaging_findings', ['imaging_analysis_id'])
    op.create_index('ix_imaging_findings_finding_code', 'imaging_findings', ['finding_code'])
    op.create_index('ix_imaging_findings_review_status', 'imaging_findings', ['review_status'])


def downgrade() -> None:
    op.drop_table('imaging_findings')
    op.drop_table('imaging_analyses')
    op.drop_table('imaging_images')
    op.drop_table('imaging_studies')
