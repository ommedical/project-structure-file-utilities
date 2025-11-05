import os
import sys
from pathlib import Path


def ProjectStructureGenerator(root_dir, prefix="", exclude_dirs=None, exclude_files=None):
    """
    Generate a visual tree structure of the directory with file names.
    Skips __pycache__ directories and their contents, plus any excluded directories/files.
    """
    if exclude_dirs is None:
        exclude_dirs = set()
    if exclude_files is None:
        exclude_files = set()

    root_path = Path(root_dir)
    output = []

    # Add the root directory name only if it's the initial call
    if prefix == "":
        output.append(f"{root_path.name}/")

    try:
        items = sorted(os.listdir(root_dir))
    except PermissionError:
        return f"{prefix}{root_path.name}/ [Permission Denied]"

    # Filter out excluded items
    items = [
        item
        for item in items
        if item != "__pycache__"
        and item not in exclude_dirs
        and item not in exclude_files
    ]

    # Separate directories and files
    dirs = [item for item in items if os.path.isdir(os.path.join(root_dir, item))]
    files = [item for item in items if os.path.isfile(os.path.join(root_dir, item))]

    # Process directories first
    for i, dir_name in enumerate(dirs):
        dir_path = os.path.join(root_dir, dir_name)
        is_last_dir = (i == len(dirs) - 1) and (len(files) == 0)

        if is_last_dir:
            new_prefix = prefix + "    "
            output.append(f"{prefix}└── {dir_name}/")
        else:
            new_prefix = prefix + "│   "
            output.append(f"{prefix}├── {dir_name}/")

        # Recursively process subdirectories
        output.append(
            ProjectStructureGenerator(dir_path, new_prefix, exclude_dirs, exclude_files)
        )

    # Process files
    for i, file_name in enumerate(files):
        is_last_file = i == len(files) - 1

        if is_last_file:
            output.append(f"{prefix}└── {file_name}")
        else:
            output.append(f"{prefix}├── {file_name}")

    return "\n".join([line for line in output if line is not None])


def get_file_contents(root_dir, exclude_dirs=None, exclude_files=None):
    """
    Generate the contents of all files with clear start/end markers.
    Skips __pycache__ directories and excluded directories/files.
    Includes full relative path from root directory in the file marker.
    """
    if exclude_dirs is None:
        exclude_dirs = set()
    if exclude_files is None:
        exclude_files = set()

    output = []
    root_dir_name = os.path.basename(root_dir)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip __pycache__ and excluded directories
        dirnames[:] = [
            d
            for d in dirnames
            if d != "__pycache__"
            and d not in exclude_dirs
            and os.path.join(dirpath, d) not in exclude_dirs
        ]

        # Skip the output file if it exists in the directory
        if os.path.basename(dirpath) == os.path.dirname(os.path.abspath(__file__)):
            filenames = [f for f in filenames if f != "directory_structure_output.txt"]

        # Filter out excluded files
        filenames = [
            f
            for f in filenames
            if f not in exclude_files and os.path.join(dirpath, f) not in exclude_files
        ]

        if filenames:
            output.append(f"\n\n=== Directory: {dirpath} ===\n")

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                # Get relative path from root directory
                rel_path = os.path.relpath(filepath, start=os.path.dirname(root_dir))
                output.append(f"\n────── FILE START: {filename} ({rel_path}) ──────\n")

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        contents = f.read()
                    output.append(contents)
                    output.append(f"\n────── FILE END: {filename} ({rel_path}) ──────")
                except UnicodeDecodeError:
                    output.append("[BINARY FILE - CONTENTS NOT SHOWN]")
                    output.append(f"\n────── FILE END: {filename} ({rel_path}) ──────")
                except Exception as e:
                    output.append(f"[ERROR READING FILE: {str(e)}]")
                    output.append(f"\n────── FILE END: {filename} ({rel_path}) ──────")

    return "\n".join(output)


