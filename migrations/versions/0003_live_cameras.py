"""Live cameras and event clips."""
from alembic import op
import sqlalchemy as sa
from backend.argus.db import Camera
revision='0003'
down_revision='0002'
def upgrade():
    bind=op.get_bind()
    Camera.__table__.create(bind,checkfirst=True)
    # 0001 creates tables from current models, so a fresh database may already have the column.
    if 'clip' not in {c['name'] for c in sa.inspect(bind).get_columns('events')}: op.add_column('events',sa.Column('clip',sa.Text(),nullable=True))
def downgrade():
    op.drop_column('events','clip')
    Camera.__table__.drop(op.get_bind())
