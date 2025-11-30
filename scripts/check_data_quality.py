#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Data Quality Verification Tool for JLTSQL

This tool checks data quality in the JRA-VAN database by:
1. Checking record counts for each table
2. Validating NULL values in important columns
3. Checking date field validity (Year, MonthDay)
4. Validating code fields (JyoCD, etc.) are in valid ranges
5. Checking referential integrity (e.g., KettoNum references)
6. Verifying record consistency (e.g., races have corresponding results)

Usage:
    python scripts/check_data_quality.py --db-path data/keiba.db
    python scripts/check_data_quality.py --db-path data/keiba.db --output report.json --verbose
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SCHEMAS
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Valid ranges for code fields
VALID_RANGES = {
    'JyoCD': {
        'min': 1,
        'max': 99,
        'description': '競馬場コード (01-99)',
        'valid_values': {
            # 中央競馬
            1: '札幌', 2: '函館', 3: '福島', 4: '新潟', 5: '東京',
            6: '中山', 7: '中京', 8: '京都', 9: '阪神', 10: '小倉',
            # 地方競馬 (代表例)
            30: '門別', 35: '盛岡', 36: '水沢', 42: '浦和', 43: '船橋',
            44: '大井', 45: '川崎', 46: '金沢', 47: '笠松', 48: '名古屋',
            50: '園田', 51: '姫路', 54: '高知', 55: '佐賀',
        }
    },
    'Kaiji': {
        'min': 1,
        'max': 10,
        'description': '開催回次 (1-10)',
    },
    'Nichiji': {
        'min': 1,
        'max': 12,
        'description': '日次 (1-12)',
    },
    'RaceNum': {
        'min': 1,
        'max': 12,
        'description': 'レース番号 (1-12)',
    },
    'Umaban': {
        'min': 1,
        'max': 28,
        'description': '馬番 (1-28)',
    },
    'TrackCD': {
        'min': 10,
        'max': 59,
        'description': 'トラックコード',
        'valid_values': {
            10: '芝', 11: 'ダ', 17: '障害芝', 18: '障害芝ダ', 19: '障害芝直',
            20: '障害ダ', 21: '障害ダ直', 22: '障害芝直ダ', 23: '障害芝ダ直',
            51: 'Aコース', 52: 'Bコース', 53: 'Cコース', 54: 'Dコース',
        }
    },
}


