"""Camera detection filters, tiled small-object detection and saved detections."""
from alembic import op
import sqlalchemy as sa
from backend.argus.db import SavedDetection
revision='0004'
down_revision='0003'
def upgrade():
    bind=op.get_bind(); existing={c['name'] for c in sa.inspect(bind).get_columns('cameras')}
    # 0001 creates tables from current models, so a fresh database may already have these columns.
    if 'classes' not in existing: op.add_column('cameras',sa.Column('classes',sa.JSON(),nullable=True))
    if 'tiling' not in existing: op.add_column('cameras',sa.Column('tiling',sa.Boolean(),nullable=False,server_default=sa.false()))
    if 'min_box' not in existing: op.add_column('cameras',sa.Column('min_box',sa.Integer(),nullable=False,server_default='0'))
    SavedDetection.__table__.create(bind,checkfirst=True)
def downgrade():
    SavedDetection.__table__.drop(op.get_bind())
    for column in ('min_box','tiling','classes'): op.drop_column('cameras',column)
