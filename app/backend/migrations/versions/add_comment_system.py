"""Add comment system for report reviews

Revision ID: 20250528_comment_system
Revises: 20250512_audio_hybrid_rag
Create Date: 2025-05-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250528_comment_system'
down_revision = '20250512_audio_hybrid_rag'
branch_labels = None
depends_on = None


def upgrade():
    # Create comment table
    op.create_table('comment',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('comment_type', sa.String(), nullable=False, server_default='feedback'),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['comment.id'], ),
        sa.ForeignKeyConstraint(['report_id'], ['report.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient querying
    op.create_index(op.f('ix_comment_id'), 'comment', ['id'], unique=False)
    op.create_index(op.f('ix_comment_report_id'), 'comment', ['report_id'], unique=False)
    op.create_index(op.f('ix_comment_section_id'), 'comment', ['section_id'], unique=False)
    op.create_index(op.f('ix_comment_user_id'), 'comment', ['user_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_comment_user_id'), table_name='comment')
    op.drop_index(op.f('ix_comment_section_id'), table_name='comment')
    op.drop_index(op.f('ix_comment_report_id'), table_name='comment')
    op.drop_index(op.f('ix_comment_id'), table_name='comment')
    
    # Drop comment table
    op.drop_table('comment')