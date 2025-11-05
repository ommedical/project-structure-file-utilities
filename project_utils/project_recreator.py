import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import logging

class ProjectRecreator:
    def __init__(self, source_file_path: str):
        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Make source file path absolute if it's relative
        if not os.path.isabs(source_file_path):
            source_file_path = os.path.join(self.script_dir, source_file_path)
            
        self.source_file_path = source_file_path
        self.project_structure = {}
        self.file_contents = {}
        self.root_directory = ""
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for debugging - create log in script directory"""
        log_file = os.path.join(self.script_dir, 'project_recreator.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def parse_source_file(self) -> bool:
        """
        Parse the source text file to extract directory structure and file contents
        Returns: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting to parse source file: {self.source_file_path}")
            self.logger.info(f"Script directory: {self.script_dir}")
            self.logger.info(f"File exists: {os.path.exists(self.source_file_path)}")
            
            if not os.path.exists(self.source_file_path):
                self.logger.error(f"Source file not found: {self.source_file_path}")
                self.logger.error(f"Current working directory: {os.getcwd()}")
                self.logger.error(f"Files in directory: {os.listdir(self.script_dir)}")
                return False
            
            with open(self.source_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract root directory from the first directory structure line
            root_match = re.search(r'Directory Structure for:\s*(.+)', content)
            if root_match:
                original_path = root_match.group(1).strip()
                self.root_directory = os.path.basename(original_path)
                self.logger.info(f"Found root directory: {self.root_directory}")
            else:
                # Alternative: try to extract from file path patterns
                file_paths = re.findall(r'FILE START:.*?\((.+?)\)', content)
                if file_paths:
                    first_file_dir = os.path.dirname(file_paths[0])
                    if '\\' in first_file_dir:
                        self.root_directory = first_file_dir.split('\\')[0]
                    elif '/' in first_file_dir:
                        self.root_directory = first_file_dir.split('/')[0]
                    else:
                        self.root_directory = "recreated_project"
                    self.logger.info(f"Extracted root directory from file paths: {self.root_directory}")
                else:
                    self.root_directory = "recreated_project"
                    self.logger.info(f"Using default root directory: {self.root_directory}")
            
            # Parse the entire content
            self._parse_file_contents_detailed(content)
            
            self.logger.info(f"Successfully parsed {len(self.file_contents)} files")
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing source file: {str(e)}", exc_info=True)
            return False

    def _parse_file_contents_detailed(self, content: str):
        """Parse file contents using more robust method"""
        self.logger.info("Parsing file contents with detailed method...")
        
        # Split by file sections using the FILE START pattern
        file_sections = re.split(r'────── FILE START:', content)
        
        for section in file_sections[1:]:  # Skip first part (directory structure)
            if not section.strip():
                continue
                
            try:
                # Extract file path and name from the first line
                first_line_end = section.find('\n')
                if first_line_end == -1:
                    continue
                    
                header_line = section[:first_line_end].strip()
                
                # Extract file path - looking for pattern like: main.py (f0\main.py)
                file_path_match = re.search(r'\((.*?)\)', header_line)
                if file_path_match:
                    file_path = file_path_match.group(1).strip()
                    
                    # Find the content between the header and FILE END
                    content_end = section.find('────── FILE END:')
                    if content_end != -1:
                        # Extract content after the header and before FILE END
                        content_start = first_line_end + 1
                        file_content = section[content_start:content_end].strip()
                        
                        # Remove any trailing file path that might be after content
                        file_content = re.sub(r'\(.*?\)\s*$', '', file_content).strip()
                        
                        self.file_contents[file_path] = file_content
                        self.logger.debug(f"Parsed: {file_path} ({len(file_content)} chars)")
                    else:
                        self.logger.warning(f"FILE END marker not found for: {file_path}")
                else:
                    self.logger.warning(f"Could not extract file path from: {header_line}")
                    
            except Exception as e:
                self.logger.error(f"Error parsing section: {str(e)}")
                continue
    
    def get_unique_directory_name(self) -> str:
        """
        Generate a unique directory name by adding _copy suffix with numbers if needed
        Returns: Unique directory name in script directory
        """
        base_name = f"{self.root_directory}_copy"
        counter = 1
        new_name = base_name
        
        while os.path.exists(os.path.join(self.script_dir, new_name)):
            new_name = f"{base_name}_{counter}"
            counter += 1
        
        self.logger.info(f"Generated unique directory name: {new_name}")
        return new_name
    
    def create_project(self) -> bool:
        """
        Create the entire project structure with all files and contents
        Returns: True if successful, False otherwise
        """
        try:
            if not self.file_contents:
                self.logger.error("No file contents parsed. Please parse source file first.")
                return False
            
            # Get unique directory name in script directory
            target_root_name = self.get_unique_directory_name()
            target_root = os.path.join(self.script_dir, target_root_name)
            
            self.logger.info(f"Creating project in: {target_root}")
            
            # Create all directories first
            self._create_directories(target_root)
            
            # Create all files with their contents
            self._create_files(target_root)
            
            self.logger.info(f"Project successfully created in: {target_root}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating project: {str(e)}", exc_info=True)
            return False
    
    def _create_directories(self, target_root: str):
        """Create all necessary directories"""
        self.logger.info("Creating directory structure...")
        
        # Extract all unique directories from file paths
        all_directories = set()
        
        for file_path in self.file_contents.keys():
            directory = os.path.dirname(file_path)
            if directory:
                # Handle both Windows and Unix-style paths
                directory = directory.replace('\\', os.sep).replace('/', os.sep)
                all_directories.add(directory)
        
        # Create directories in sorted order (deepest first to ensure parent directories exist)
        sorted_directories = sorted(all_directories, key=lambda x: x.count(os.sep))
        
        for directory in sorted_directories:
            full_dir_path = os.path.join(target_root, directory)
            try:
                os.makedirs(full_dir_path, exist_ok=True)
                self.logger.debug(f"Created directory: {full_dir_path}")
            except Exception as e:
                self.logger.error(f"Failed to create directory {full_dir_path}: {str(e)}")
    
    def _create_files(self, target_root: str):
        """Create all files with their contents"""
        self.logger.info(f"Creating {len(self.file_contents)} files...")
        
        files_created = 0
        files_failed = 0
        
        for file_path, content in self.file_contents.items():
            try:
                # Normalize path separators
                normalized_path = file_path.replace('\\', os.sep).replace('/', os.sep)
                full_file_path = os.path.join(target_root, normalized_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                
                # Write file content with UTF-8 encoding
                with open(full_file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                files_created += 1
                self.logger.debug(f"Created file: {full_file_path} ({len(content)} chars)")
                
            except Exception as e:
                files_failed += 1
                self.logger.error(f"Failed to create file {file_path}: {str(e)}")
        
        self.logger.info(f"Files created: {files_created}, failed: {files_failed}")
    
    def get_statistics(self) -> Dict:
        """Get statistics about the parsed project"""
        return {
            'root_directory': self.root_directory,
            'files_parsed': len(self.file_contents),
            'file_paths': list(self.file_contents.keys())[:10]  # First 10 files
        }


def safe_print(message: str):
    """Safely print messages that might contain Unicode characters"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: replace problematic characters
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)


def main():
    """
    Main function to demonstrate usage
    """
    # Use the actual file name
    source_file = "your_project_structure_file.txt"
    
    safe_print("Starting Project Recreator...")
    safe_print(f"Looking for source file: {source_file}")
    
    recreator = ProjectRecreator(source_file)
    
    # Parse the source file
    if recreator.parse_source_file():
        safe_print("✓ Source file parsed successfully")
        
        # Show statistics
        stats = recreator.get_statistics()
        safe_print("Project Statistics:")
        safe_print(f"  Root Directory: {stats['root_directory']}")
        safe_print(f"  Files Found: {stats['files_parsed']}")
        safe_print("  Sample files:")
        for file_path in stats['file_paths']:
            safe_print(f"    - {file_path}")
        
        # Create the project
        safe_print("Creating project...")
        if recreator.create_project():
            safe_print("✓ Project created successfully!")
        else:
            safe_print("✗ Failed to create project")
    else:
        safe_print("✗ Failed to parse source file")
        safe_print("Check project_recreator.log for details")


if __name__ == "__main__":

    main()
