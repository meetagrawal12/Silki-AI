from sqlalchemy import Column, String, Text, Integer
from app.db.database import Base  # adjust to your actual Base import

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="general")