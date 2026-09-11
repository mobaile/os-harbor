import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from osharbor.cli import main
from osharbor.core import HarborError


class CliTests(unittest.TestCase):
    def test_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['--registry', str(Path(tmp)/'systems.json'), 'list']), 0)
            self.assertIn('"systems": []', out.getvalue())

    def test_error_exit(self):
        with patch('osharbor.cli.WindowsVolumes', side_effect=HarborError('Unavailable')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['verify', '--bundle', 'missing']), 2)

    def test_doctor_records_unavailable_host(self):
        with tempfile.TemporaryDirectory() as tmp, patch('osharbor.cli.run_ps', side_effect=HarborError('Unavailable')), patch('osharbor.cli.WindowsVolumes', side_effect=HarborError('Unavailable')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--registry', str(Path(tmp)/'systems.json'), 'doctor']), 1)