class DataQualityChecker:
    """Data quality checker for JRA-VAN database"""

    def __init__(self, db_path: str, verbose: bool = False):
        """Initialize data quality checker

        Args:
            db_path: Path to SQLite database file
            verbose: Enable verbose output
        """
        self.db_path = Path(db_path)
        self.verbose = verbose
        self.db = SQLiteDatabase({'path': str(self.db_path)})
        self.issues: List[Dict[str, Any]] = []
        self.table_stats: Dict[str, Dict[str, Any]] = {}

    def check_all(self) -> Dict[str, Any]:
        """Run all data quality checks

        Returns:
            Dictionary containing quality report
        """
        self.db.connect()
        try:
            print("=" * 80)
            print("Data Quality Report")
            print("=" * 80)
            print(f"Database: {self.db_path}")
            print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Get table count
            tables = self._get_existing_tables()
            print(f"Tables: {len(tables)}")
            print()

            # Check each table
            for table_name in sorted(tables):
                self._check_table(table_name)

            # Check cross-table relationships
            print("\n" + "=" * 80)
            print("Cross-Table Integrity Checks")
            print("=" * 80)
            self._check_referential_integrity()

            # Generate summary
            print("\n" + "=" * 80)
            print("Summary")
            print("=" * 80)
            print(f"Total Issues Found: {len(self.issues)}")

            if self.issues:
                print("\nIssues by Severity:")
                critical = sum(1 for i in self.issues if i.get('severity') == 'CRITICAL')
                warning = sum(1 for i in self.issues if i.get('severity') == 'WARNING')
                info = sum(1 for i in self.issues if i.get('severity') == 'INFO')
                print(f"  CRITICAL: {critical}")
                print(f"  WARNING:  {warning}")
                print(f"  INFO:     {info}")

                # Show top issues
                print("\nTop Issues:")
                for i, issue in enumerate(self.issues[:10], 1):
                    severity = issue.get('severity', 'INFO')
                    table = issue.get('table', 'N/A')
                    message = issue.get('message', '')
                    print(f"  {i}. [{severity}] {table}: {message}")

            # Generate report
            report = {
                'database': str(self.db_path),
                'generated_at': datetime.now().isoformat(),
                'total_tables': len(tables),
                'total_issues': len(self.issues),
                'table_stats': self.table_stats,
                'issues': self.issues,
            }

            return report

        finally:
            self.db.disconnect()

    def _get_existing_tables(self) -> List[str]:
        """Get list of existing tables in database

        Returns:
            List of table names
        """
        result = self.db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row['name'] for row in result]

    def _check_table(self, table_name: str):
        """Check data quality for a single table

        Args:
            table_name: Name of table to check
        """
        print(f"\n[{table_name}]")

        # Get record count
        count_result = self.db.fetch_one(f"SELECT COUNT(*) as count FROM `{table_name}`")
        record_count = count_result['count'] if count_result else 0

        if record_count == 0:
            print(f"  Records: 0 (EMPTY)")
            self.table_stats[table_name] = {
                'record_count': 0,
                'quality': 'EMPTY',
            }
            return

        print(f"  Records: {record_count:,}")

        # Initialize stats
        stats = {
            'record_count': record_count,
            'quality': 'GOOD',
            'checks': {},
        }

        # Get table schema
        schema_info = self.db.get_table_info(table_name)
        columns = {col['name']: col['type'] for col in schema_info}

        # Check date fields
        if 'Year' in columns and 'MonthDay' in columns:
            self._check_date_fields(table_name, record_count, stats)

        # Check code fields
        for code_field in ['JyoCD', 'Kaiji', 'Nichiji', 'RaceNum', 'Umaban', 'TrackCD']:
            if code_field in columns:
                self._check_code_field(table_name, code_field, record_count, stats)

        # Check important fields for NULL values
        self._check_null_values(table_name, columns, record_count, stats)

        # Check for duplicate primary keys (should not happen with PRIMARY KEY constraint)
        self._check_duplicates(table_name, stats)

        # Print quality assessment
        quality = stats.get('quality', 'UNKNOWN')
        print(f"  Quality: {quality}")

        self.table_stats[table_name] = stats

    def _check_date_fields(self, table_name: str, total_records: int, stats: Dict[str, Any]):
        """Check validity of date fields (Year, MonthDay)

        Args:
            table_name: Name of table
            total_records: Total number of records
            stats: Stats dictionary to update
        """
        # Check Year range (should be reasonable, e.g., 1900-2100)
        year_check = self.db.fetch_one(f"""
            SELECT
                MIN(Year) as min_year,
                MAX(Year) as max_year,
                COUNT(CASE WHEN Year IS NULL OR Year < 1900 OR Year > 2100 THEN 1 END) as invalid_count
            FROM `{table_name}`
        """)

        if year_check:
            min_year = year_check['min_year']
            max_year = year_check['max_year']
            invalid_count = year_check['invalid_count']

            if min_year and max_year:
                print(f"  Date Range: {min_year}-01-01 ~ {max_year}-12-31")

            if invalid_count > 0:
                pct = (invalid_count / total_records) * 100
                self._add_issue(
                    table_name,
                    f"{invalid_count:,} records ({pct:.1f}%) with invalid Year",
                    'WARNING'
                )
                stats['quality'] = 'WARNING'

        # Check MonthDay format (should be 4 digits MMDD)
        monthday_check = self.db.fetch_one(f"""
            SELECT
                COUNT(CASE WHEN
                    MonthDay IS NULL
                    OR LENGTH(CAST(MonthDay AS TEXT)) != 4
                    OR CAST(SUBSTR(CAST(MonthDay AS TEXT), 1, 2) AS INTEGER) > 12
                    OR CAST(SUBSTR(CAST(MonthDay AS TEXT), 1, 2) AS INTEGER) < 1
                    OR CAST(SUBSTR(CAST(MonthDay AS TEXT), 3, 2) AS INTEGER) > 31
                    OR CAST(SUBSTR(CAST(MonthDay AS TEXT), 3, 2) AS INTEGER) < 1
                THEN 1 END) as invalid_count
            FROM `{table_name}`
        """)

        if monthday_check and monthday_check['invalid_count'] > 0:
            invalid_count = monthday_check['invalid_count']
            pct = (invalid_count / total_records) * 100
            self._add_issue(
                table_name,
                f"{invalid_count:,} records ({pct:.1f}%) with invalid MonthDay format",
                'WARNING'
            )
            stats['quality'] = 'WARNING'

        stats['checks']['date_fields'] = 'CHECKED'

    def _check_code_field(self, table_name: str, field_name: str, total_records: int, stats: Dict[str, Any]):
        """Check validity of code fields

        Args:
            table_name: Name of table
            field_name: Name of code field
            total_records: Total number of records
            stats: Stats dictionary to update
        """
        if field_name not in VALID_RANGES:
            return

        range_info = VALID_RANGES[field_name]
        min_val = range_info['min']
        max_val = range_info['max']

        # Check for values outside valid range
        invalid_check = self.db.fetch_one(f"""
            SELECT COUNT(*) as invalid_count
            FROM `{table_name}`
            WHERE {field_name} IS NOT NULL
            AND ({field_name} < {min_val} OR {field_name} > {max_val})
        """)

        if invalid_check and invalid_check['invalid_count'] > 0:
            invalid_count = invalid_check['invalid_count']
            pct = (invalid_count / total_records) * 100
            self._add_issue(
                table_name,
                f"{invalid_count:,} records ({pct:.1f}%) with invalid {field_name} ({range_info['description']})",
                'WARNING'
            )
            stats['quality'] = 'WARNING'

        stats['checks'][f'code_{field_name}'] = 'CHECKED'

    def _check_null_values(self, table_name: str, columns: Dict[str, str], total_records: int, stats: Dict[str, Any]):
        """Check NULL values in important columns

        Args:
            table_name: Name of table
            columns: Dictionary of column names and types
            total_records: Total number of records
            stats: Stats dictionary to update
        """
        # Define important fields that should not be NULL
        important_fields = {
            'NL_RA': ['Year', 'MonthDay', 'JyoCD', 'RaceNum', 'RaceName'],
            'RT_RA': ['Year', 'MonthDay', 'JyoCD', 'RaceNum', 'RaceName'],
            'NL_SE': ['Year', 'MonthDay', 'JyoCD', 'RaceNum', 'Umaban', 'KettoNum'],
            'RT_SE': ['Year', 'MonthDay', 'JyoCD', 'RaceNum', 'Umaban', 'KettoNum'],
            'NL_UM': ['KettoNum', 'Bamei'],
            'NL_KS': ['KisyuCode', 'KisyuName'],
            'NL_CH': ['ChokyosiCode', 'ChokyosiName'],
        }

        fields_to_check = important_fields.get(table_name, [])
        null_stats = []

        for field in fields_to_check:
            if field not in columns:
                continue

            null_check = self.db.fetch_one(f"""
                SELECT COUNT(*) as null_count
                FROM `{table_name}`
                WHERE {field} IS NULL OR TRIM(CAST({field} AS TEXT)) = ''
            """)

            if null_check and null_check['null_count'] > 0:
                null_count = null_check['null_count']
                pct = (null_count / total_records) * 100
                null_stats.append(f"{field}={pct:.1f}%")

                if pct > 10:  # More than 10% NULL is concerning
                    self._add_issue(
                        table_name,
                        f"{null_count:,} records ({pct:.1f}%) with NULL {field}",
                        'WARNING'
                    )
                    stats['quality'] = 'WARNING'

        if null_stats and self.verbose:
            print(f"  NULL ratio: {', '.join(null_stats)}")

        stats['checks']['null_values'] = 'CHECKED'

    def _check_duplicates(self, table_name: str, stats: Dict[str, Any]):
        """Check for duplicate records

        Args:
            table_name: Name of table
            stats: Stats dictionary to update
        """
        # Define primary key columns for each table type
        pk_definitions = {
            'NL_RA': ['Year', 'MonthDay', 'JyoCD', 'Kaiji', 'Nichiji', 'RaceNum'],
            'RT_RA': ['Year', 'MonthDay', 'JyoCD', 'Kaiji', 'Nichiji', 'RaceNum'],
            'NL_SE': ['Year', 'MonthDay', 'JyoCD', 'Kaiji', 'Nichiji', 'RaceNum', 'Umaban'],
            'RT_SE': ['Year', 'MonthDay', 'JyoCD', 'Kaiji', 'Nichiji', 'RaceNum', 'Umaban'],
            'NL_UM': ['KettoNum'],
            'NL_KS': ['KisyuCode'],
            'NL_CH': ['ChokyosiCode'],
            'NL_BN': ['BanusiCode'],
            'NL_BR': ['BreederCode'],
        }

        pk_cols = pk_definitions.get(table_name)
        if not pk_cols:
            return

        # Get table schema to check if columns exist
        schema_info = self.db.get_table_info(table_name)
        available_cols = {col['name'] for col in schema_info}

        # Filter to only existing columns
        pk_cols = [col for col in pk_cols if col in available_cols]
        if not pk_cols:
            return

        # Check for duplicates
        pk_str = ', '.join(pk_cols)
        dup_check = self.db.fetch_one(f"""
            SELECT COUNT(*) as dup_count
            FROM (
                SELECT {pk_str}, COUNT(*) as cnt
                FROM `{table_name}`
                GROUP BY {pk_str}
                HAVING cnt > 1
            )
        """)

        if dup_check and dup_check['dup_count'] > 0:
            dup_count = dup_check['dup_count']
            self._add_issue(
                table_name,
                f"{dup_count:,} duplicate primary key combinations found",
                'CRITICAL'
            )
            stats['quality'] = 'CRITICAL'

        stats['checks']['duplicates'] = 'CHECKED'

    def _check_referential_integrity(self):
        """Check referential integrity between tables"""

        # Check if NL_SE records reference existing NL_RA records
        if self.db.table_exists('NL_SE') and self.db.table_exists('NL_RA'):
            orphan_check = self.db.fetch_one("""
                SELECT COUNT(*) as orphan_count
                FROM NL_SE se
                LEFT JOIN NL_RA ra
                    ON se.Year = ra.Year
                    AND se.MonthDay = ra.MonthDay
                    AND se.JyoCD = ra.JyoCD
                    AND se.Kaiji = ra.Kaiji
                    AND se.Nichiji = ra.Nichiji
                    AND se.RaceNum = ra.RaceNum
                WHERE ra.Year IS NULL
            """)

            if orphan_check and orphan_check['orphan_count'] > 0:
                orphan_count = orphan_check['orphan_count']

                # Get total NL_SE count for percentage
                total_se = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")
                total_count = total_se['cnt'] if total_se else 1
                pct = (orphan_count / total_count) * 100

                print(f"\n  NL_SE → NL_RA: {pct:.1f}% linked ({total_count - orphan_count:,}/{total_count:,})")

                if pct > 1:  # More than 1% orphaned is concerning
                    self._add_issue(
                        'NL_SE',
                        f"{orphan_count:,} records ({pct:.1f}%) do not have corresponding NL_RA records",
                        'WARNING'
                    )
            else:
                # All linked
                total_se = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")
                total_count = total_se['cnt'] if total_se else 0
                if total_count > 0:
                    print(f"\n  NL_SE → NL_RA: 100.0% linked ({total_count:,}/{total_count:,})")

        # Check if NL_SE records reference valid horses in NL_UM
        if self.db.table_exists('NL_SE') and self.db.table_exists('NL_UM'):
            orphan_horses = self.db.fetch_one("""
                SELECT COUNT(*) as orphan_count
                FROM NL_SE se
                LEFT JOIN NL_UM um ON se.KettoNum = um.KettoNum
                WHERE um.KettoNum IS NULL AND se.KettoNum IS NOT NULL
            """)

            if orphan_horses and orphan_horses['orphan_count'] > 0:
                orphan_count = orphan_horses['orphan_count']

                total_se = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE WHERE KettoNum IS NOT NULL")
                total_count = total_se['cnt'] if total_se else 1
                pct = (orphan_count / total_count) * 100

                print(f"  NL_SE → NL_UM: {100-pct:.1f}% linked ({total_count - orphan_count:,}/{total_count:,})")

                if pct > 5:  # More than 5% is concerning
                    self._add_issue(
                        'NL_SE',
                        f"{orphan_count:,} records ({pct:.1f}%) reference non-existent horses (KettoNum)",
                        'WARNING'
                    )
            else:
                total_se = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE WHERE KettoNum IS NOT NULL")
                total_count = total_se['cnt'] if total_se else 0
                if total_count > 0:
                    print(f"  NL_SE → NL_UM: 100.0% linked ({total_count:,}/{total_count:,})")

        # Check race-to-results ratio
        if self.db.table_exists('NL_RA') and self.db.table_exists('NL_SE'):
            race_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_RA")
            result_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")

            if race_count and result_count:
                races = race_count['cnt']
                results = result_count['cnt']
                if races > 0:
                    ratio = results / races
                    print(f"  Race to Results Ratio: {ratio:.1f} results per race")

                    if ratio < 5:  # Less than 5 results per race is unusual
                        self._add_issue(
                            'NL_RA/NL_SE',
                            f"Unusually low results per race: {ratio:.1f} (expected ~8-18)",
                            'INFO'
                        )

    def _add_issue(self, table: str, message: str, severity: str = 'WARNING'):
        """Add an issue to the issues list

        Args:
            table: Table name
            message: Issue description
            severity: Severity level (CRITICAL, WARNING, INFO)
        """
        self.issues.append({
            'table': table,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
        })


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check data quality in JRA-VAN database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic check
    python scripts/check_data_quality.py --db-path data/keiba.db

    # Verbose output with JSON report
    python scripts/check_data_quality.py --db-path data/keiba.db --output report.json --verbose

    # Check test database
    python scripts/check_data_quality.py --db-path data/test_simple.db
        """
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='data/keiba.db',
        help='Path to SQLite database file (default: data/keiba.db)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON report file path (optional)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Check if database exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    try:
        # Run quality check
        checker = DataQualityChecker(str(db_path), verbose=args.verbose)
        report = checker.check_all()

        # Save JSON report if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nDetailed report saved to: {output_path}")

    except Exception as e:
        logger.error(f"Quality check failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
