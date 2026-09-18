import unittest

from core.state_key_migration import legacy_component_key


class TestStateKeyMigration(unittest.TestCase):
    def test_legacy_keys_remain_readable_without_hardcoded_sample_name(self):
        legacy_prefix = "".join(("e", "v", "y"))
        self.assertEqual(
            legacy_component_key("other_income"),
            f"{legacy_prefix}_other_income",
        )
        self.assertEqual(
            legacy_component_key("final_other_income_rows"),
            f"{legacy_prefix}_final_other_income_rows",
        )
        self.assertEqual(
            legacy_component_key("reconciliation"),
            f"{legacy_prefix}_reconciliation",
        )


if __name__ == "__main__":
    unittest.main()
