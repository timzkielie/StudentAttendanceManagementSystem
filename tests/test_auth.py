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

    def test_password_must_be_ascii_alphanumeric(self):
        for password in ("hello@123", "student#1", "hello 123", "１２３４５６"):
            with self.subTest(password=password):
                with self.assertRaises(auth.AuthError):
                    auth.register_user("crizti", password, password)

    def test_blank_password_has_specific_error(self):
        with self.assertRaisesRegex(auth.AuthError, "^Password is required\\.$"):
            auth.register_user("crizti", "", "")

    def test_short_password_has_specific_error(self):
        with self.assertRaisesRegex(
            auth.AuthError, "^Password must be at least 6 characters long\\.$"
        ):
            auth.register_user("crizti", "abc12", "abc12")

    def test_special_character_has_specific_error(self):
        with self.assertRaisesRegex(
            auth.AuthError,
            "^Password must contain letters and numbers only\\. "
            "Special characters are not allowed\\.$",
        ):
            auth.register_user("crizti", "hello@123", "hello@123")

    @patch("auth.db")
    def test_password_with_letters_and_numbers_is_accepted(self, mock_db):
        mock_db.create_user.return_value = 1
        auth.register_user("crizti", "attend2026", "attend2026")
        mock_db.create_user.assert_called_once()

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