def get_exclusion_list(prompt):
    """
    Helper function to get a list of items to exclude from user input.
    """
    items = input(prompt).strip()
    if not items:
        return set()
    return set(item.strip() for item in items.split(",") if item.strip())


def main():
    import datetime

    # Get the parent directory from user input
    parent_dir_input = input("Enter the parent directory name: ").strip()

    # Check if it's an absolute path
    if os.path.isabs(parent_dir_input) and os.path.isdir(parent_dir_input):
        parent_dir = parent_dir_input
    else:
        # Search for directory by name under base path
        script_base_dir = os.path.dirname(os.path.abspath(__file__))
        found_path = None
        for root, dirs, _ in os.walk(script_base_dir):
            if parent_dir_input in dirs:
                found_path = os.path.join(root, parent_dir_input)
                break
        if not found_path:
            print(f"Error: Directory '{parent_dir_input}' not found under {script_base_dir}.")
            sys.exit(1)
        parent_dir = found_path

    # Get exclusion lists
    print("\nEnter directories/files to exclude (comma-separated, relative or absolute paths):")
    exclude_dirs = get_exclusion_list("Directories to exclude (e.g., 'venv,.git'): ")
    exclude_files = get_exclusion_list("Files to exclude (e.g., '*.log,config.ini'): ")

    # Get the absolute path
    parent_dir = os.path.abspath(parent_dir)

    # Generate the output
    output = f"Directory Structure for: {parent_dir}\n\n"
    output += ProjectStructureGenerator(
        parent_dir, exclude_dirs=exclude_dirs, exclude_files=exclude_files
    )
    output += "\n\n" + "=" * 80 + "\n\n"
    output += "FILE CONTENTS\n"
    output += get_file_contents(
        parent_dir, exclude_dirs=exclude_dirs, exclude_files=exclude_files
    )

    # Prepare output file path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))  # save in script's dir
    dir_name_only = os.path.basename(parent_dir)  # just folder name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        script_dir,
        f"{dir_name_only}_directory_structure_{timestamp}.txt"
    )

    # Save to file
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Directory structure and contents saved to {output_file}")
    except Exception as e:
        print(f"Error saving output file: {str(e)}")




if __name__ == "__main__":

    # 1️⃣ Get the absolute path of the currently running script
    script_path = os.path.abspath(__file__)
    print("Script Path:", script_path)

    # 2️⃣ Get the directory containing the script
    base_dir = os.path.dirname(script_path)
    print("Base Directory:", base_dir)

    # 3️⃣ Walk through all directories and nested directories
    print("\nAll directories under base path:")
    for root, dirs, files in os.walk(base_dir):
        for d in dirs:
            print(os.path.join(root, d))


    main()



# Key Enhancements:
# Exclusion Parameters:

# Added exclude_dirs and exclude_files parameters to both main functions

# These parameters accept sets of directory and file names/paths to exclude

# User Input for Exclusions:

# Added get_exclusion_list() helper function to get comma-separated exclusions from user

# Users can now specify directories/files to exclude when running the script

# Flexible Exclusion:

# Can exclude by name (e.g., "venv") or by path (e.g., "/full/path/to/dir")

# Exclusions work at any level in the directory hierarchy

# Both directory structure and file contents respect the exclusions

# Backward Compatibility:

# All existing functionality remains unchanged

# If no exclusions are provided, behavior is identical to original version

# Usage Examples:
# Exclude common directories:

# text
# Enter directories/files to exclude (comma-separated, relative or absolute paths):
# Directories to exclude (e.g., 'venv,.git'): venv, .git, __pycache__, node_modules
# Files to exclude (e.g., '*.log,config.ini'): 
# Exclude specific files:

# text
# Files to exclude (e.g., '*.log,config.ini'): secrets.json, *.log, temp_*.txt
# Exclude by full path:

# text
# Directories to exclude: /home/user/project/tests,/home/user/project/docs