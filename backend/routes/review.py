import json
import os
import pickle
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add padosi root to path so we can import from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from database import get_db
import models
from auth import decode_token

router = APIRouter(prefix="/api", tags=["review"])
security = HTTPBearer()

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "bug_risk_model.pkl")
_model = None


def get_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            loaded = pickle.load(f)
            # Backward compatible: accept both raw estimator and packaged artifact.
            if isinstance(loaded, dict) and "model" in loaded:
                _model = loaded
            else:
                _model = {"model": loaded, "meta": {"artifact_version": "legacy"}}
    return _model


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class ReviewRequest(BaseModel):
    code: str
    filename: Optional[str] = "untitled.py"
    language: Optional[str] = None


@router.post("/review")
def review(
    data: ReviewRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from src.predict import review_code

    import numpy as np

    model = get_model()
    result = review_code(
        data.code,
        model,
        language=data.language,
        filename=data.filename,
    )

    # Convert numpy types to native Python so json.dumps works
    def _native(obj):
        if isinstance(obj, dict):
            return {k: _native(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_native(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    result = _native(result)

    review_record = models.Review(
        user_id=current_user.id,
        code=data.code,
        filename=data.filename,
        result=json.dumps(result),
    )
    db.add(review_record)
    db.commit()
    db.refresh(review_record)

    return {
        "id": review_record.id,
        "result": result,
        "created_at": review_record.created_at.isoformat(),
    }


@router.get("/reviews")
def get_reviews(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reviews = (
        db.query(models.Review)
        .filter(models.Review.user_id == current_user.id)
        .order_by(models.Review.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "result": json.loads(r.result) if r.result else {},
            "created_at": r.created_at.isoformat(),
            "code": r.code,
        }
        for r in reviews
    ]
