"""Base parser for JV-Data records.

This module provides the base class for all JV-Data record parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger

logger = get_logger(__name__)


def validate_fixed_record(
    record: bytes,
    record_type: str,
    expected_lengths: int | Tuple[int, ...],
) -> None:
    """Validate a complete fixed-length JV-Data physical record.

    Unknown lengths, a mismatched record ID, a non-CRLF terminator, and bytes
    that are not valid CP932 are rejected before any field can be persisted.
    """

    lengths = (
        (expected_lengths,)
        if isinstance(expected_lengths, int)
        else tuple(expected_lengths)
    )
    if len(record) not in lengths:
        raise ValueError(
            f"{record_type} record length mismatch: "
            f"expected={lengths}, actual={len(record)}"
        )
    expected_type = record_type.encode("ascii")
    if record[:2] != expected_type:
        raise ValueError(
            f"Record type mismatch: expected {record_type}, "
            f"got {record[:2]!r}"
        )
    if record[-2:] != b"\r\n":
        raise ValueError(f"{record_type} record delimiter must be CRLF")
    record.decode(ENCODING_JVDATA, errors="strict")


@dataclass
class FieldDef:
    """Field definition for fixed-length record parsing.

    Attributes:
        name: Field name (matches database column name)
        start: Start position in record (0-indexed)
        length: Field length in bytes
        type: Data type ('str', 'int', 'float') - legacy, use convert_type instead
        description: Field description
        convert_type: Target type for conversion (e.g., 'DATE', 'INT', 'DECIMAL')
        converter_kwargs: Additional kwargs for converter function
    """

    name: str
    start: int
    length: int
    type: str = "str"
    description: str = ""
    convert_type: Optional[str] = None
    converter_kwargs: Dict[str, Any] = field(default_factory=dict)


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

        record_length = getattr(self, "RECORD_LENGTH", None)
        if record_length is not None:
            validate_fixed_record(record, self.record_type, record_length)

        # JV-Data positions and lengths are byte-based. Decode only after
        # slicing so CP932 multibyte text cannot shift later field offsets.
        actual_type = record[:2].decode(ENCODING_JVDATA, errors="strict")
        if actual_type != self.record_type:
            raise ValueError(
                f"Record type mismatch: expected {self.record_type}, got {actual_type}"
            )

        # Parse all fields
        result = {}
        for field_def in self._fields:
            try:
                value = self._extract_field(record, field_def)
                result[field_def.name] = value
            except UnicodeDecodeError:
                # A fixed-width field boundary may split an otherwise valid
                # whole-record CP932 sequence. Never persist a partial row.
                raise
            except Exception as e:
                logger.warning(
                    f"Failed to parse field {field_def.name}",
                    field=field_def.name,
                    error=str(e),
                )
                result[field_def.name] = None

        # Note: Per-record debug logging removed to reduce verbosity during batch processing

        return result

    def _extract_field(self, record: bytes, field_def: FieldDef) -> Any:
        """Extract a single field from the record.

        Args:
            record: Raw JV-Data record bytes
            field_def: Field definition

        Returns:
            Parsed field value
        """
        end = field_def.start + field_def.length
        raw_value = record[field_def.start:end].decode(
            ENCODING_JVDATA, errors="strict"
        )

        # Strip whitespace
        value = raw_value.strip()

        # Use new convert_type if specified
        if field_def.convert_type:
            try:
                from src.parser.converters import convert_value
                return convert_value(value, field_def.convert_type, **field_def.converter_kwargs)
            except Exception as e:
                logger.warning(
                    f"Failed to convert field {field_def.name} to {field_def.convert_type}: {e}",
                    field=field_def.name,
                    value=value,
                    target_type=field_def.convert_type,
                )
                return None

        # Legacy type conversion (for backward compatibility)
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
