"""Add structured report support

Revision ID: 20250102_structured_reports
Revises: add_comment_system
Create Date: 2025-01-02 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250102_structured_reports'
down_revision = '20250528_comment_system'  # Reference to the last migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add support for structured AD reports while maintaining backward compatibility
    """
    
    # Add new columns to report table for structured data support
    print("Adding structured report support columns...")
    
    # Add generation method tracking
    op.add_column('report', sa.Column(
        'generation_method', 
        sa.String(50), 
        nullable=True, 
        server_default='legacy'
    ))
    
    # Add structured data format version
    op.add_column('report', sa.Column(
        'format_version', 
        sa.String(10), 
        nullable=True, 
        server_default='1.0'
    ))
    
    # Add layout type (separate from template_id)
    op.add_column('report', sa.Column(
        'layout_type', 
        sa.String(50), 
        nullable=True, 
        server_default='standaard'
    ))
    
    # Add export capabilities tracking
    op.add_column('report', sa.Column(
        'export_formats', 
        postgresql.JSON(), 
        nullable=True
    ))
    
    # Add quality metrics for structured reports
    op.add_column('report', sa.Column(
        'quality_metrics', 
        postgresql.JSON(), 
        nullable=True
    ))
    
    # Add performance tracking
    op.add_column('report', sa.Column(
        'generation_time_ms', 
        sa.Integer(), 
        nullable=True
    ))
    
    # Add FML rubrieken count for quick access
    op.add_column('report', sa.Column(
        'fml_rubrieken_count', 
        sa.Integer(), 
        nullable=True, 
        server_default='0'
    ))
    
    # Add structured content indicator
    op.add_column('report', sa.Column(
        'has_structured_data', 
        sa.Boolean(), 
        nullable=True, 
        server_default='false'
    ))
    
    # Create indexes for better performance
    print("Creating indexes for structured report columns...")
    
    op.create_index(
        'ix_report_generation_method', 
        'report', 
        ['generation_method'], 
        unique=False
    )
    
    op.create_index(
        'ix_report_format_version', 
        'report', 
        ['format_version'], 
        unique=False
    )
    
    op.create_index(
        'ix_report_has_structured_data', 
        'report', 
        ['has_structured_data'], 
        unique=False
    )
    
    op.create_index(
        'ix_report_layout_type', 
        'report', 
        ['layout_type'], 
        unique=False
    )
    
    # Update existing reports with default values
    print("Updating existing reports with default structured report values...")
    
    # Mark existing reports as legacy format
    op.execute("""
        UPDATE report 
        SET 
            generation_method = 'legacy',
            format_version = '1.0',
            layout_type = 'standaard',
            has_structured_data = false,
            fml_rubrieken_count = 0
        WHERE generation_method IS NULL
    """)
    
    # Try to detect existing structured reports based on content structure
    op.execute("""
        UPDATE report 
        SET 
            has_structured_data = true,
            generation_method = 'hybrid'
        WHERE content IS NOT NULL 
        AND (
            content::text LIKE '%structured_data%' 
            OR content::text LIKE '%fml_rubrieken%'
            OR content::text LIKE '%belastbaarheid%'
        )
    """)
    
    print("Structured report support migration completed successfully!")


def downgrade():
    """
    Remove structured report support columns
    """
    print("Removing structured report support...")
    
    # Drop indexes
    op.drop_index('ix_report_layout_type', table_name='report')
    op.drop_index('ix_report_has_structured_data', table_name='report')
    op.drop_index('ix_report_format_version', table_name='report')
    op.drop_index('ix_report_generation_method', table_name='report')
    
    # Drop columns
    op.drop_column('report', 'has_structured_data')
    op.drop_column('report', 'fml_rubrieken_count')
    op.drop_column('report', 'generation_time_ms')
    op.drop_column('report', 'quality_metrics')
    op.drop_column('report', 'export_formats')
    op.drop_column('report', 'layout_type')
    op.drop_column('report', 'format_version')
    op.drop_column('report', 'generation_method')
    
    print("Structured report support removed successfully!")