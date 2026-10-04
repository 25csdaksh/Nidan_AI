"""Add Doctor AI Copilot tables

Revision ID: 0005_doctor_copilot
Revises: 0004_prescription_intelligence
Create Date: 2026-10-04 23:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_doctor_copilot'
down_revision = '0004_prescription_intelligence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create copilot_sessions table
    op.create_table(
        'copilot_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('clinician_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Clinical Case Review'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('context_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['clinician_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_copilot_sessions_patient_id', 'copilot_sessions', ['patient_id'])
    op.create_index('ix_copilot_sessions_clinician_id', 'copilot_sessions', ['clinician_id'])
    op.create_index('ix_copilot_sessions_status', 'copilot_sessions', ['status'])
    op.create_index('ix_copilot_sessions_patient_created', 'copilot_sessions', ['patient_id', 'created_at'])
    op.create_index('ix_copilot_sessions_clinician_patient', 'copilot_sessions', ['clinician_id', 'patient_id'])

    # 2. Create copilot_messages table
    op.create_table(
        'copilot_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(length=100), nullable=False, server_default='GENERAL_QUERY'),
        sa.Column('structured_response', sa.JSON(), nullable=False),
        sa.Column('evidence_ids', sa.JSON(), nullable=False),
        sa.Column('safety_status', sa.String(length=50), nullable=False, server_default='PASSED'),
        sa.Column('model_provider', sa.String(length=50), nullable=False, server_default='nidan-deterministic'),
        sa.Column('model_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('prompt_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('safety_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('response_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['copilot_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_copilot_messages_session_id', 'copilot_messages', ['session_id'])
    op.create_index('ix_copilot_messages_patient_id', 'copilot_messages', ['patient_id'])
    op.create_index('ix_copilot_messages_role', 'copilot_messages', ['role'])
    op.create_index('ix_copilot_messages_query_type', 'copilot_messages', ['query_type'])
    op.create_index('ix_copilot_messages_safety_status', 'copilot_messages', ['safety_status'])
    op.create_index('ix_copilot_messages_session_created', 'copilot_messages', ['session_id', 'created_at'])
    op.create_index('ix_copilot_messages_patient_created', 'copilot_messages', ['patient_id', 'created_at'])

    # 3. Create copilot_feedback table
    op.create_table(
        'copilot_feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('message_id', sa.String(length=36), nullable=False),
        sa.Column('clinician_id', sa.String(length=36), nullable=True),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('rating', sa.String(length=20), nullable=False),
        sa.Column('feedback_category', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['clinician_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['message_id'], ['copilot_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_copilot_feedback_message_id', 'copilot_feedback', ['message_id'])
    op.create_index('ix_copilot_feedback_clinician_id', 'copilot_feedback', ['clinician_id'])
    op.create_index('ix_copilot_feedback_category', 'copilot_feedback', ['feedback_category'])


def downgrade() -> None:
    op.drop_table('copilot_feedback')
    op.drop_table('copilot_messages')
    op.drop_table('copilot_sessions')
