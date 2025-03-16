"""File for the Violation ORM model."""

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from .base import Base


class Violation(Base):
    """Class for Violation ORM model."""

    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    defendant = Column(String)
    plaintiff = Column(String)
    year = Column(Integer)
    settlement = Column(Float, nullable=True)
    violation_type = Column(String)
    data_source = Column(String)
    link = Column(String)
    notes = Column(String)

    __table_args__ = (
        UniqueConstraint("defendant", "year", "link", name="unique_violation"),
    )

    def __repr__(self):
        """Return a string representation of the Violation object."""
        return (
            f"<Violation(defendant='{self.defendant}', year={self.year},"
            f" settlement={self.settlement})>"
        )
