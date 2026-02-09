"""Parser factory for JV-Data records.

This module provides a factory for creating appropriate parser instances
based on record type. Supports 41 record types (38 JRA + 3 NAR: HA, NC, NU).

Auto-generated parsers based on: 公式JV-Data仕様書 Ver.4.9.0.1
"""

import importlib
from typing import Any, Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


# All supported record types (41 parsers: 38 official JRA + 3 NAR: HA, NU, NC)
ALL_RECORD_TYPES = [
    'AV', 'BN', 'BR', 'BT', 'CC', 'CH', 'CK', 'CS', 'DM',
    'H1', 'H6', 'HC', 'HN', 'HR', 'HS', 'HY',
    'JC', 'JG', 'KS',
    'HA',  # NAR (地方競馬) 払戻データ
    'NC',  # NAR (地方競馬) 競馬場マスタ
    'NK',  # NAR (地方競馬) 騎手 (KSと同一構造)
    'NU',  # NAR (地方競馬) 競走馬登録データ
    'OA',  # NAR (地方競馬) オッズ
    'O1', 'O2', 'O3', 'O4', 'O5', 'O6',
    'RA', 'RC', 'SE', 'SK', 'TC', 'TK', 'TM',
    'UM', 'WC', 'WE', 'WF', 'WH', 'YS'
]

# NAR record type aliases: maps NAR-specific codes to JRA equivalents
# These use the same parser/struct as their JRA counterpart
PARSER_ALIASES = {
    'NK': 'KS',  # NAR騎手 → KSパーサー (JV_KS_KISYU構造体)
}


class ParserFactory:
    """Factory for creating JV-Data record parsers.

    This factory maintains a registry of parser instances and creates
    appropriate parsers based on record type.

    All parsers are auto-generated from official JV-Data specification.

    Examples:
        >>> factory = ParserFactory()
        >>> parser = factory.get_parser("RA")
        >>> data = parser.parse(record_bytes)
    """

    def __init__(self):
        """Initialize parser factory with dynamic parser loading."""
        self._parsers: Dict[str, Any] = {}
        self._parser_classes: Dict[str, Any] = {}

        logger.info("ParserFactory initialized", total_types=len(ALL_RECORD_TYPES))

    def _load_parser_class(self, record_type: str):
        """Dynamically load parser class for record type.

        Args:
            record_type: Two-character record type code (e.g., "RA", "SE", "HR")

        Returns:
            Parser class if found, None otherwise
        """
        try:
            # Convert record type to module name (e.g., "RA" -> "ra_parser")
            module_name = f"src.parser.{record_type.lower()}_parser"
            class_name = f"{record_type.upper()}Parser"

            # Import module
            module = importlib.import_module(module_name)

            # Get parser class
            parser_class = getattr(module, class_name)

            logger.debug(f"Loaded parser class: {class_name}")
            return parser_class

        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load parser for {record_type}: {e}")
            return None

    def get_parser(self, record_type: str):
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

        # Normalize to uppercase
        record_type = record_type.upper()

        # Return cached parser if available
        if record_type in self._parsers:
            return self._parsers[record_type]

        # Resolve alias (e.g., NK -> KS)
        resolved_type = PARSER_ALIASES.get(record_type, record_type)

        # Load parser class if not cached
        if record_type not in self._parser_classes:
            parser_class = self._load_parser_class(resolved_type)
            if not parser_class:
                logger.warning(f"No parser available for record type: {record_type}")
                return None
            self._parser_classes[record_type] = parser_class

        # Create parser instance
        try:
            parser = self._parser_classes[record_type]()
            self._parsers[record_type] = parser
            logger.debug(f"Created parser for record type: {record_type}")
            return parser
        except Exception as e:
            logger.error(f"Failed to create parser for {record_type}", error=str(e))
            return None

    def supported_types(self) -> list:
        """Get list of supported record types.

        Returns:
            List of two-character record type codes
        """
        return ALL_RECORD_TYPES.copy()

    def parse(self, record: bytes) -> Optional[dict]:
        """Parse a record by auto-detecting its type.

        Args:
            record: Raw record bytes

        Returns:
            Parsed data dictionary, or None if parsing fails

        Examples:
            >>> factory = ParserFactory()
            >>> data = factory.parse(b"RA1202406010603081...")
            >>> print(data['RecordSpec'])
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

            parsed_result = parser.parse(record)
            # Some parsers (H1, H6) return List[Dict] for full-struct records
            return parsed_result

        except UnicodeDecodeError:
            logger.error("Failed to decode record type")
            return None
        except Exception as e:
            logger.error("Failed to parse record", error=str(e))
            return None

    def __repr__(self) -> str:
        """String representation."""
        return f"<ParserFactory types={len(ALL_RECORD_TYPES)} cached={len(self._parsers)}>"


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
