from sqlalchemy import Column, String, Text, DateTime, Date, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date
import uuid

from app.core.database import Base


class DevLog(Base):
    __tablename__ = "dev_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True, default=date.today)
    title = Column(String(255), nullable=False)
    content_json = Column(JSONB, nullable=False, default={})
    tags = Column(ARRAY(String), nullable=True, default=[])
    
    # Future-proofing columns
    ai_summary = Column(Text, nullable=True)
    visibility = Column(String(20), nullable=False, default="private")  # private, team, public
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="logs")
    
    def __repr__(self):
        return f"<DevLog {self.title} - {self.log_date}>"
