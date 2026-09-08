import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from nostr_dvm.utils.env_utils import get_env_path, load_env, set_env_key
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


class EnvironmentConfigTests(unittest.TestCase):
    def test_path_does_not_depend_on_working_directory(self):
        expected = Path(__file__).resolve().parents[2] / ".env"
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(get_env_path(), expected)
            finally:
                os.chdir(original)

    def test_existing_wallet_and_identity_load_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("LNBITS_INVOICE_KEY_TEST=invoice\nLNBITS_ADMIN_KEY_TEST=admin\n"
                                "LNBITS_WALLET_ID_TEST=wallet\nLNADDRESS_TEST=test@example.com\n"
                                "DVM_PRIVATE_KEY_TEST=existing-key\n")
            with patch.dict(os.environ, {}, clear=True), patch(
                    "nostr_dvm.utils.env_utils.get_env_path", return_value=env_path), patch(
                    "nostr_dvm.utils.zap_utils.create_lnbits_wallet") as create_wallet:
                self.assertEqual(check_and_set_ln_bits_keys("test", "unused"),
                                 ("invoice", "admin", "wallet", "test@example.com"))
                self.assertEqual(check_and_set_private_key("test"), "existing-key")
                create_wallet.assert_not_called()

    def test_load_preserves_explicit_environment_and_write_updates_process(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("LNBITS_HOST=file-host\n")
            with patch.dict(os.environ, {"LNBITS_HOST": "process-host"}, clear=True), patch(
                    "nostr_dvm.utils.env_utils.get_env_path", return_value=env_path):
                load_env()
                self.assertEqual(os.environ["LNBITS_HOST"], "process-host")
                set_env_key("LNBITS_INVOICE_KEY_TEST", "new-invoice")
                self.assertEqual(os.environ["LNBITS_INVOICE_KEY_TEST"], "new-invoice")
                self.assertEqual(dotenv_values(env_path)["LNBITS_INVOICE_KEY_TEST"], "new-invoice")

    def test_failed_wallet_creation_does_not_write_empty_credentials(self):
        with patch("nostr_dvm.utils.zap_utils.load_env"), patch.dict(os.environ, {}, clear=True), patch(
                "nostr_dvm.utils.zap_utils.create_lnbits_wallet", return_value=("", "", "", "failed")), patch(
                "nostr_dvm.utils.zap_utils.add_key_to_env_file") as write_key:
            self.assertEqual(check_and_set_ln_bits_keys("test", "unused"), ("", "", "", ""))
            write_key.assert_not_called()


if __name__ == "__main__":
    unittest.main()
