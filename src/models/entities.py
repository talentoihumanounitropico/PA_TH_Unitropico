from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base

# Junction for Tags
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
    extend_existing=True
)

# Junction for Responsibles
task_responsibles = Table(
    "task_responsibles",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("responsible_id", ForeignKey("responsibles.id"), primary_key=True),
    extend_existing=True
)

# Junction for Activity Supervisors
activity_supervisors = Table(
    "activity_supervisors",
    Base.metadata,
    Column("activity_id", ForeignKey("activities.id"), primary_key=True),
    Column("responsible_id", ForeignKey("responsibles.id"), primary_key=True),
    extend_existing=True
)

class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")

class Responsible(Base):
    __tablename__ = "responsibles"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    
    
    tasks: Mapped[List["Task"]] = relationship(
        secondary=task_responsibles, back_populates="responsibles"
    )
    supervised_activities: Mapped[List["Activity"]] = relationship(
        secondary=activity_supervisors, back_populates="supervisors"
    )

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20)) # Admin, Supervisor, Worker
    status: Mapped[str] = mapped_column(String(10), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Link to Responsible
    responsible_id: Mapped[Optional[int]] = mapped_column(ForeignKey("responsibles.id"))
    responsible: Mapped[Optional["Responsible"]] = relationship()

class PlanMacro(Base):
    """
    PlanMacro represents the highest level in the strategic hierarchy (Level 5).
    It usually corresponds to a full fiscal year of Human Resources management.
    """
    __tablename__ = "plan_macros"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="active")
    progress: Mapped[float] = mapped_column(Float, default=0.0) # Consolidated progress from Level 4
    
    policies: Mapped[List["Policy"]] = relationship(back_populates="plan_macro", cascade="all, delete-orphan")

class Policy(Base):
    __tablename__ = "policies"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_macro_id: Mapped[int] = mapped_column(ForeignKey("plan_macros.id"))
    name: Mapped[str] = mapped_column(String(200))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    
    plan_macro: Mapped["PlanMacro"] = relationship(back_populates="policies")
    strategic_items: Mapped[List["StrategicItem"]] = relationship(back_populates="policy", cascade="all, delete-orphan")

class StrategicItem(Base):
    __tablename__ = "strategic_items"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    
    policy: Mapped["Policy"] = relationship(back_populates="strategic_items")
    activities: Mapped[List["Activity"]] = relationship(back_populates="strategic_item", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    strategic_item_id: Mapped[int] = mapped_column(ForeignKey("strategic_items.id"))
    name: Mapped[str] = mapped_column(String(200))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="Pendiente")
    
    strategic_item: Mapped["StrategicItem"] = relationship(back_populates="activities")
    tasks: Mapped[List["Task"]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    evidences: Mapped[List["Evidence"]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    supervisors: Mapped[List["Responsible"]] = relationship(
        secondary=activity_supervisors, back_populates="supervised_activities"
    )

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"))
    name: Mapped[str] = mapped_column(String(200))
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="Pendiente")
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime) # Legacy
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime) # Nueva
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)   # Nueva
    fulfillment_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    responsible_name: Mapped[Optional[str]] = mapped_column(String(100))
    observations: Mapped[Optional[str]] = mapped_column(Text)
    
    activity: Mapped["Activity"] = relationship(back_populates="tasks")
    evidences: Mapped[List["Evidence"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    responsibles: Mapped[List["Responsible"]] = relationship(
        secondary=task_responsibles, back_populates="tasks"
    )

class Evidence(Base):
    __tablename__ = "evidences"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"))
    activity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("activities.id"))
    url: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(String(200))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    task: Mapped[Optional["Task"]] = relationship(back_populates="evidences")
    activity: Mapped[Optional["Activity"]] = relationship(back_populates="evidences")
