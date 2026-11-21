from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# --- User & Auth Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class TokenData(BaseModel):
    user_id: Optional[int] = None

# --- Widget Listing Schemas ---
class WidgetListingBase(BaseModel):
    name: str
    description: str
    category: Optional[str] = None
    author: str
    version: str = "1.0.0"
    price: float = 0.0
    config_schema: Dict[str, Any]
    preview_image_url: Optional[str] = None
    is_featured: bool = False

class WidgetListingCreate(WidgetListingBase):
    pass

class WidgetListingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    config_schema: Optional[Dict[str, Any]] = None
    preview_image_url: Optional[str] = None
    is_featured: Optional[bool] = None
    is_approved: Optional[bool] = None

class WidgetListing(WidgetListingBase):
    id: int
    download_count: int
    rating: float
    review_count: int
    is_approved: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# --- Installed Widget Schemas ---
class InstalledWidgetBase(BaseModel):
    id: str  # UUID from Flutter
    listing_id: Union[str, int]
    widget_type: Optional[str] = None
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    state: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_enabled: bool = True
    placement: Optional[str] = "homescreen"

class InstalledWidgetCreate(InstalledWidgetBase):
    user_id: Optional[int] = None

class InstalledWidgetUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    placement: Optional[str] = None
    last_used: Optional[datetime] = None

class InstalledWidget(InstalledWidgetBase):
    user_id: int
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# --- Notebook & Note Schemas (For Cloud Sync) ---
class NoteEntrySync(BaseModel):
    id: str
    notebook_id: str
    title: str = ""
    content: str
    raw_text: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_app: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotebookSync(BaseModel):
    id: str
    name: str
    description: str = ""
    color_hex: str = "#4F46E5"
    icon_name: str = "book"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Cloud Sync Payloads ---
class SyncPushRequest(BaseModel):
    installed_widgets: List[InstalledWidgetBase] = Field(default_factory=list)
    notebooks: List[NotebookSync] = Field(default_factory=list)
    notes: List[NoteEntrySync] = Field(default_factory=list)

class SyncPullResponse(BaseModel):
    user: User
    installed_widgets: List[InstalledWidget]
    notebooks: List[NotebookSync]
    notes: List[NoteEntrySync]
    synced_at: datetime

# --- Widget Usage & Favorites Schemas ---
class WidgetUsageBase(BaseModel):
    event_type: str
    duration_seconds: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

class WidgetUsageCreate(WidgetUsageBase):
    widget_id: str

class WidgetUsage(WidgetUsageBase):
    id: int
    widget_id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class UserFavoriteBase(BaseModel):
    user_id: int
    listing_id: int

class UserFavoriteCreate(UserFavoriteBase):
    pass

class UserFavorite(UserFavoriteBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True