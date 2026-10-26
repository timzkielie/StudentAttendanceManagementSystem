import unittest
from unittest.mock import patch

import auth


class TestPasswordHashing(unittest.TestCase):
    def test_correct_password_verifies(self):
        stored = auth.hash_password("secret1")
        valid, needs_upgrade = auth.verify_password("secret1", stored)
        self.assertTrue(valid)
        self.assertFalse(needs_upgrade)

    def test_wrong_password_rejected(self):
        stored = auth.hash_password("secret1")
        valid, _ = auth.verify_password("wrongpass", stored)
        self.assertFalse(valid)

    def test_plain_text_password_is_flagged_for_upgrade(self):
        valid, needs_upgrade = auth.verify_password("abc123", "abc123")
        self.assertTrue(valid)
        self.assertTrue(needs_upgrade)


class TestRegisterUser(unittest.TestCase):
    @patch("auth.db")  # fake database, so MySQL is not needed
    def test_valid_account_accepted(self, mock_db):
        mock_db.create_user.return_value = 1
        auth.register_user("crizti", "secret1", "secret1")
        mock_db.create_user.assert_called_once()

    def test_short_password_rejected(self):
        with self.assertRaises(auth.AuthError):
            auth.register_user("crizti", "123", "123")

    def test_mismatched_password_rejected(self):
        with self.assertRaises(auth.AuthError):
            auth.register_user("crizti", "secret1", "secret2")

    @patch("auth.db")
    def test_taken_username_rejected(self, mock_db):
        mock_db.create_user.return_value = None
        with self.assertRaises(auth.AuthError):
            auth.register_user("crizti", "secret1", "secret1")


if __name__ == "__main__":
    unittest.main()