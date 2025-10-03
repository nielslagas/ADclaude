"""Add audio support and hybrid RAG

Revision ID: 20250512_audio_hybrid_rag
Revises: 
Create Date: 2025-05-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250512_audio_hybrid_rag'
down_revision = None  # set to the previous revision or None if this is the first
branch_labels = None
depends_on = None


def upgrade():
    # Voeg nieuwe kolommen toe aan document tabel
    op.add_column('document', sa.Column('document_type', sa.String(), nullable=True, server_default='document'))
    op.add_column('document', sa.Column('content', sa.Text(), nullable=True))
    op.add_column('document', sa.Column('processing_strategy', sa.String(), nullable=True))
    
    # Voeg indexen toe voor nieuwe kolommen
    op.create_index(op.f('ix_document_document_type'), 'document', ['document_type'], unique=False)
    
    # Update bestaande documenten
    op.execute("UPDATE document SET document_type = 'document' WHERE document_type IS NULL")


def downgrade():
    # Verwijder indexen
    op.drop_index(op.f('ix_document_document_type'), table_name='document')
    
    # Verwijder kolommen
    op.drop_column('document', 'processing_strategy')
    op.drop_column('document', 'content')
    op.drop_column('document', 'document_type')