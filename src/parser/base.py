"""Base parser for JV-Data records.

This module provides the base class for all JV-Data record parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FieldDef:
    """Field definition for fixed-length record parsing.

    Attributes:
        name: Field name (matches database column name)
        start: Start position in record (0-indexed)
        length: Field length in bytes
        type: Data type ('str', 'int', 'float')
        description: Field description
    """

    name: str
    start: int
    length: int
    type: str = "str"
    description: str = ""


class BaseParser(ABC):
    """Base class for JV-Data record parsers.

    This abstract base class provides common functionality for parsing
    fixed-length JV-Data records.

    Subclasses must implement:
        - record_type: Class attribute identifying the record type (e.g., "RA")
        - _define_fields: Method returning field definitions

    Examples:
        >>> class RAParser(BaseParser):
        ...     record_type = "RA"
        ...
        ...     def _define_fields(self) -> List[FieldDef]:
        ...         return [
        ...             FieldDef("headRecordSpec", 0, 2, description="Record type"),
        ...             # ... more fields
        ...         ]
        >>>
        >>> parser = RAParser()
        >>> data = parser.parse(b"RA1202406010603081...")
    """

    record_type: str = ""  # Must be overridden by subclasses

    def __init__(self):
        """Initialize parser with field definitions."""
        if not self.record_type:
            raise ValueError(f"{self.__class__.__name__} must define record_type")

        # Get field definitions (may be tuples or FieldDef objects)
        field_defs = self._define_fields()

        # Convert tuples to FieldDef objects if necessary
        self._fields: List[FieldDef] = []
        for field_def in field_defs:
            if isinstance(field_def, tuple):
                # Legacy format: (start, length, name)
                start, length, name = field_def
                self._fields.append(FieldDef(
                    name=name,
                    start=start - 1,  # Convert 1-indexed to 0-indexed
                    length=length,
                    type="str",
                    description=""
                ))
            elif isinstance(field_def, FieldDef):
                self._fields.append(field_def)
            else:
                raise ValueError(f"Invalid field definition type: {type(field_def)}")

        self._field_map: Dict[str, FieldDef] = {f.name: f for f in self._fields}

        logger.debug(
            f"{self.__class__.__name__} initialized",
            record_type=self.record_type,
            field_count=len(self._fields),
        )

    @abstractmethod
    def _define_fields(self) -> List:
        """Define fields for this record type.

        Returns:
            List of FieldDef objects or tuples (start, length, name) defining the record structure
        """
        pass

    def parse(self, record: bytes) -> Dict[str, Any]:
        """Parse a JV-Data record.

        Args:
            record: Raw record bytes (Shift_JIS encoded)

        Returns:
            Dictionary mapping field names to values

        Raises:
            ValueError: If record type doesn't match or parsing fails

        Examples:
            >>> parser = RAParser()
            >>> data = parser.parse(b"RA12024...")
            >>> print(data['headRecordSpec'])
            'RA'
        """
        if not record:
            raise ValueError("Empty record")

        # Decode record from Shift_JIS
        try:
            record_str = record.decode(ENCODING_JVDATA)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode record: {e}")

        # Verify record type
        actual_type = record_str[:2]
        if actual_type != self.record_type:
            raise ValueError(
                f"Record type mismatch: expected {self.record_type}, got {actual_type}"
            )

        # Parse all fields
        result = {}
        for field_def in self._fields:
            try:
                value = self._extract_field(record_str, field_def)
                result[field_def.name] = value
            except Exception as e:
                logger.warning(
                    f"Failed to parse field {field_def.name}",
                    field=field_def.name,
                    error=str(e),
                )
                result[field_def.name] = None

        logger.debug(
            f"Parsed {self.record_type} record",
            record_type=self.record_type,
            field_count=len(result),
        )

        return result

    def _extract_field(self, record: str, field_def: FieldDef) -> Any:
        """Extract a single field from the record.

        Args:
            record: Decoded record string
            field_def: Field definition

        Returns:
            Parsed field value
        """
        end = field_def.start + field_def.length
        raw_value = record[field_def.start:end]

        # Strip whitespace
        value = raw_value.strip()

        # Convert type if specified
        if field_def.type == "int" and value:
            try:
                return int(value)
            except ValueError:
                logger.warning(
                    f"Failed to convert field to int: {field_def.name}={value}"
                )
                return None
        elif field_def.type == "float" and value:
            try:
                return float(value)
            except ValueError:
                logger.warning(
                    f"Failed to convert field to float: {field_def.name}={value}"
                )
                return None

        return value if value else None

    def get_field_names(self) -> List[str]:
        """Get list of all field names.

        Returns:
            List of field names in order
        """
        return [f.name for f in self._fields]

    def get_field_def(self, field_name: str) -> Optional[FieldDef]:
        """Get field definition by name.

        Args:
            field_name: Name of field

        Returns:
            FieldDef if found, None otherwise
        """
        return self._field_map.get(field_name)

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__} record_type={self.record_type} fields={len(self._fields)}>"
