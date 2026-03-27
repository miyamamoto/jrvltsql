"""Data source definitions for JLTSQL.

This module defines the DataSource enum for JRA (中央競馬) data source.
"""

from enum import Enum
from typing import Optional


class DataSource(Enum):
    """Data source identifier enum.

    Attributes:
        JRA: 中央競馬 (JRA-VAN DataLab)
    """
    JRA = "jra"

    @property
    def display_name(self) -> str:
        """Get Japanese display name."""
        names = {
            DataSource.JRA: "中央競馬",
        }
        return names[self]

    @property
    def com_prog_id(self) -> Optional[str]:
        """Get COM ProgID for the data source."""
        prog_ids = {
            DataSource.JRA: "JVDTLab.JVLink",
        }
        return prog_ids[self]

    @classmethod
    def from_string(cls, value: str) -> "DataSource":
        """Create DataSource from string value.

        Args:
            value: String value ("jra")

        Returns:
            DataSource enum member

        Raises:
            ValueError: If value is not valid
        """
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Invalid data source: {value}")
