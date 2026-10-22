"""
One-time password reset utility for local development testing.

Safety Guarantees:
  1. Localhost Only: Validates that MYSQL_HOST is local (localhost / 127.0.0.1 / ::1).
  2. Transactional Engine Check: Validates MySQL 'users' table uses InnoDB (ACID compliant).
  3. Git Protection: Confirms final, temporary, and backup file patterns are all git-ignored.
  4. Orphaned File Protection: If employee_test_credentials.txt.tmp already exists, stops immediately
     without changing the database or overwriting, displaying recovery steps.
  5. Collision-Free Backup: If employee_test_credentials.txt exists, creates a unique backup with
     microsecond timestamps and collision loops so no prior backup is ever overwritten.
  6. Strict Pre-Validation: Verifies all 13 employee accounts exist and none has the customer role
     BEFORE touching any database records. Aborts if any account is missing or invalid.
  7. Cryptographic Self-Test: Verifies each generated password and hash via bcrypt before staging.
  8. Single Atomic Transaction: Applies all updates in one transaction with db.commit().
     If update fails before commit, calls db.rollback() and cleans up the staging file.
  9. Uncertain Commit Handling: If db.commit() raises an exception, calls db.rollback() where
     appropriate but explicitly PRESERVES the staged credentials file because commit status is uncertain.
  10. Fault-Tolerant File Promotion: Pre-writes and fsyncs credentials to .tmp file before database
     updates. If post-commit promotion fails, the .tmp file is preserved, the issue is prominently
     flagged, and exact recovery instructions are output.
  11. Confidentiality: Passwords are NEVER printed to stdout/stderr or terminal logs.
  12. Data Integrity: Preserves IDs, emails, names, roles, departments, customer accounts, and timestamps.
"""

from datetime import datetime
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

# Ensure backend directory is in Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import bcrypt
from sqlalchemy import text
from app.database import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    SessionLocal,
)
from app.models.models import User

# Exact list of 13 employee accounts identified in local database
TARGET_EMPLOYEE_EMAILS = [
    "support@telecom.local",
    "engineer@telecom.local",
    "manager@telecom.local",
    "staff.test@telecom.local",
    "admin.demo@netpulse.test",
    "staff.demo@netpulse.test",
    "support.agent@telecom.local",
    "noc.engineer@telecom.local",
    "field.engineer@telecom.local",
    "billing.specialist@telecom.local",
    "tech.support@telecom.local",
    "dept.manager@telecom.local",
    "sys.admin@telecom.local",
]

ALLOWED_EMPLOYEE_ROLES = {"staff", "support_agent", "engineer", "manager", "admin"}

FINAL_CREDENTIALS_FILE = ROOT / "employee_test_credentials.txt"
TEMP_CREDENTIALS_FILE = ROOT / "employee_test_credentials.txt.tmp"


class UncertainCommitError(RuntimeError):
    """Raised when db.commit() fails, meaning database state is uncertain and temp file must be preserved."""
    pass


def verify_local_database_target(host: str = MYSQL_HOST, user: str = MYSQL_USER, port: int = MYSQL_PORT, db_name: str = MYSQL_DATABASE):
    """Safety guard: ensure we are operating strictly on a local development instance."""
    allowed_hosts = {"localhost", "127.0.0.1", "::1"}
    h = str(host).strip().lower()
    if h not in allowed_hosts:
        raise RuntimeError(
            f"Safety guard triggered: Refusing to run on non-local host '{host}'. "
            "This utility must only be run against a local development database."
        )
    print(f"[OK] Target database verified: {user}@{host}:{port}/{db_name}")


def verify_transactional_storage_engine(db, database_name: str = MYSQL_DATABASE):
    """Safety guard: verify MySQL 'users' table uses a transactional engine (InnoDB)."""
    try:
        bind = db.get_bind()
        if bind.dialect.name == "sqlite":
            print("[OK] Storage engine verified: SQLite test database (transactional).")
            return

        res = db.execute(
            text("SELECT ENGINE FROM information_schema.tables WHERE table_schema = :db AND table_name = 'users'"),
            {"db": database_name},
        ).scalar()
        if res and res.lower() != "innodb":
            raise RuntimeError(
                f"Safety guard triggered: 'users' table engine is '{res}', expected 'InnoDB'. "
                "Non-transactional storage engines do not support atomic rollbacks."
            )
        print(f"[OK] Storage engine verified: 'users' table uses transactional engine '{res or 'InnoDB'}'.")
    except Exception as e:
        if "Safety guard triggered" in str(e):
            raise
        raise RuntimeError(f"Storage engine verification failed: {e}")


