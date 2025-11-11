"""
Safe patch script for google.adk cli logs.py
- Makes a timestamped backup of the original file
- Inserts a try/except around os.symlink to fallback to shutil.copy2 on failure

Run this from PowerShell (run as admin if you prefer), e.g.:
python .\fix_adk_logs_patch.py

It will print the path it modifies. Inspect the backup before re-running anything.
"""
import io
import os
import shutil
import datetime
import sys
from pathlib import Path

# Path to the installed file (adjust if your Python installation path differs)
target = Path(sys.prefix) / "Lib" / "site-packages" / "google" / "adk" / "cli" / "utils" / "logs.py"
if not target.exists():
    # Try common alternative: user site-packages
    import site
    for p in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = Path(p) / "google" / "adk" / "cli" / "utils" / "logs.py"
        if candidate.exists():
            target = candidate
            break

print("Target file:", target)
if not target.exists():
    print("Could not find logs.py at the expected location. Please open the file path from the traceback and pass it here.")
    sys.exit(1)

# Read file
orig = target.read_text(encoding="utf-8")

# Quick heuristic: if we've already applied the patch, exit
if "fallback to copying the log file" in orig:
    print("Patch appears to already be applied. No changes made.")
    sys.exit(0)

# Ensure shutil is imported near top; add it if missing
if "import shutil" not in orig:
    # place it after other imports (very simple heuristic)
    orig = orig.replace("import os\n", "import os\nimport shutil\n", 1)

# Replace the os.symlink(...) call with a try/except fallback
old_call = "os.symlink(log_filepath, latest_log_link)"
if old_call not in orig:
    print("Could not find the os.symlink call pattern. Please open the file and apply manually. Exiting.")
    sys.exit(1)

new_block = (
    "try:\n"
    "        if os.path.exists(latest_log_link):\n"
    "            os.remove(latest_log_link)\n"
    "        os.symlink(log_filepath, latest_log_link)\n"
    "    except OSError:\n"
    "        # Windows: creating symlinks requires a privilege; fall back to copying the file.\n"
    "        try:\n"
    "            shutil.copy2(log_filepath, latest_log_link)\n"
    "        except Exception:\n"
    "            # Last resort: ignore copying failure to avoid crashing the CLI.\n"
    "            pass\n"
)

new = orig.replace(old_call, new_block, 1)

# Backup
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = target.with_suffix(target.suffix + f".bak_{stamp}")
print(f"Writing backup to: {backup}")
backup.write_text(orig, encoding="utf-8")

# Write patched file
target.write_text(new, encoding="utf-8")
print("Patched logs.py successfully. Please inspect the backup and the modified file before re-running your command.")
print("If you prefer not to modify site-packages, consider running the adk command with Administrator privileges or enable Windows Developer Mode.")
