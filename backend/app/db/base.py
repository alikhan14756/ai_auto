"""Database base imports for Alembic and Model discovery."""

from app.db.session import Base
import app.models  # noqa: F401 - Register all 21 models with Base.metadata

# Export Base
__all__ = ["Base"]
