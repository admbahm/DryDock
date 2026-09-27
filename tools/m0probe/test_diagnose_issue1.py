import json
import pathlib
import unittest

import diagnose_issue1_backpressure as diagnostic


class DiagnosticProfileTests(unittest.TestCase):
    def test_build_create_argv_uses_one_probe_mode_and_preserves_limits(self):
        profile_path = pathlib.Path("docs/evidence/m0-004/behavior/commands.json")
        profile = json.loads(profile_path.read_text())
        template = next(argv for argv in profile if "create" in argv and argv[-1] == "output")
        image = "sha256:" + "a" * 64

        argv = diagnostic.build_create_argv(template, image, "run123", "paused")

        self.assertEqual(argv[-2:], [image, "output"])
        self.assertEqual(argv.count("output"), 1)
        self.assertEqual(argv[argv.index("--name") + 1], "drydock-issue1-run123-paused")
        self.assertIn("drydock.issue1.run=run123", argv)
        self.assertEqual(argv[argv.index("--network") + 1], "none")
        self.assertIn("--read-only", argv)
        self.assertEqual(argv[argv.index("--memory") + 1], "256m")
        self.assertEqual(argv[argv.index("--pids-limit") + 1], "64")
        for disallowed in ("--volume", "--mount", "--env", "--privileged"):
            self.assertNotIn(disallowed, argv)


if __name__ == "__main__":
    unittest.main()
