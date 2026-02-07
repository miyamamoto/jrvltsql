"""Data source definitions for JLTSQL.

This module defines the DataSource enum for selecting between
JRA (中央競馬) and NAR (地方競馬) data sources.
"""

from enum import Enum
from typing import Optional


class DataSource(Enum):
    """Data source identifier enum.

    Attributes:
        JRA: 中央競馬 (JRA-VAN DataLab)
        NAR: 地方競馬 (地方競馬DATA / UmaConn)
        ALL: 両方 (for status commands)
    """
    JRA = "jra"
    NAR = "nar"
    ALL = "all"

    @property
    def display_name(self) -> str:
        """Get Japanese display name."""
        names = {
            DataSource.JRA: "中央競馬",
            DataSource.NAR: "地方競馬",
            DataSource.ALL: "全て",
        }
        return names[self]

    @property
    def com_prog_id(self) -> Optional[str]:
        """Get COM ProgID for the data source."""
        prog_ids = {
            DataSource.JRA: "JVDTLab.JVLink",
            DataSource.NAR: "NVDTLabLib.NVLink",
            DataSource.ALL: None,
        }
        return prog_ids[self]

    @classmethod
    def from_string(cls, value: str) -> "DataSource":
        """Create DataSource from string value.

        Args:
            value: String value ("jra", "nar", or "all")

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
