"""Add Prescription Intelligence and Medication Safety tables

Revision ID: 0004_prescription_intelligence
Revises: 0003_longitudinal_intelligence
Create Date: 2026-10-04 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_prescription_intelligence'
down_revision = '0003_longitudinal_intelligence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Alter/Extend prescriptions table if needed or create if not present
    # In PostgreSQL, add new columns to prescriptions table
    with op.batch_alter_table('prescriptions') as batch_op:
        batch_op.add_column(sa.Column('document_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('prescriber_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('prescription_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('source_confidence', sa.Float(), server_default='1.0', nullable=False))
        batch_op.add_column(sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False))
        batch_op.create_foreign_key('fk_prescriptions_document_id', 'medical_documents', ['document_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_prescriptions_document_id', ['document_id'])
        batch_op.create_index('ix_prescriptions_prescription_date', ['prescription_date'])

    # 2. prescription_medications table
    op.create_table(
        'prescription_medications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('prescription_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('raw_medication_name', sa.String(length=255), nullable=False),
        sa.Column('canonical_medication_name', sa.String(length=255), nullable=False),
        sa.Column('generic_name', sa.String(length=255), nullable=True),
        sa.Column('brand_name', sa.String(length=255), nullable=True),
        sa.Column('strength_value', sa.Float(), nullable=True),
        sa.Column('strength_unit', sa.String(length=50), nullable=True),
        sa.Column('dosage_form', sa.String(length=100), nullable=True),
        sa.Column('route', sa.String(length=50), nullable=True),
        sa.Column('frequency_code', sa.String(length=50), nullable=True),
        sa.Column('frequency_text', sa.String(length=100), nullable=True),
        sa.Column('dose_quantity', sa.String(length=100), nullable=True),
        sa.Column('duration_value', sa.Integer(), nullable=True),
        sa.Column('duration_unit', sa.String(length=50), nullable=True),
        sa.Column('instruction_text', sa.Text(), nullable=True),
        sa.Column('is_prn', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('bounding_box', sa.JSON(), nullable=True),
        sa.Column('review_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_prescription_medications_patient_id', 'prescription_medications', ['patient_id'])
    op.create_index('ix_prescription_medications_prescription_id', 'prescription_medications', ['prescription_id'])
    op.create_index('ix_prescription_medications_canonical_name', 'prescription_medications', ['canonical_medication_name'])
    op.create_index('ix_prescription_medications_review_status', 'prescription_medications', ['review_status'])

    # 3. medication_safety_findings table
    op.create_table(
        'medication_safety_findings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('prescription_id', sa.String(length=36), nullable=True),
        sa.Column('medication_id', sa.String(length=36), nullable=True),
        sa.Column('finding_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=50), server_default='INFO', nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('clinical_association', sa.String(length=255), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('rule_id', sa.String(length=100), nullable=True),
        sa.Column('rule_version', sa.String(length=50), server_default='1.0.0', nullable=False),
        sa.Column('requires_review', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('review_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('clinician_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['medication_id'], ['prescription_medications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_medication_safety_findings_patient_id', 'medication_safety_findings', ['patient_id'])
    op.create_index('ix_medication_safety_findings_prescription_id', 'medication_safety_findings', ['prescription_id'])
    op.create_index('ix_medication_safety_findings_type', 'medication_safety_findings', ['finding_type'])
    op.create_index('ix_medication_safety_findings_severity', 'medication_safety_findings', ['severity'])
    op.create_index('ix_medication_safety_findings_review_status', 'medication_safety_findings', ['review_status'])

    # 4. medication_interaction_rules table
    op.create_table(
        'medication_interaction_rules',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('drug_a', sa.String(length=255), nullable=False),
        sa.Column('drug_b', sa.String(length=255), nullable=False),
        sa.Column('interaction_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), server_default='MODERATE', nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('clinical_association', sa.String(length=255), nullable=True),
        sa.Column('evidence_source', sa.String(length=255), nullable=False),
        sa.Column('source_version', sa.String(length=50), server_default='2026.1', nullable=False),
        sa.Column('rule_version', sa.String(length=50), server_default='1.0.0', nullable=False),
        sa.Column('requires_review', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_medication_interaction_rules_drug_a', 'medication_interaction_rules', ['drug_a'])
    op.create_index('ix_medication_interaction_rules_drug_b', 'medication_interaction_rules', ['drug_b'])


def downgrade() -> None:
    op.drop_table('medication_interaction_rules')
    op.drop_table('medication_safety_findings')
    op.drop_table('prescription_medications')
    with op.batch_alter_table('prescriptions') as batch_op:
        batch_op.drop_index('ix_prescriptions_prescription_date')
        batch_op.drop_index('ix_prescriptions_document_id')
        batch_op.drop_constraint('fk_prescriptions_document_id', type_='foreignkey')
        batch_op.drop_column('status')
        batch_op.drop_column('source_confidence')
        batch_op.drop_column('prescription_date')
        batch_op.drop_column('prescriber_name')
        batch_op.drop_column('document_id')
