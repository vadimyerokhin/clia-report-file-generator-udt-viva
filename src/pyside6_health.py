#!/usr/bin/env python3
"""PySide6 health check and auto-repair functionality.

This module detects corrupted PySide6 installations and automatically repairs them
across different platforms (macOS, Linux, Windows). It checks for the presence of
critical Qt modules and reinstalls if corruption is detected.

Usage:
    from src.pyside6_health import check_and_repair_pyside6

    # Returns True if healthy or successfully repaired, False if repair failed
    if not check_and_repair_pyside6():
        sys.exit(1)
"""
import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PySide6HealthChecker:
    """Health checker and auto-repair for PySide6 installations."""

    # Critical modules that must be present
    CRITICAL_MODULES = [
        'QtCore',
        'QtGui',
        'QtWidgets'
    ]

    def __init__(self, silent: bool = False):
        """Initialize health checker.

        Args:
            silent: If True, suppress console output (only log)
        """
        self.silent = silent
        self.platform = platform.system()
        self.python_executable = sys.executable

    def _print(self, message: str, level: str = "info"):
        """Print message to console if not silent."""
        if not self.silent:
            print(message)

        # Always log
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)

    def _get_package_manager(self) -> Tuple[str, list]:
        """Detect package manager and return command prefix.

        Returns:
            Tuple of (manager_name, command_prefix_list)
        """
        # Check if we're in a uv-managed environment
        if os.environ.get('VIRTUAL_ENV') and Path('.venv').exists():
            # Check if uv is available
            try:
                result = subprocess.run(
                    ['uv', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return ('uv', ['uv', 'pip'])
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        # Fall back to standard pip
        return ('pip', [self.python_executable, '-m', 'pip'])

    def _find_site_packages(self) -> Optional[Path]:
        """Find the site-packages directory for current Python environment.

        Returns:
            Path to site-packages or None if not found
        """
        try:
            import site
            site_packages = site.getsitepackages()
            if site_packages:
                return Path(site_packages[0])
        except Exception as e:
            logger.error(f"Failed to find site-packages: {e}")

        return None

    def _check_pyside6_files(self) -> bool:
        """Check if critical PySide6 module files exist.

        Returns:
            True if all critical files present, False otherwise
        """
        site_packages = self._find_site_packages()
        if not site_packages:
            return False

        pyside6_dir = site_packages / "PySide6"
        if not pyside6_dir.exists():
            self._print("⚠️  PySide6 directory not found", "warning")
            return False

        # Platform-specific extension for compiled modules
        if self.platform == "Windows":
            module_ext = ".pyd"
        else:
            module_ext = ".abi3.so"

        missing_modules = []
        for module in self.CRITICAL_MODULES:
            module_file = pyside6_dir / f"{module}{module_ext}"
            if not module_file.exists():
                missing_modules.append(module)

        if missing_modules:
            self._print(
                f"⚠️  Missing PySide6 modules: {', '.join(missing_modules)}",
                "warning"
            )
            return False

        return True

    def _can_import_pyside6(self) -> bool:
        """Test if PySide6 can be imported successfully.

        Returns:
            True if import succeeds, False otherwise
        """
        try:
            # Test import in a subprocess to avoid polluting current environment
            result = subprocess.run(
                [
                    self.python_executable,
                    '-c',
                    'from PySide6.QtCore import QThread, Signal; '
                    'from PySide6.QtWidgets import QApplication'
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Import test failed: {e}")
            return False

    def check_health(self) -> bool:
        """Check PySide6 installation health.

        Returns:
            True if healthy, False if corrupted or missing
        """
        self._print("🔍 Checking PySide6 installation health...")

        # Check 1: Files exist
        if not self._check_pyside6_files():
            self._print("❌ PySide6 files check failed", "error")
            return False

        # Check 2: Can import
        if not self._can_import_pyside6():
            self._print("❌ PySide6 import check failed", "error")
            return False

        self._print("✅ PySide6 installation is healthy")
        return True

    def _clean_corrupted_files(self) -> bool:
        """Remove corrupted PySide6 files and metadata.

        Returns:
            True if cleaning succeeded, False otherwise
        """
        site_packages = self._find_site_packages()
        if not site_packages:
            return False

        try:
            # Remove PySide6 directories
            for pattern in ['PySide6*', 'pyside6*', 'shiboken6*']:
                for path in site_packages.glob(pattern):
                    if path.is_dir():
                        import shutil
                        self._print(f"🧹 Removing {path.name}")
                        shutil.rmtree(path, ignore_errors=True)
                    elif path.is_file():
                        path.unlink(missing_ok=True)

            return True
        except Exception as e:
            logger.error(f"Failed to clean corrupted files: {e}")
            return False

    def repair(self) -> bool:
        """Repair corrupted PySide6 installation.

        Returns:
            True if repair succeeded, False otherwise
        """
        self._print("🔧 Starting PySide6 repair...")

        manager_name, cmd_prefix = self._get_package_manager()
        self._print(f"📦 Using package manager: {manager_name}")

        try:
            # Step 1: Uninstall existing packages
            self._print("1️⃣  Uninstalling corrupted packages...")
            uninstall_cmd = cmd_prefix + [
                'uninstall',
                'pyside6',
                'pyside6-essentials',
                'pyside6-addons',
                'shiboken6'
            ]

            result = subprocess.run(
                uninstall_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # Uninstall might fail if packages not found - that's OK
                logger.warning(f"Uninstall had warnings: {result.stderr}")

            # Step 2: Clean up leftover files
            self._print("2️⃣  Cleaning leftover files...")
            self._clean_corrupted_files()

            # Step 3: Reinstall fresh
            self._print("3️⃣  Reinstalling PySide6 (this may take a minute)...")
            install_cmd = cmd_prefix + ['install', 'pyside6>=6.10.0']

            # Add reinstall and no-cache flags for uv
            if manager_name == 'uv':
                install_cmd.extend(['--reinstall', '--no-cache'])
            else:
                # For pip, use --force-reinstall
                install_cmd.append('--force-reinstall')

            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for download
            )

            if result.returncode != 0:
                self._print(f"❌ Installation failed: {result.stderr}", "error")
                return False

            # Step 4: Verify repair
            self._print("4️⃣  Verifying repair...")
            if self._can_import_pyside6():
                self._print("✅ PySide6 repair successful!")
                return True
            else:
                self._print("❌ Repair verification failed", "error")
                return False

        except subprocess.TimeoutExpired:
            self._print("❌ Repair timed out", "error")
            return False
        except Exception as e:
            self._print(f"❌ Repair failed: {e}", "error")
            logger.exception("Repair exception details:")
            return False

    def check_and_repair(self, auto_repair: bool = True) -> bool:
        """Check health and optionally auto-repair if needed.

        Args:
            auto_repair: If True, automatically repair if unhealthy

        Returns:
            True if healthy or successfully repaired, False otherwise
        """
        if self.check_health():
            return True

        if not auto_repair:
            self._print(
                "❌ PySide6 installation is corrupted. Run with auto_repair=True to fix.",
                "error"
            )
            return False

        self._print("\n⚕️  Corrupted PySide6 installation detected. Attempting auto-repair...")
        return self.repair()


def check_and_repair_pyside6(silent: bool = False, auto_repair: bool = True) -> bool:
    """Convenience function to check and repair PySide6.

    Args:
        silent: If True, suppress console output (only log)
        auto_repair: If True, automatically repair if corrupted

    Returns:
        True if healthy or successfully repaired, False otherwise

    Example:
        if not check_and_repair_pyside6():
            print("Failed to repair PySide6. Please reinstall manually.")
            sys.exit(1)
    """
    checker = PySide6HealthChecker(silent=silent)
    return checker.check_and_repair(auto_repair=auto_repair)


if __name__ == '__main__':
    # CLI usage for manual checks
    import argparse

    parser = argparse.ArgumentParser(
        description='Check and repair PySide6 installation'
    )
    parser.add_argument(
        '--no-repair',
        action='store_true',
        help='Check only, do not auto-repair'
    )
    parser.add_argument(
        '--silent',
        action='store_true',
        help='Silent mode (log only, no console output)'
    )

    args = parser.parse_args()

    success = check_and_repair_pyside6(
        silent=args.silent,
        auto_repair=not args.no_repair
    )

    sys.exit(0 if success else 1)
