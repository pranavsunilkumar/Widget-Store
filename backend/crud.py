from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
import models
import schemas
from auth import get_password_hash, verify_password

# --- User CRUD & Auth ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# --- Widget Listing CRUD ---
def get_listings(db: Session, skip: int = 0, limit: int = 100, category: str = None):
    query = db.query(models.WidgetListing).filter(models.WidgetListing.is_approved == True)
    if category:
        query = query.filter(models.WidgetListing.category == category)
    return query.offset(skip).limit(limit).all()

def get_listing(db: Session, listing_id: int):
    return db.query(models.WidgetListing).filter(models.WidgetListing.id == listing_id).first()

def create_listing(db: Session, listing: schemas.WidgetListingCreate):
    db_listing = models.WidgetListing(**listing.model_dump())
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

def update_listing(db: Session, listing_id: int, listing: schemas.WidgetListingUpdate):
    db_listing = get_listing(db, listing_id)
    if not db_listing:
        return None
    
    update_data = listing.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_listing, field, value)
    
    db.commit()
    db.refresh(db_listing)
    return db_listing

def delete_listing(db: Session, listing_id: int):
    db_listing = get_listing(db, listing_id)
    if not db_listing:
        return False
    
    db.delete(db_listing)
    db.commit()
    return True

# --- User Favorites CRUD ---
def add_user_favorite(db: Session, user_id: int, listing_id: int):
    existing = db.query(models.UserFavorite).filter(
        and_(
            models.UserFavorite.user_id == user_id,
            models.UserFavorite.listing_id == listing_id
        )
    ).first()
    
    if existing:
        return existing
    
    db_favorite = models.UserFavorite(user_id=user_id, listing_id=listing_id)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite

def remove_user_favorite(db: Session, user_id: int, listing_id: int):
    db_favorite = db.query(models.UserFavorite).filter(
        and_(
            models.UserFavorite.user_id == user_id,
            models.UserFavorite.listing_id == listing_id
        )
    ).first()
    
    if not db_favorite:
        return False
    
    db.delete(db_favorite)
    db.commit()
    return True

def get_user_favorites(db: Session, user_id: int):
    favorites = db.query(models.UserFavorite).filter(
        models.UserFavorite.user_id == user_id
    ).all()
    
    listing_ids = [fav.listing_id for fav in favorites]
    return db.query(models.WidgetListing).filter(
        models.WidgetListing.id.in_(listing_ids)
    ).all() if listing_ids else []

# --- Installed Widgets CRUD ---
def get_installed_widget(db: Session, widget_id: str, user_id: int = None):
    query = db.query(models.InstalledWidget).filter(models.InstalledWidget.id == widget_id)
    if user_id is not None:
        query = query.filter(models.InstalledWidget.user_id == user_id)
    return query.first()

def get_user_installed_widgets(db: Session, user_id: int):
    return db.query(models.InstalledWidget).filter(models.InstalledWidget.user_id == user_id).all()

def upsert_installed_widget(db: Session, user_id: int, widget: schemas.InstalledWidgetBase):
    db_widget = db.query(models.InstalledWidget).filter(models.InstalledWidget.id == widget.id).first()
    if db_widget:
        db_widget.user_id = user_id
        db_widget.listing_id = str(widget.listing_id)
        db_widget.widget_type = widget.widget_type
        db_widget.name = widget.name
        db_widget.config = widget.config
        db_widget.state = widget.state
        db_widget.is_enabled = widget.is_enabled
        db_widget.placement = widget.placement
    else:
        db_widget = models.InstalledWidget(
            id=widget.id,
            user_id=user_id,
            listing_id=str(widget.listing_id),
            widget_type=widget.widget_type,
            name=widget.name,
            config=widget.config,
            state=widget.state,
            is_enabled=widget.is_enabled,
            placement=widget.placement
        )
        db.add(db_widget)
    db.commit()
    db.refresh(db_widget)
    return db_widget

def delete_installed_widget(db: Session, user_id: int, widget_id: str) -> bool:
    db_widget = get_installed_widget(db, widget_id=widget_id, user_id=user_id)
    if not db_widget:
        return False
    db.delete(db_widget)
    db.commit()
    return True

# --- Full Cloud Sync (Push & Pull) ---
def sync_push(db: Session, user_id: int, payload: schemas.SyncPushRequest):
    # 1. Upsert Installed Widgets
    for w in payload.installed_widgets:
        upsert_installed_widget(db, user_id=user_id, widget=w)

    # 2. Upsert Notebooks
    for nb in payload.notebooks:
        db_nb = db.query(models.Notebook).filter(models.Notebook.id == nb.id).first()
        if db_nb:
            db_nb.user_id = user_id
            db_nb.name = nb.name
            db_nb.description = nb.description
            db_nb.color_hex = nb.color_hex
            db_nb.icon_name = nb.icon_name
        else:
            db_nb = models.Notebook(
                id=nb.id,
                user_id=user_id,
                name=nb.name,
                description=nb.description,
                color_hex=nb.color_hex,
                icon_name=nb.icon_name
            )
            db.add(db_nb)
    db.commit()

    # 3. Upsert Notes
    for note in payload.notes:
        db_note = db.query(models.NoteEntry).filter(models.NoteEntry.id == note.id).first()
        if db_note:
            db_note.user_id = user_id
            db_note.notebook_id = note.notebook_id
            db_note.title = note.title
            db_note.content = note.content
            db_note.raw_text = note.raw_text
            db_note.tags = note.tags
            db_note.source_app = note.source_app
        else:
            db_note = models.NoteEntry(
                id=note.id,
                notebook_id=note.notebook_id,
                user_id=user_id,
                title=note.title,
                content=note.content,
                raw_text=note.raw_text,
                tags=note.tags,
                source_app=note.source_app
            )
            db.add(db_note)
    db.commit()

def sync_pull(db: Session, user: models.User) -> schemas.SyncPullResponse:
    widgets = db.query(models.InstalledWidget).filter(models.InstalledWidget.user_id == user.id).all()
    notebooks = db.query(models.Notebook).filter(models.Notebook.user_id == user.id).all()
    notes = db.query(models.NoteEntry).filter(models.NoteEntry.user_id == user.id).all()
    
    return schemas.SyncPullResponse(
        user=user,
        installed_widgets=widgets,
        notebooks=notebooks,
        notes=notes,
        synced_at=datetime.now(timezone.utc)
    )