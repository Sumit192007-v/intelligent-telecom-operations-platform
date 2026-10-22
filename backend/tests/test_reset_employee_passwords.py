"""
Isolated unit tests for reset_employee_passwords safety guards and failure recovery.
Runs strictly against mocks and isolated temporary directories—never against the real database.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from reset_employee_passwords import (
    ROLE_PASSWORD_MAP,
    UncertainCommitError,
    execute_database_update,
    get_role_based_password,
    handle_existing_credentials_files,
    promote_credentials_file,
    verify_git_protection,
    verify_local_database_target,
    verify_transactional_storage_engine,
)


def test_remote_host_aborts_immediately():
    """Verify that a non-local database host triggers an immediate safety abort."""
    with pytest.raises(RuntimeError, match="Safety guard triggered: Refusing to run on non-local host"):
        verify_local_database_target(host="db.production.telecom.com")


def test_pre_existing_temp_file_stops_without_modifications(tmp_path):
    """
    If employee_test_credentials.txt.tmp already exists, the script must STOP
    immediately without deleting, overwriting, or touching anything.
    """
    final_file = tmp_path / "employee_test_credentials.txt"
    temp_file = tmp_path / "employee_test_credentials.txt.tmp"
    temp_file.write_text("ORPHANED_CREDENTIALS_DATA", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        handle_existing_credentials_files(root_dir=tmp_path, final_file=final_file, temp_file=temp_file)

    assert "An orphaned temporary credentials file was detected" in str(exc_info.value)
    assert str(temp_file.resolve()) in str(exc_info.value)
    # Ensure orphaned file is preserved intact
    assert temp_file.exists()
    assert temp_file.read_text(encoding="utf-8") == "ORPHANED_CREDENTIALS_DATA"


def test_backup_filename_collision_avoided(tmp_path):
    """
    If employee_test_credentials.txt exists and an existing backup has the same timestamp,
    a collision-free incremented filename must be used instead of overwriting the prior backup.
    """
    final_file = tmp_path / "employee_test_credentials.txt"
    final_file.write_text("INITIAL_CREDENTIALS", encoding="utf-8")
    temp_file = tmp_path / "employee_test_credentials.txt.tmp"

    # Pre-create a collision file
    with patch("reset_employee_passwords.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "20261022_120000_000000"
        colliding_backup = tmp_path / "employee_test_credentials.txt.bak.20261022_120000_000000"
        colliding_backup.write_text("PREVIOUS_BACKUP_CONTENT", encoding="utf-8")

        handle_existing_credentials_files(root_dir=tmp_path, final_file=final_file, temp_file=temp_file)

        # Assert prior backup was NOT overwritten
        assert colliding_backup.read_text(encoding="utf-8") == "PREVIOUS_BACKUP_CONTENT"

        # Assert new backup was created with counter
        expected_new_backup = tmp_path / "employee_test_credentials.txt.bak.20261022_120000_000000_1"
        assert expected_new_backup.exists()
        assert expected_new_backup.read_text(encoding="utf-8") == "INITIAL_CREDENTIALS"


def test_database_update_failure_before_commit_rolls_back_and_cleans_staging(tmp_path):
    """
    If a failure occurs during the update loop before commit,
    db.rollback() must be called and the staging file must be cleaned up.
    """
    temp_file = tmp_path / "employee_test_credentials.txt.tmp"
    temp_file.write_text("TEMP_DATA", encoding="utf-8")

    mock_db = MagicMock()
    # Bad update entry that raises an exception
    mock_user = MagicMock()
    type(mock_user).password_hash = property(
        fget=lambda self: "old_hash",
        fset=MagicMock(side_effect=Exception("Disk error on property set"))
    )

    updates = [(mock_user, "new_hash")]

    with pytest.raises(RuntimeError, match="Database update failed before commit"):
        execute_database_update(mock_db, updates, temp_file)

    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()
    assert not temp_file.exists()


def test_uncertain_commit_failure_preserves_staged_credentials(tmp_path):
    """
    CRITICAL: If db.commit() raises an exception, the commit status is UNCERTAIN.
    db.rollback() must be called, but temp_file must NOT be deleted.
    """
    temp_file = tmp_path / "employee_test_credentials.txt.tmp"
    temp_file.write_text("VALUABLE_NEW_PASSWORDS", encoding="utf-8")

    mock_db = MagicMock()
    mock_user = MagicMock()
    updates = [(mock_user, "new_hash")]

    # Simulate connection drop / timeout during commit
    mock_db.commit.side_effect = Exception("Lost connection to MySQL server during query")

    with pytest.raises(UncertainCommitError) as exc_info:
        execute_database_update(mock_db, updates, temp_file)

    assert "The commit status is UNCERTAIN" in str(exc_info.value)
    assert "temporary credentials file HAS BEEN PRESERVED" in str(exc_info.value)
    mock_db.rollback.assert_called_once()

    # The staged credentials file MUST still exist!
    assert temp_file.exists()
    assert temp_file.read_text(encoding="utf-8") == "VALUABLE_NEW_PASSWORDS"


def test_file_promotion_failure_preserves_temp_file_and_reports_recovery(tmp_path):
    """
    If os.replace and fallback copy both fail (e.g. file lock),
    promote_credentials_file must return False and preserve temp_file.
    """
    temp_file = tmp_path / "employee_test_credentials.txt.tmp"
    temp_file.write_text("PASSWORD_DATA", encoding="utf-8")
    final_file = tmp_path / "employee_test_credentials.txt"

    with patch("os.replace", side_effect=PermissionError("File locked by external process")):
        with patch("shutil.copy2", side_effect=PermissionError("File locked by external process")):
            success, err = promote_credentials_file(temp_file, final_file)

            assert success is False
            assert "os.replace error" in err
            # Staged file must still be intact
            assert temp_file.exists()
            assert temp_file.read_text(encoding="utf-8") == "PASSWORD_DATA"


def test_non_innodb_storage_engine_triggers_abort():
    """Verify that a non-transactional storage engine (e.g. MyISAM) aborts execution."""
    mock_db = MagicMock()
    mock_db.get_bind.return_value.dialect.name = "mysql"
    mock_db.execute.return_value.scalar.return_value = "MyISAM"

    with pytest.raises(RuntimeError, match="Safety guard triggered: 'users' table engine is 'MyISAM', expected 'InnoDB'"):
        verify_transactional_storage_engine(mock_db, "telecom_operations")


def test_role_based_password_format_matches_requirements():
    """Verify that every employee role generates the exact required NetPulseRole!2026 password."""
    expected_passwords = {
        "engineer": "NetPulseEngineer!2026",
        "support_agent": "NetPulseSupport!2026",
        "manager": "NetPulseManager!2026",
        "staff": "NetPulseStaff!2026",
        "admin": "NetPulseAdmin!2026",
    }
    assert ROLE_PASSWORD_MAP == expected_passwords

    for role, expected_pwd in expected_passwords.items():
        assert get_role_based_password(role) == expected_pwd

    with pytest.raises(ValueError, match="No role-based password defined for role"):
        get_role_based_password("customer")

    with pytest.raises(ValueError, match="No role-based password defined for role"):
        get_role_based_password("unauthorized_role")
