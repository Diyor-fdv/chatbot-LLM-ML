from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.services.query_builder import run_readonly_sql

router = APIRouter()


class RunSQLRequest(BaseModel):
    sql: str = Field(..., min_length=6, max_length=20000)


@router.post("/run-sql")
def run_sql(req: RunSQLRequest, db: Session = Depends(get_db)):
    if settings.app_env.lower() not in ("dev", "local"):
        raise HTTPException(status_code=403, detail="Not available in this environment")
    data, columns = run_readonly_sql(db, req.sql)
    return {"columns": columns, "data": data, "rows": len(data)}

