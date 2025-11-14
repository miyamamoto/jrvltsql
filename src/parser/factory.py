"""Parser factory for JV-Data records.

This module provides a factory for creating appropriate parser instances
based on record type.
"""

from typing import Dict, Optional, Type

from src.parser.base import BaseParser
from src.parser.hr_parser import HRParser
from src.parser.ra_parser import RAParser
from src.parser.se_parser import SEParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ParserFactory:
    """Factory for creating JV-Data record parsers.

    This factory maintains a registry of parser classes and creates
    appropriate parser instances based on record type.

    Examples:
        >>> factory = ParserFactory()
        >>> parser = factory.get_parser("RA")
        >>> data = parser.parse(record_bytes)
    """

    def __init__(self):
        """Initialize parser factory with default parsers."""
        self._parsers: Dict[str, BaseParser] = {}
        self._parser_classes: Dict[str, Type[BaseParser]] = {
            "RA": RAParser,
            "SE": SEParser,
            "HR": HRParser,
        }

        logger.info("ParserFactory initialized", parser_types=list(self._parser_classes.keys()))

    def get_parser(self, record_type: str) -> Optional[BaseParser]:
        """Get parser for specified record type.

        Args:
            record_type: Two-character record type code (e.g., "RA", "SE", "HR")

        Returns:
            Parser instance if record type is supported, None otherwise

        Examples:
            >>> factory = ParserFactory()
            >>> parser = factory.get_parser("RA")
            >>> if parser:
            ...     data = parser.parse(record)
        """
        if not record_type:
            logger.warning("Empty record type provided")
            return None

        # Return cached parser if available
        if record_type in self._parsers:
            return self._parsers[record_type]

        # Create new parser instance
        parser_class = self._parser_classes.get(record_type)
        if not parser_class:
            logger.warning(f"No parser registered for record type: {record_type}")
            return None

        try:
            parser = parser_class()
            self._parsers[record_type] = parser
            logger.debug(f"Created parser for record type: {record_type}")
            return parser
        except Exception as e:
            logger.error(f"Failed to create parser for {record_type}", error=str(e))
            return None

    def register_parser(self, record_type: str, parser_class: Type[BaseParser]):
        """Register a custom parser class.

        Args:
            record_type: Two-character record type code
            parser_class: Parser class (must inherit from BaseParser)

        Raises:
            ValueError: If parser_class is not a BaseParser subclass

        Examples:
            >>> from src.parser.base import BaseParser
            >>> class CustomParser(BaseParser):
            ...     record_type = "XX"
            ...     def _define_fields(self):
            ...         return []
            >>>
            >>> factory = ParserFactory()
            >>> factory.register_parser("XX", CustomParser)
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"{parser_class} must inherit from BaseParser")

        self._parser_classes[record_type] = parser_class
        # Clear cached instance if exists
        if record_type in self._parsers:
            del self._parsers[record_type]

        logger.info(f"Registered parser for record type: {record_type}")

    def supported_types(self) -> list[str]:
        """Get list of supported record types.

        Returns:
            List of two-character record type codes
        """
        return list(self._parser_classes.keys())

    def parse(self, record: bytes) -> Optional[dict]:
        """Parse a record by auto-detecting its type.

        Args:
            record: Raw record bytes

        Returns:
            Parsed data dictionary, or None if parsing fails

        Examples:
            >>> factory = ParserFactory()
            >>> data = factory.parse(b"RA1202406010603081...")
            >>> print(data['headRecordSpec'])
            'RA'
        """
        if not record or len(record) < 2:
            logger.warning("Invalid record: too short")
            return None

        try:
            # Auto-detect record type from first 2 bytes
            record_type = record[:2].decode("ascii")
            parser = self.get_parser(record_type)

            if not parser:
                logger.warning(f"No parser available for record type: {record_type}")
                return None

            return parser.parse(record)

        except UnicodeDecodeError:
            logger.error("Failed to decode record type")
            return None
        except Exception as e:
            logger.error(f"Failed to parse record", error=str(e))
            return None

    def __repr__(self) -> str:
        """String representation."""
        return f"<ParserFactory types={len(self._parser_classes)} cached={len(self._parsers)}>"


# Global factory instance
_factory_instance: Optional[ParserFactory] = None


def get_parser_factory() -> ParserFactory:
    """Get global parser factory instance.

    Returns:
        Global ParserFactory instance (singleton)

    Examples:
        >>> factory = get_parser_factory()
        >>> parser = factory.get_parser("RA")
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ParserFactory()
    return _factory_instance
