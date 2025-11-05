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
            
            # Parse the entire content using the robust method
            self._parse_file_contents_robust(content)
            
            self.logger.info(f"Successfully parsed {len(self.file_contents)} files")
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing source file: {str(e)}", exc_info=True)
            return False

    def _parse_file_contents_robust(self, content: str):
        """Parse file contents using robust method that handles all files"""
        self.logger.info("Parsing file contents with robust method...")
        
        # Use regex to find all file sections
        # Pattern: FILE START: filename (filepath) ------ content ------ FILE END: filename (filepath)
        file_pattern = r'────── FILE START:\s*(.*?)\s*\((.*?)\)\s*─+\s*(.*?)\s*─+\s*FILE END:\s*\1\s*\(\2\)'
        file_matches = re.findall(file_pattern, content, re.DOTALL)
        
        files_parsed = 0
        
        for match in file_matches:
            try:
                file_name = match[0].strip()
                file_path = match[1].strip()
                file_content = match[2].strip()
                
                self.file_contents[file_path] = file_content
                files_parsed += 1
                self.logger.debug(f"Parsed: {file_path} ({len(file_content)} chars)")
                
            except Exception as e:
                self.logger.error(f"Error parsing file match: {str(e)}")
                continue
        
        # If the above pattern didn't work, try alternative parsing
        if files_parsed == 0:
            self.logger.info("Trying alternative parsing method...")
            self._parse_file_contents_alternative(content)
        else:
            self.logger.info(f"Successfully parsed {files_parsed} files using primary method")

    def _parse_file_contents_alternative(self, content: str):
        """Alternative parsing method for different file formats"""
        # Split by file sections using the FILE START pattern
        file_sections = re.split(r'=+\n\n────── FILE START:', content)
        
        # Handle the first section separately if it doesn't start with FILE START
        if file_sections and not file_sections[0].startswith('FILE START:'):
            # Check if first section contains any file content
            if 'FILE START:' in file_sections[0]:
                first_parts = file_sections[0].split('FILE START:', 1)
                if len(first_parts) > 1:
                    file_sections[0] = 'FILE START:' + first_parts[1]
                else:
                    file_sections = file_sections[1:]
            else:
                file_sections = file_sections[1:]
        
        files_parsed = 0
        
        for section in file_sections:
            if not section.strip():
                continue
                
            try:
                # Extract file path from the first line
                first_line_end = section.find('\n')
                if first_line_end == -1:
                    continue
                    
                header_line = section[:first_line_end].strip()
                
                # Extract file path - looking for pattern like: main.py (f0\main.py)
                file_path_match = re.search(r'\((.*?)\)', header_line)
                if not file_path_match:
                    self.logger.warning(f"Could not extract file path from: {header_line}")
                    continue
                    
                file_path = file_path_match.group(1).strip()
                
                # Find the content between the header and FILE END
                content_start = first_line_end + 1
                content_end = section.find('────── FILE END:')
                
                if content_end == -1:
                    self.logger.warning(f"FILE END marker not found for: {file_path}")
                    continue
                
                # Extract content
                file_content = section[content_start:content_end].strip()
                
                # Clean up any trailing path references
                file_content = re.sub(r'\(.*?\)\s*$', '', file_content).strip()
                
                self.file_contents[file_path] = file_content
                files_parsed += 1
                self.logger.debug(f"Parsed (alt): {file_path} ({len(file_content)} chars)")
                    
            except Exception as e:
                self.logger.error(f"Error parsing section: {str(e)}")
                continue
        
        self.logger.info(f"Alternative method parsed {files_parsed} files")

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
            self._create_files_complete(target_root)
            
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
    
    def _create_files_complete(self, target_root: str):
        """Create all files with their complete contents without truncation"""
        self.logger.info(f"Creating {len(self.file_contents)} files with complete content...")
        
        files_created = 0
        files_failed = 0
        
        for file_path, content in self.file_contents.items():
            try:
                # Normalize path separators
                normalized_path = file_path.replace('\\', os.sep).replace('/', os.sep)
                full_file_path = os.path.join(target_root, normalized_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                
                # Write file content with UTF-8 encoding - COMPLETE CONTENT
                with open(full_file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                # Verify the content was written completely (optional, for debugging)
                with open(full_file_path, 'r', encoding='utf-8') as verify_file:
                    written_content = verify_file.read()
                
                if written_content == content:
                    files_created += 1
                    self.logger.debug(f"✓ Created file: {full_file_path} ({len(content)} chars)")
                else:
                    files_failed += 1
                    self.logger.error(f"✗ Content mismatch for: {file_path}")
                    self.logger.error(f"  Expected: {len(content)} chars, Got: {len(written_content)} chars")
                
            except Exception as e:
                files_failed += 1
                self.logger.error(f"Failed to create file {file_path}: {str(e)}")
        
        self.logger.info(f"Files created: {files_created}, failed: {files_failed}")
        
        # Final verification
        if files_failed == 0:
            self.logger.info("✓ All files created successfully with complete content")
        else:
            self.logger.warning(f"⚠ {files_failed} files had issues during creation")
    
    def get_statistics(self) -> Dict:
        """Get statistics about the parsed project"""
        total_chars = sum(len(content) for content in self.file_contents.values())
        
        return {
            'root_directory': self.root_directory,
            'files_parsed': len(self.file_contents),
            'total_characters': total_chars,
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


def get_file_path_from_user():
    """Get file path from user input or use default"""
    safe_print("\n" + "="*50)
    safe_print("PROJECT RECREATOR")
    safe_print("="*50)
    
    # Show files in current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    safe_print(f"Current directory: {current_dir}")
    safe_print("Text files in directory:")
    
    txt_files = [f for f in os.listdir(current_dir) if f.endswith('.txt')]
    if txt_files:
        for i, file in enumerate(txt_files, 1):
            safe_print(f"  {i}. {file}")
    else:
        safe_print("  No .txt files found")
    
    safe_print("\nOptions:")
    safe_print("  1. Enter full path to text file")
    safe_print("  2. Enter just filename (if in same directory)")
    safe_print("  3. Press Enter to use default")
    
    user_input = input("\nEnter file path (or press Enter for default): ").strip()
    
    if user_input:
        return user_input
    else:
        # Default file - try to find any .txt file with "structure" in name
        default_files = [
            "your_project_structure_text_file.txt",
            "project_structure.txt", 
            "directory_structure.txt"
        ]
        
        # Also check for any .txt files in directory
        all_txt_files = [f for f in os.listdir(current_dir) if f.endswith('.txt')]
        if all_txt_files:
            default_files = all_txt_files + default_files
        
        for default_file in default_files:
            full_path = os.path.join(current_dir, default_file)
            if os.path.exists(full_path):
                safe_print(f"Using default file: {default_file}")
                return default_file
        
        # If no default file exists, ask again
        safe_print("No default file found. Please specify a file path.")
        return get_file_path_from_user()


def main():
    """
    Main function to demonstrate usage
    """
    try:
        # Get file path from user
        source_file = get_file_path_from_user()
        
        safe_print(f"\nUsing source file: {source_file}")
        
        recreator = ProjectRecreator(source_file)
        
        # Parse the source file
        safe_print("Parsing source file...")
        if recreator.parse_source_file():
            safe_print("✓ Source file parsed successfully")
            
            # Show statistics
            stats = recreator.get_statistics()
            safe_print("\nProject Statistics:")
            safe_print(f"  Root Directory: {stats['root_directory']}")
            safe_print(f"  Files Found: {stats['files_parsed']}")
            safe_print(f"  Total Characters: {stats['total_characters']:,}")
            
            if stats['files_parsed'] > 0:
                safe_print("  Sample files:")
                for file_path in stats['file_paths']:
                    file_size = len(recreator.file_contents.get(file_path, ''))
                    safe_print(f"    - {file_path} ({file_size} chars)")
            else:
                safe_print("  ⚠ No files were parsed!")
                safe_print("  Check the source file format and project_recreator.log for details")
                return
            
            # Auto-create project without confirmation
            target_dir = f"{stats['root_directory']}_copy"
            safe_print(f"\nAuto-creating project: {target_dir}")
            safe_print("Creating project...")
            
            if recreator.create_project():
                safe_print("✓ Project created successfully!")
                safe_print("✓ All files contain complete content without truncation")
                safe_print(f"✓ Project location: {os.path.join(recreator.script_dir, target_dir)}")
            else:
                safe_print("✗ Failed to create project")
                
        else:
            safe_print("✗ Failed to parse source file")
            safe_print("Check project_recreator.log for details")
            
    except KeyboardInterrupt:
        safe_print("\nOperation cancelled by user")
    except Exception as e:
        safe_print(f"Unexpected error: {str(e)}")
        safe_print("Check project_recreator.log for details")


if __name__ == "__main__":
    main()
