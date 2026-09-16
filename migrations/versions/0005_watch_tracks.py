"""Session-scoped person track watchlist."""
from alembic import op
from backend.argus.db import WatchTrack

revision = '0005'
down_revision = '0004'

def upgrade():
    WatchTrack.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    WatchTrack.__table__.drop(op.get_bind())
