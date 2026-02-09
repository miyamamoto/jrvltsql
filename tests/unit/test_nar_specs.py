"""Tests for NAR-specific spec selection in quickstart."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestNARSpecSelection:
    """Ensure NAR modes use NAR-specific specs (no JRA-only specs like TOKU/BLDN)."""

    def _get_setup_runner(self, data_source, mode):
        from scripts.quickstart import QuickstartRunner
        settings = {
            'data_source': data_source,
            'mode': mode,
            'db_type': 'sqlite',
            'db_path': ':memory:',
        }
        return QuickstartRunner(settings)

    def test_nar_simple_uses_nar_specs(self):
        runner = self._get_setup_runner('nar', 'simple')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        assert 'DIFN' in spec_names
        assert 'RACE' in spec_names
        # No JRA-only specs
        for jra_only in ['TOKU', 'BLDN', 'MING', 'SLOP', 'WOOD', 'YSCH', 'HOSN', 'HOYU', 'COMM']:
            assert jra_only not in spec_names, f"{jra_only} should not be in NAR simple specs"

    def test_nar_standard_uses_nar_specs(self):
        runner = self._get_setup_runner('nar', 'standard')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        assert 'DIFN' in spec_names
        assert 'RACE' in spec_names
        for jra_only in ['TOKU', 'BLDN', 'MING', 'SLOP', 'WOOD', 'YSCH', 'HOSN', 'HOYU', 'COMM']:
            assert jra_only not in spec_names, f"{jra_only} should not be in NAR standard specs"

    def test_nar_full_uses_nar_specs(self):
        runner = self._get_setup_runner('nar', 'full')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        assert 'DIFN' in spec_names
        assert 'RACE' in spec_names
        for jra_only in ['TOKU', 'BLDN', 'MING', 'SLOP', 'WOOD', 'YSCH', 'HOSN', 'HOYU', 'COMM']:
            assert jra_only not in spec_names, f"{jra_only} should not be in NAR full specs"

    def test_nar_update_uses_nar_specs(self):
        runner = self._get_setup_runner('nar', 'update')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        for jra_only in ['TOKU', 'TCVN', 'RCVN']:
            assert jra_only not in spec_names, f"{jra_only} should not be in NAR update specs"

    def test_jra_standard_still_has_full_specs(self):
        """JRA standard mode should still include all JRA specs."""
        runner = self._get_setup_runner('jra', 'standard')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        assert 'TOKU' in spec_names
        assert 'RACE' in spec_names
        assert 'BLDN' in spec_names
        assert 'COMM' in spec_names

    def test_jra_full_still_has_full_specs(self):
        runner = self._get_setup_runner('jra', 'full')
        specs = runner._get_specs_for_mode()
        spec_names = [s[0] for s in specs]
        assert 'TOKU' in spec_names
        assert 'COMM' in spec_names
