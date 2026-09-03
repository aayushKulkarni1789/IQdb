"""add postgis and image location geography gist index

Revision ID: 686ff0f4021f
Revises: 9f77bd0d1e2c
Create Date: 2026-09-03 05:29:19.723125

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import pgvector.sqlalchemy
import geoalchemy2


# revision identifiers, used by Alembic.
revision = '686ff0f4021f'
down_revision = '9f77bd0d1e2c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'image',
        sa.Column(
            'location',
            geoalchemy2.types.Geography(
                geometry_type='POINT',
                srid=4326,
                dimension=2,
                from_text='ST_GeogFromText',
                name='geography',
                spatial_index=False,
            ),
            nullable=True,
        ),
    )
    op.create_index('idx_image_location_gist', 'image', ['location'], unique=False, postgresql_using='gist')
    op.execute(
        "UPDATE image SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL;"
    )


def downgrade():
    op.drop_index('idx_image_location_gist', table_name='image', postgresql_using='gist')
    op.drop_column('image', 'location')
