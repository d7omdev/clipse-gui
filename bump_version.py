#!/usr/bin/env python3
"""
Version bump script for Clipse GUI
Updates version in __init__.py and Makefile desktop entry
"""

import re
import sys
from pathlib import Path


def get_current_version():
    """Get the current version from __init__.py"""
    init_file = Path("clipse_gui/__init__.py")
    if not init_file.exists():
        print("Error: clipse_gui/__init__.py not found")
        sys.exit(1)
    
    content = init_file.read_text()
    match = re.search(r'__version__ = "([^"]+)"', content)
    if not match:
        print("Error: Could not find version in __init__.py")
        sys.exit(1)
    
    return match.group(1)


def parse_version(version_str):
    """Parse version string into major, minor, patch components"""
    try:
        parts = version_str.split('.')
        if len(parts) != 3:
            raise ValueError("Version must have 3 parts")
        return [int(part) for part in parts]
    except ValueError as e:
        print(f"Error parsing version '{version_str}': {e}")
        sys.exit(1)


def bump_version(current_version, bump_type):
    """Bump version based on type (major, minor, patch)"""
    major, minor, patch = parse_version(current_version)
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        print(f"Error: Invalid bump type '{bump_type}'. Use major, minor, or patch")
        sys.exit(1)
    
    return f"{major}.{minor}.{patch}"


def update_init_file(new_version):
    """Update version in __init__.py"""
    init_file = Path("clipse_gui/__init__.py")
    content = init_file.read_text()
    
    new_content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    
    init_file.write_text(new_content)
    print(f"Updated clipse_gui/__init__.py to version {new_version}")


def update_makefile(new_version):
    """Update version in Makefile desktop entry"""
    makefile = Path("Makefile")
    if not makefile.exists():
        print("Warning: Makefile not found, skipping desktop entry version update")
        return
    
    content = makefile.read_text()
    
    new_content = re.sub(
        r'"Version=[^"]*"',
        f'"Version={new_version}"',
        content
    )
    
    makefile.write_text(new_content)
    print(f"Updated Makefile desktop entry to version {new_version}")


def interactive_bump():
    """Interactive version bump with user selection"""
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    print()
    
    # Show what each bump type would result in
    major_version = bump_version(current_version, "major")
    minor_version = bump_version(current_version, "minor")
    patch_version = bump_version(current_version, "patch")
    
    print("Select bump type:")
    print(f"1. Major: {current_version} → {major_version}")
    print(f"2. Minor: {current_version} → {minor_version}")
    print(f"3. Patch: {current_version} → {patch_version}")
    print("4. Cancel")
    print()
    
    while True:
        try:
            choice = input("Enter choice (1-4): ").strip()
            if choice == "1":
                return "major", major_version
            elif choice == "2":
                return "minor", minor_version
            elif choice == "3":
                return "patch", patch_version
            elif choice == "4":
                print("Cancelled")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
        except KeyboardInterrupt:
            print("\nCancelled")
            sys.exit(0)


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Non-interactive mode with command line argument
        bump_type = sys.argv[1].lower()
        if bump_type not in ["major", "minor", "patch"]:
            print("Usage: python bump_version.py [major|minor|patch]")
            print("Or run without arguments for interactive mode")
            sys.exit(1)
        
        current_version = get_current_version()
        new_version = bump_version(current_version, bump_type)
        print(f"Bumping {bump_type} version: {current_version} → {new_version}")
    else:
        # Interactive mode
        bump_type, new_version = interactive_bump()
        print(f"Bumping {bump_type} version to {new_version}")
    
    # Confirm the change
    confirm = input(f"Proceed with version bump? (y/N): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Cancelled")
        sys.exit(0)
    
    # Update files
    update_init_file(new_version)
    update_makefile(new_version)
    
    print(f"Version successfully bumped to {new_version}")
    print("Don't forget to commit the changes!")


if __name__ == "__main__":
    main()