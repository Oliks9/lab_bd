import re
import unittest
from pathlib import Path

from quiz_client.installer import installation_steps


class InstallationCompletenessTest(unittest.TestCase):
    def test_required_objects_match_installed_schema(self):
        root = Path(__file__).resolve().parents[2] / "sql"
        source = (root / "tests/check_invalid_objects.sql").read_text(encoding="utf-8")
        required = {
            (kind, name)
            for kind, names in re.findall(
                r"require_objects\('([^']+)', SYS\.ODCIVARCHAR2LIST\((.*?)\)\);",
                source,
                re.S,
            )
            for name in re.findall(r"'([^']+)'", names)
        }
        installed = set()
        for step in installation_steps(root):
            match = re.match(
                r"CREATE\s+(?:OR\s+REPLACE\s+)?(PACKAGE BODY|PACKAGE|TABLE|FUNCTION|PROCEDURE|TRIGGER)\s+(\w+)",
                step.sql,
                re.I,
            )
            if match:
                installed.add(tuple(value.upper() for value in match.groups()))
        self.assertEqual(len(required), 32)
        self.assertEqual(required, installed)


if __name__ == "__main__":
    unittest.main()
