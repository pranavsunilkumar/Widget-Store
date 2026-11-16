from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from dotenv import load_dotenv

from database import get_db, engine
import models
import schemas
import crud
from auth import create_access_token, get_current_user

load_dotenv()

# Create database tables automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Widget Marketplace API",
    description="Backend API for Android Widget Marketplace & Overlay Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Widget Marketplace API", "version": "2.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.post("/api/auth/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = crud.create_user(db=db, user=user_in)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.post("/api/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, email=credentials.email, password=credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.post("/api/auth/token", response_model=schemas.Token)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Swagger UI Authorize button support"""
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/api/auth/me", response_model=schemas.User)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# ==========================================
# CLOUD DATA RETENTION & SYNC ENDPOINTS
# ==========================================

@app.get("/api/sync/pull", response_model=schemas.SyncPullResponse)
def pull_user_data(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Downloads all saved widgets, notebooks, and notes for the logged-in user."""
    return crud.sync_pull(db=db, user=current_user)

@app.post("/api/sync/push", response_model=schemas.SyncPullResponse)
def push_user_data(
    payload: schemas.SyncPushRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upserts the device's local widgets, notebooks, and notes to PostgreSQL and returns the merged state."""
    crud.sync_push(db=db, user_id=current_user.id, payload=payload)
    return crud.sync_pull(db=db, user=current_user)

@app.delete("/api/sync/widgets/{widget_id}")
def delete_synced_widget(
    widget_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deleted = crud.delete_installed_widget(db=db, user_id=current_user.id, widget_id=widget_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Widget not found")
    return {"message": "Widget deleted from cloud"}

# ==========================================
# MARKETPLACE LISTING ENDPOINTS
# ==========================================

@app.get("/listings/", response_model=List[schemas.WidgetListing])
def read_listings(
    skip: int = 0, 
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return crud.get_listings(db, skip=skip, limit=limit, category=category)

@app.post("/listings/", response_model=schemas.WidgetListing)
def create_listing(
    listing: schemas.WidgetListingCreate,
    db: Session = Depends(get_db)
):
    return crud.create_listing(db=db, listing=listing)

@app.get("/listings/{listing_id}", response_model=schemas.WidgetListing)
def read_listing(listing_id: int, db: Session = Depends(get_db)):
    db_listing = crud.get_listing(db, listing_id=listing_id)
    if db_listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return db_listing

@app.put("/listings/{listing_id}", response_model=schemas.WidgetListing)
def update_listing(
    listing_id: int,
    listing: schemas.WidgetListingUpdate,
    db: Session = Depends(get_db)
):
    db_listing = crud.update_listing(db, listing_id=listing_id, listing=listing)
    if db_listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return db_listing

@app.delete("/listings/{listing_id}")
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    success = crud.delete_listing(db, listing_id=listing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"message": "Listing deleted successfully"}

# ==========================================
# USER FAVORITES ENDPOINTS
# ==========================================

@app.post("/users/{user_id}/favorites/{listing_id}")
def add_favorite(user_id: int, listing_id: int, db: Session = Depends(get_db)):
    return crud.add_user_favorite(db, user_id=user_id, listing_id=listing_id)

@app.delete("/users/{user_id}/favorites/{listing_id}")
def remove_favorite(user_id: int, listing_id: int, db: Session = Depends(get_db)):
    success = crud.remove_user_favorite(db, user_id=user_id, listing_id=listing_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Favorite removed successfully"}

@app.get("/users/{user_id}/favorites/", response_model=List[schemas.WidgetListing])
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_favorites(db, user_id=user_id)