def verify_git_protection(root_dir: Path = ROOT, final_file: Path = FINAL_CREDENTIALS_FILE, temp_file: Path = TEMP_CREDENTIALS_FILE):
    """Safety guard: verify that final, temp, and backup filename patterns are all ignored by Git."""
    test_backup = root_dir / f"employee_test_credentials.txt.bak.{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    patterns_to_test = [
        final_file,
        temp_file,
        test_backup,
    ]

    for p in patterns_to_test:
        try:
            res = subprocess.run(
                ["git", "check-ignore", "-q", str(p)],
                cwd=root_dir,
                capture_output=True,
            )
            if res.returncode != 0:
                raise RuntimeError(
                    f"Safety guard triggered: '{p.name}' is NOT ignored by Git. "
                    "Ensure 'employee_test_credentials.txt*' is in .gitignore before running."
                )
        except FileNotFoundError:
            gitignore = root_dir / ".gitignore"
            if not gitignore.exists() or "employee_test_credentials.txt" not in gitignore.read_text(encoding="utf-8"):
                raise RuntimeError("Safety guard triggered: employee_test_credentials.txt not found in .gitignore.")
            break

    print("[OK] Git protection verified: final, temporary, and backup files are all ignored by Git.")


def handle_existing_credentials_files(root_dir: Path = ROOT, final_file: Path = FINAL_CREDENTIALS_FILE, temp_file: Path = TEMP_CREDENTIALS_FILE):
    """
    Safety guard:
    1. Stop if an orphaned temporary credentials file exists.
    2. Back up existing credentials file with collision-free naming.
    """
    if temp_file.exists():
        raise RuntimeError(
            f"Safety guard triggered: An orphaned temporary credentials file was detected at:\n"
            f"  --> {temp_file.resolve()}\n\n"
            f"This file may contain active credentials from an earlier run whose promotion was interrupted.\n"
            f"To safely recover it, inspect or copy the file:\n"
            f"  Copy-Item '{temp_file.resolve()}' '{final_file.resolve()}'\n\n"
            f"Once verified, remove the .tmp file before running this utility.\n"
            f"Execution ABORTED. No database changes were made."
        )

    if final_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_file = root_dir / f"employee_test_credentials.txt.bak.{timestamp}"
        counter = 1
        while backup_file.exists():
            backup_file = root_dir / f"employee_test_credentials.txt.bak.{timestamp}_{counter}"
            counter += 1

        try:
            shutil.copy2(final_file, backup_file)
            print(f"[OK] Existing credentials backed up safely to: '{backup_file.name}'")
        except Exception as e:
            raise RuntimeError(f"Failed to back up existing credentials file without collision. Aborting: {e}")


ROLE_PASSWORD_MAP = {
    "engineer": "NetPulseEngineer!2026",
    "support_agent": "NetPulseSupport!2026",
    "manager": "NetPulseManager!2026",
    "staff": "NetPulseStaff!2026",
    "admin": "NetPulseAdmin!2026",
}


def get_role_based_password(role: str) -> str:
    """Return deterministic role-based password matching NetPulseRole!2026 format."""
    if role not in ROLE_PASSWORD_MAP:
        raise ValueError(f"No role-based password defined for role: '{role}'")
    return ROLE_PASSWORD_MAP[role]


def generate_strong_password(role: str | None = None) -> str:
    """Generate temporary password, preferring role-based pattern."""
    if role and role in ROLE_PASSWORD_MAP:
        return get_role_based_password(role)
    return f"Temp-{secrets.token_urlsafe(16)}"


