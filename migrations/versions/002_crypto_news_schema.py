"""Create crypto news tables with dedup and compression

Revision ID: 002_crypto_news_schema
Revises: 001_initial
Create Date: 2026-02-03 03:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_crypto_news_schema'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create new crypto news tables."""
    
    # Create crypto_news table
    op.create_table(
        'crypto_news',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('source_id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('text_summary', sa.String(500), nullable=False),
        sa.Column('text_full', sa.Text(), nullable=True),
        sa.Column('layer1_matched_keywords', sa.JSON(), nullable=True),
        sa.Column('layer2_quality_score', sa.Float(), nullable=True),
        sa.Column('layer2_sentiment', sa.String(), nullable=True),
        sa.Column('layer2_urgency', sa.String(), nullable=True),
        sa.Column('layer2_credibility', sa.Float(), nullable=True),
        sa.Column('layer3_relevance', sa.Float(), nullable=True),
        sa.Column('layer3_credibility', sa.Float(), nullable=True),
        sa.Column('layer3_market_impact', sa.Float(), nullable=True),
        sa.Column('final_weight', sa.Float(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('message_link', sa.String(), nullable=True),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('occurrences', sa.Integer(), server_default='1'),
        sa.Column('view_count', sa.Integer(), server_default='0'),
        sa.Column('share_count', sa.Integer(), server_default='0'),
        sa.Column('user_feedback', sa.Integer(), server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for crypto_news
    op.create_index('idx_content_hash', 'crypto_news', ['content_hash'])
    op.create_index('idx_source_id', 'crypto_news', ['source_id'])
    op.create_index('idx_created_at', 'crypto_news', ['created_at'])
    op.create_index('idx_final_weight', 'crypto_news', ['final_weight'])
    
    # Create news_duplicates table
    op.create_table(
        'news_duplicates',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('first_news_id', sa.BigInteger(), nullable=False),
        sa.Column('source_id', sa.BigInteger(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('cosine_similarity', sa.Float(), server_default='0.95'),
        sa.Column('text_diff_ratio', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['first_news_id'], ['crypto_news.id'], )
    )
    
    # Create indices for news_duplicates
    op.create_index('idx_content_hash_dup', 'news_duplicates', ['content_hash'])
    op.create_index('idx_first_news_id', 'news_duplicates', ['first_news_id'])
    
    # Create news_archive table
    op.create_table(
        'news_archive',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('summary', sa.String(200), nullable=False),
        sa.Column('total_occurrences', sa.Integer(), server_default='1'),
        sa.Column('final_weight', sa.Float(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('original_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices for news_archive
    op.create_index('idx_archived_at', 'news_archive', ['archived_at'])


def downgrade() -> None:
    """Downgrade: drop all crypto news tables."""
    
    # Drop indices
    op.drop_index('idx_archived_at', table_name='news_archive')
    op.drop_index('idx_first_news_id', table_name='news_duplicates')
    op.drop_index('idx_content_hash_dup', table_name='news_duplicates')
    op.drop_index('idx_final_weight', table_name='crypto_news')
    op.drop_index('idx_created_at', table_name='crypto_news')
    op.drop_index('idx_source_id', table_name='crypto_news')
    op.drop_index('idx_content_hash', table_name='crypto_news')
    
    # Drop tables
    op.drop_table('news_archive')
    op.drop_table('news_duplicates')
    op.drop_table('crypto_news')
