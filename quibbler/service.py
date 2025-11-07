#!/usr/bin/env python3
"""Service management for Quibbler hook server"""

import os
import sys
import subprocess
from pathlib import Path


def get_plist_path():
    """Get the path to the launchd plist file"""
    return Path.home() / "Library/LaunchAgents/com.quibbler.hookserver.plist"


def get_quibbler_path():
    """Get the path to the quibbler executable"""
    # Use 'which' to find the quibbler executable
    result = subprocess.run(
        ["which", "quibbler"], capture_output=True, text=True, check=False
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def create_plist_content(quibbler_path, port=8081):
    """Create the launchd plist content"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.quibbler.hookserver</string>
    <key>ProgramArguments</key>
    <array>
        <string>{quibbler_path}</string>
        <string>hook</string>
        <string>server</string>
        <string>{port}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.quibbler/hookserver.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.quibbler/hookserver.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}</string>
    </dict>
</dict>
</plist>
"""


def cmd_service_install(args):
    """Install quibbler hook server as a launchd service"""
    port = getattr(args, "port", None) or 8081

    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ Service installation is currently only supported on macOS")
        print("   You can manually start the server with: quibbler hook server")
        return 1

    # Get quibbler path
    quibbler_path = get_quibbler_path()
    if not quibbler_path:
        print("❌ Could not find quibbler executable")
        return 1

    # Create .quibbler directory for logs
    quibbler_dir = Path.home() / ".quibbler"
    quibbler_dir.mkdir(exist_ok=True)

    # Get plist path
    plist_path = get_plist_path()

    # Check if already installed
    if plist_path.exists():
        print(f"⚠️  Service already installed at {plist_path}")
        response = input("   Overwrite? [y/N]: ")
        if response.lower() != "y":
            print("   Cancelled")
            return 0

        # Unload existing service first
        subprocess.run(
            ["launchctl", "unload", str(plist_path)], capture_output=True, check=False
        )

    # Create LaunchAgents directory if it doesn't exist
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Write plist file
    plist_content = create_plist_content(quibbler_path, port)
    plist_path.write_text(plist_content)
    print(f"✓ Created service file at {plist_path}")

    # Load the service
    result = subprocess.run(
        ["launchctl", "load", str(plist_path)], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ Failed to load service: {result.stderr}")
        return 1

    print(f"✓ Quibbler hook server installed and started on port {port}")
    print(f"  Logs: {quibbler_dir}/hookserver.log")
    print(f"  Errors: {quibbler_dir}/hookserver.error.log")
    print()
    print("The service will automatically start on login.")
    print()
    print("To check status: launchctl list | grep quibbler")
    print(f"To uninstall: quibbler service uninstall")

    return 0


def cmd_service_uninstall(args):
    """Uninstall quibbler hook server service"""

    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ Service management is currently only supported on macOS")
        return 1

    plist_path = get_plist_path()

    if not plist_path.exists():
        print("❌ Service is not installed")
        return 1

    # Unload the service
    result = subprocess.run(
        ["launchctl", "unload", str(plist_path)], capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"⚠️  Failed to unload service: {result.stderr}")
        # Continue anyway to remove the plist file

    # Remove the plist file
    plist_path.unlink()
    print(f"✓ Removed service file from {plist_path}")
    print("✓ Quibbler hook server service uninstalled")

    return 0


def cmd_service_status(args):
    """Check status of quibbler hook server service"""

    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ Service management is currently only supported on macOS")
        return 1

    plist_path = get_plist_path()

    if not plist_path.exists():
        print("Service is not installed")
        print(f"To install: quibbler service install")
        return 0

    # Check if service is loaded
    result = subprocess.run(
        ["launchctl", "list"], capture_output=True, text=True, check=False
    )

    if "com.quibbler.hookserver" in result.stdout:
        print("✓ Service is installed and running")

        # Try to get the port from the plist
        plist_content = plist_path.read_text()
        if "8081" in plist_content:
            print("  Port: 8081")
        elif "<string>hook</string>" in plist_content:
            # Extract port from plist
            lines = plist_content.split("\n")
            for i, line in enumerate(lines):
                if "<string>server</string>" in line and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith("<string>") and next_line.endswith(
                        "</string>"
                    ):
                        port = next_line.replace("<string>", "").replace("</string>", "")
                        print(f"  Port: {port}")
                        break

        # Show log locations
        quibbler_dir = Path.home() / ".quibbler"
        print(f"  Logs: {quibbler_dir}/hookserver.log")
        print(f"  Errors: {quibbler_dir}/hookserver.error.log")
    else:
        print("⚠️  Service is installed but not running")
        print(f"   To start: launchctl load {plist_path}")

    return 0