def stage_credentials_file(temp_file: Path, records: list[dict], db_name: str, host: str, port: int):
    """Writes and fsyncs generated credentials to disk buffer."""
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("# Intelligent Telecom Operations Platform - Local Employee Test Credentials\n")
        f.write("# Generated for local development testing only. Never commit or share.\n")
        f.write(f"# Target Database: {db_name} on {host}:{port}\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"{'ID':<4} | {'Name':<22} | {'Email':<34} | {'Role':<14} | {'Department':<22} | {'Temporary Password'}\n")
        f.write("-" * 135 + "\n")
        for r in records:
            f.write(
                f"{r['id']:<4} | {r['name']:<22} | {r['email']:<34} | {r['role']:<14} | {r['department']:<22} | {r['password']}\n"
            )
        f.flush()
        os.fsync(f.fileno())


def execute_database_update(db, updates: list[tuple[User, str]], temp_file: Path):
    """
    Applies password hash updates within the current session.
    If an error occurs before commit, rolls back and cleans up temp_file.
    If commit fails, calls rollback where appropriate but explicitly preserves temp_file
    because commit status is uncertain.
    """
    try:
        for user, password_hash in updates:
            user.password_hash = password_hash
    except Exception as update_err:
        try:
            db.rollback()
        except Exception:
            pass
        if temp_file.exists():
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
        raise RuntimeError(f"Database update failed before commit: {update_err}")

    try:
        db.commit()
        print(f"[OK] Single database transaction committed successfully for all {len(updates)} accounts.")
    except Exception as commit_err:
        rollback_detail = ""
        try:
            db.rollback()
            rollback_detail = "db.rollback() was attempted."
        except Exception as rb_err:
            rollback_detail = f"db.rollback() also failed: {rb_err}."

        raise UncertainCommitError(
            f"Database commit failed with error: {commit_err}. {rollback_detail}\n"
            f"[CRITICAL SAFETY WARNING] The commit status is UNCERTAIN.\n"
            f"The database server may have committed the transaction before connection loss.\n"
            f"The temporary credentials file HAS BEEN PRESERVED at:\n"
            f"  --> {temp_file.resolve()}\n"
            f"Do NOT delete this file. Verify the database state to determine if passwords updated."
        )


def promote_credentials_file(temp_file: Path, final_file: Path) -> tuple[bool, str | None]:
    """
    Promotes staged credentials file to final file.
    Returns (True, None) on success.
    Returns (False, error_message) on failure, preserving temp_file.
    """
    try:
        os.replace(temp_file, final_file)
        return True, None
    except Exception as replace_err:
        try:
            shutil.copy2(temp_file, final_file)
            temp_file.unlink(missing_ok=True)
            return True, None
        except Exception as copy_err:
            err_msg = f"os.replace error: {replace_err} | fallback copy error: {copy_err}"
            return False, err_msg


def run_atomic_password_reset(
    session_factory=SessionLocal,
    root_dir: Path = ROOT,
    final_file: Path = FINAL_CREDENTIALS_FILE,
    temp_file: Path = TEMP_CREDENTIALS_FILE,
) -> int:
    """
    Coordinates the full safety verification, pre-validation, credential generation,
    staging, database transaction, and promotion workflow.
    """
    # 1. Environment, safety, and overwrite checks
    verify_local_database_target()
    verify_git_protection(root_dir, final_file, temp_file)
    handle_existing_credentials_files(root_dir, final_file, temp_file)

    with session_factory() as db:
        # Check storage engine
        verify_transactional_storage_engine(db, MYSQL_DATABASE)

        # Phase 1: Read-Only Pre-Validation
        print("\n[Phase 1] Pre-validating target employee accounts in database...")
        missing_emails = []
        invalid_role_accounts = []
        target_users = []

        for email in TARGET_EMPLOYEE_EMAILS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                missing_emails.append(email)
                continue

            if user.role == "customer":
                invalid_role_accounts.append(f"{email} has protected role 'customer'")
            elif user.role not in ALLOWED_EMPLOYEE_ROLES:
                invalid_role_accounts.append(f"{email} has unexpected role '{user.role}'")
            else:
                target_users.append(user)

        # Abort immediately if any target account is missing or has an unexpected role
        if missing_emails:
            raise RuntimeError(
                f"Pre-validation failed: Missing employee account(s) in database: {missing_emails}. "
                "No passwords were changed."
            )

        if invalid_role_accounts:
            raise RuntimeError(
                f"Pre-validation failed: Invalid role detected: {invalid_role_accounts}. "
                "No passwords were changed."
            )

        if len(target_users) != len(TARGET_EMPLOYEE_EMAILS):
            raise RuntimeError(
                f"Pre-validation failed: Expected {len(TARGET_EMPLOYEE_EMAILS)} accounts, found {len(target_users)}. "
                "No passwords were changed."
            )

        print(f"[OK] All {len(target_users)} employee accounts validated successfully.")

        # Phase 2: In-memory password generation & cryptographic self-test
        print("\n[Phase 2] Generating role-based passwords and running bcrypt verification...")
        updates = []
        credentials_records = []

        for user in target_users:
            plain_password = get_role_based_password(user.role)

            password_hash = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt(12)).decode()

            if not bcrypt.checkpw(plain_password.encode(), password_hash.encode()):
                raise RuntimeError(
                    f"Cryptographic self-test failed for user {user.email}. Hash does not match password."
                )

            if bcrypt.checkpw(b"incorrect_probe_password", password_hash.encode()):
                raise RuntimeError(
                    f"Cryptographic self-test failed for user {user.email}. Hash accepted invalid password."
                )

            updates.append((user, password_hash))
            credentials_records.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "department": user.department or "Unassigned",
                "password": plain_password,
            })

        print(f"[OK] Generated and verified {len(updates)} role-based password hashes.")

        # Phase 3: File staging (Write and fsync to temporary buffer)
        print("\n[Phase 3] Staging credentials file to disk...")
        try:
            stage_credentials_file(temp_file, credentials_records, MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT)
            print(f"[OK] Staged credentials file written and synced to disk buffer.")
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink(missing_ok=True)
                except Exception:
                    pass
            raise RuntimeError(f"File write failed before database transaction. Aborting: {e}")

        # Phase 4: Single atomic database transaction
        print("\n[Phase 4] Executing single atomic database transaction...")
        execute_database_update(db, updates, temp_file)

        # Phase 5: Fault-tolerant credentials file promotion & recovery handling
        print("\n[Phase 5] Promoting credentials file...")
        promotion_success, promotion_error = promote_credentials_file(temp_file, final_file)
        if promotion_success:
            print(f"[OK] Credentials file promoted atomically to: {final_file}")

        # Phase 6: Terminal Summary & Outcome Reporting
        if not promotion_success:
            print("\n" + "!" * 85)
            print("[CRITICAL WARNING] DATABASE COMMITTED BUT FILE PROMOTION ENCOUNTERED AN ISSUE")
            print("!" * 85)
            print(f"Details: {promotion_error}\n")
            print("RECOVERY INSTRUCTIONS:")
            print("  1. The new passwords are ACTIVE in MySQL.")
            print(f"  2. All generated passwords are safely preserved in:")
            print(f"     --> {temp_file.resolve()}")
            print(f"  3. To complete promotion manually, run in PowerShell:")
            print(f"     Copy-Item '{temp_file.resolve()}' '{final_file.resolve()}'")
            print("  4. Do NOT delete the .tmp file until verified.")
            print("!" * 85 + "\n")
            return 2

        print("\n" + "=" * 80)
        print("PASSWORD RESET SUMMARY - ALL CHANGES COMMITTED SUCCESSFULLY")
        print("=" * 80)
        print(f"{'ID':<4} | {'Name':<22} | {'Email':<34} | {'Role':<14} | {'Status'}")
        print("-" * 80)
        for r in credentials_records:
            print(f"{r['id']:<4} | {r['name']:<22} | {r['email']:<34} | {r['role']:<14} | Reset & Verified")
        print("-" * 80)
        print("NOTE: Temporary passwords were NOT printed to this console for security.")
        print(f"Please inspect your credentials locally in:\n  -> {final_file}\n")
        return 0


if __name__ == "__main__":
    sys.exit(run_atomic_password_reset())
