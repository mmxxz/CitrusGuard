"""Add case management fields

Revision ID: add_case_management_fields
Revises: 2a867e316341
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_case_management_fields'
down_revision = '2a867e316341'
branch_labels = None
depends_on = None


def upgrade():
    # Add maintenance advice field to diagnoses table
    op.add_column('diagnoses', sa.Column('maintenance_advice', sa.TEXT(), nullable=True))
    
    # Add severity level field to diagnoses table
    op.add_column('diagnoses', sa.Column('severity_level', sa.String(), nullable=True))
    
    # Add case status field to diagnoses table
    op.add_column('diagnoses', sa.Column('case_status', sa.String(), nullable=True, default='active'))
    
    # Add last maintenance date to diagnoses table
    op.add_column('diagnoses', sa.Column('last_maintenance_date', sa.DateTime(timezone=True), nullable=True))
    
    # Add maintenance history to diagnoses table
    op.add_column('diagnoses', sa.Column('maintenance_history', postgresql.JSONB(), nullable=True))


def downgrade():
    # Remove added columns
    op.drop_column('diagnoses', 'maintenance_history')
    op.drop_column('diagnoses', 'last_maintenance_date')
    op.drop_column('diagnoses', 'case_status')
    op.drop_column('diagnoses', 'severity_level')
    op.drop_column('diagnoses', 'maintenance_advice')
