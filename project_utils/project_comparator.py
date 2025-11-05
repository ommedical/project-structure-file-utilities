import os
import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
import filecmp
import difflib
from typing import Dict, List, Tuple, Any, Set, Optional

class ProjectComparator:
    """
    A comprehensive class to compare two projects for directory structures, 
    files, and file contents with detailed reporting and exclusion support.
    """
    
    def __init__(self, project1_path: str, project2_path: str, 
                 exclude_dirs: Optional[Set[str]] = None, 
                 exclude_files: Optional[Set[str]] = None,
                 exclude_extensions: Optional[Set[str]] = None):
        """
        Initialize the ProjectComparator with two project paths and exclusion patterns.
        
        Args:
            project1_path (str): Path to the first project
            project2_path (str): Path to the second project
            exclude_dirs (Set[str]): Directory names to exclude from comparison
            exclude_files (Set[str]): File names to exclude from comparison
            exclude_extensions (Set[str]): File extensions to exclude from comparison
        """
        # Setup logging first before any other operations
        self.setup_logging()
        
        self.project1_path = self._resolve_path(project1_path)
        self.project2_path = self._resolve_path(project2_path)
        
        # Initialize exclusion sets
        self.exclude_dirs = exclude_dirs or set()
        self.exclude_files = exclude_files or set()
        self.exclude_extensions = exclude_extensions or set()
        
        self.comparison_report = {}
        
        # Log initialization details
        self.logger.info("ProjectComparator initialized successfully")
        self.logger.info(f"Project 1 path: {self.project1_path}")
        self.logger.info(f"Project 2 path: {self.project2_path}")
        self.logger.info(f"Excluded directories: {self.exclude_dirs}")
        self.logger.info(f"Excluded files: {self.exclude_files}")
        self.logger.info(f"Excluded extensions: {self.exclude_extensions}")
        
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve and validate the provided path.
        
        Args:
            path (str): The path to resolve
            
        Returns:
            Path: Resolved Path object
            
        Raises:
            ValueError: If path doesn't exist
        """
        self.logger.debug(f"Resolving path: {path}")
        resolved_path = Path(path).resolve()
        
        if not resolved_path.exists():
            error_msg = f"Path does not exist: {resolved_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.logger.debug(f"Successfully resolved path to: {resolved_path}")
        return resolved_path
    
    def setup_logging(self):
        """Setup comprehensive logging configuration."""
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        log_file = script_dir / "project_comparison_debug.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()  # Also print to console
            ]
        )
        self.logger = logging.getLogger('ProjectComparator')
        
        self.logger.info(f"Logging initialized. Log file: {log_file}")
    
    def _should_exclude_directory(self, dir_name: str, dir_path: Path) -> bool:
        """
        Check if a directory should be excluded from comparison.
        
        Args:
            dir_name (str): Name of the directory
            dir_path (Path): Full path of the directory
            
        Returns:
            bool: True if directory should be excluded
        """
        if dir_name in self.exclude_dirs:
            self.logger.debug(f"Excluding directory: {dir_path} (name matches exclusion list)")
            return True
        return False
    
    def _should_exclude_file(self, file_name: str, file_path: Path) -> bool:
        """
        Check if a file should be excluded from comparison.
        
        Args:
            file_name (str): Name of the file
            file_path (Path): Full path of the file
            
        Returns:
            bool: True if file should be excluded
        """
        # Check file name exclusion
        if file_name in self.exclude_files:
            self.logger.debug(f"Excluding file: {file_path} (name matches exclusion list)")
            return True
        
        # Check file extension exclusion
        file_extension = file_path.suffix.lower()
        if file_extension in self.exclude_extensions:
            self.logger.debug(f"Excluding file: {file_path} (extension {file_extension} matches exclusion list)")
            return True
        
        return False
    
    def _is_directory_empty(self, dir_path: Path) -> bool:
        """
        Check if a directory is empty.
        
        Args:
            dir_path (Path): Path to the directory
            
        Returns:
            bool: True if directory is empty
        """
        try:
            # Check if directory exists and has no items (excluding . and ..)
            return not any(item for item in dir_path.iterdir() if item.name not in ['.', '..'])
        except Exception as e:
            self.logger.debug(f"Error checking if directory is empty {dir_path}: {str(e)}")
            return False
    
    def _is_file_empty(self, file_path: Path) -> bool:
        """
        Check if a file is empty.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            bool: True if file is empty
        """
        try:
            return file_path.stat().st_size == 0
        except Exception as e:
            self.logger.debug(f"Error checking if file is empty {file_path}: {str(e)}")
            return False
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get detailed information about a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            Dict: File information including stats and hash
        """
        try:
            stat = file_path.stat()
            file_info = {
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_file': True,
                'is_dir': False,
                'is_empty': self._is_file_empty(file_path)
            }
            
            # Calculate file hash for content comparison
            if file_path.is_file():
                file_info['hash'] = self._calculate_file_hash(file_path)
                
            return file_info
            
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {str(e)}")
            return {}
    
    def get_directory_info(self, dir_path: Path) -> Dict[str, Any]:
        """
        Get detailed information about a directory.
        
        Args:
            dir_path (Path): Path to the directory
            
        Returns:
            Dict: Directory information
        """
        try:
            stat = dir_path.stat()
            return {
                'name': dir_path.name,
                'path': str(dir_path),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_file': False,
                'is_dir': True,
                'is_empty': self._is_directory_empty(dir_path)
            }
        except Exception as e:
            self.logger.error(f"Error getting directory info for {dir_path}: {str(e)}")
            return {}
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of file content.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: MD5 hash of file content
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            return "error"
    
    def scan_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """
        Recursively scan and collect information about project structure with exclusions.
        
        Args:
            project_path (Path): Root path of the project
            
        Returns:
            Dict: Complete project structure with files and directories
        """
        self.logger.info(f"Scanning project structure: {project_path}")
        
        def _scan_directory(current_path: Path) -> Dict[str, Any]:
            structure = {
                'directories': {},
                'files': {}
            }
            
            try:
                for item in current_path.iterdir():
                    relative_path = item.relative_to(project_path)
                    
                    # Check if directory should be excluded
                    if item.is_dir():
                        if self._should_exclude_directory(item.name, item):
                            self.logger.debug(f"Skipping excluded directory: {item}")
                            continue
                            
                        structure['directories'][str(relative_path)] = {
                            'info': self.get_directory_info(item),
                            'contents': _scan_directory(item)
                        }
                    else:
                        # Check if file should be excluded
                        if self._should_exclude_file(item.name, item):
                            self.logger.debug(f"Skipping excluded file: {item}")
                            continue
                            
                        structure['files'][str(relative_path)] = self.get_file_info(item)
                        
            except PermissionError as e:
                self.logger.warning(f"Permission denied accessing {current_path}: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error scanning {current_path}: {str(e)}")
                
            return structure
        
        return {
            'root_info': self.get_directory_info(project_path),
            'structure': _scan_directory(project_path)
        }
    
    def compare_files_content(self, file1_path: Path, file2_path: Path) -> Dict[str, Any]:
        """
        Compare content of two files and generate detailed differences.
        
        Args:
            file1_path (Path): Path to first file
            file2_path (Path): Path to second file
            
        Returns:
            Dict: Comparison results
        """
        self.logger.debug(f"Comparing file content: {file1_path} vs {file2_path}")
        
        try:
            with open(file1_path, 'r', encoding='utf-8', errors='ignore') as f1:
                content1 = f1.readlines()
            with open(file2_path, 'r', encoding='utf-8', errors='ignore') as f2:
                content2 = f2.readlines()
                
            differ = difflib.Differ()
            diff = list(differ.compare(content1, content2))
            
            # Count differences
            added = sum(1 for line in diff if line.startswith('+ '))
            removed = sum(1 for line in diff if line.startswith('- '))
            changed = sum(1 for line in diff if line.startswith('? '))
            
            return {
                'identical': content1 == content2,
                'line_count_project1': len(content1),
                'line_count_project2': len(content2),
                'differences': {
                    'added_lines': added,
                    'removed_lines': removed,
                    'changed_lines': changed,
                    'total_changes': added + removed + changed
                },
                'diff_output': diff
            }
            
        except UnicodeDecodeError:
            self.logger.warning(f"Binary file detected, skipping content comparison: {file1_path}")
            return {'identical': None, 'binary_file': True}
        except Exception as e:
            self.logger.error(f"Error comparing file content {file1_path} vs {file2_path}: {str(e)}")
            return {'identical': None, 'error': str(e)}
    
    def compare_projects(self) -> Dict[str, Any]:
        """
        Main method to compare two projects comprehensively.
        
        Returns:
            Dict: Complete comparison report
        """
        self.logger.info("Starting project comparison...")
        
        # Scan both projects
        project1_structure = self.scan_project_structure(self.project1_path)
        project2_structure = self.scan_project_structure(self.project2_path)
        
        # Initialize comparison report
        comparison_report = {
            'comparison_timestamp': datetime.now().isoformat(),
            'exclusion_settings': {
                'excluded_directories': list(self.exclude_dirs),
                'excluded_files': list(self.exclude_files),
                'excluded_extensions': list(self.exclude_extensions)
            },
            'project1': {
                'path': str(self.project1_path),
                'root_info': project1_structure['root_info']
            },
            'project2': {
                'path': str(self.project2_path),
                'root_info': project2_structure['root_info']
            },
            'directory_comparison': {},
            'file_comparison': {},
            'summary': {
                'unique_directories_project1': 0,
                'unique_directories_project2': 0,
                'unique_files_project1': 0,
                'unique_files_project2': 0,
                'common_files_different_content': 0,
                'common_files_identical_content': 0,
                'excluded_directories_count': 0,
                'excluded_files_count': 0
            }
        }
        
        # Compare directories
        self._compare_directories(
            project1_structure['structure'], 
            project2_structure['structure'], 
            comparison_report
        )
        
        # Compare files
        self._compare_files(
            project1_structure['structure'], 
            project2_structure['structure'], 
            comparison_report
        )
        
        self.comparison_report = comparison_report
        self.logger.info("Project comparison completed successfully")
        
        return comparison_report
    
    def _compare_directories(self, struct1: Dict, struct2: Dict, report: Dict):
        """Compare directory structures recursively."""
        dirs1 = set(struct1['directories'].keys())
        dirs2 = set(struct2['directories'].keys())
        
        common_dirs = dirs1.intersection(dirs2)
        unique_dirs1 = dirs1 - dirs2
        unique_dirs2 = dirs2 - dirs1
        
        # Update summary
        report['summary']['unique_directories_project1'] += len(unique_dirs1)
        report['summary']['unique_directories_project2'] += len(unique_dirs2)
        
        # Record directory differences
        for dir_path in common_dirs:
            dir1_info = struct1['directories'][dir_path]['info']
            dir2_info = struct2['directories'][dir_path]['info']
            
            report['directory_comparison'][dir_path] = {
                'status': 'common',
                'project1_info': dir1_info,
                'project2_info': dir2_info,
                'latest_version': self._get_latest_info(dir1_info, dir2_info),
                'is_empty_project1': dir1_info.get('is_empty', False),
                'is_empty_project2': dir2_info.get('is_empty', False)
            }
            
            # Recursively compare subdirectories
            self._compare_directories(
                struct1['directories'][dir_path]['contents'],
                struct2['directories'][dir_path]['contents'],
                report
            )
        
        for dir_path in unique_dirs1:
            dir_info = struct1['directories'][dir_path]['info']
            report['directory_comparison'][dir_path] = {
                'status': 'only_in_project1',
                'project1_info': dir_info,
                'latest_version': 'Project 1',
                'is_empty_project1': dir_info.get('is_empty', False),
                'is_empty_project2': None
            }
        
        for dir_path in unique_dirs2:
            dir_info = struct2['directories'][dir_path]['info']
            report['directory_comparison'][dir_path] = {
                'status': 'only_in_project2',
                'project2_info': dir_info,
                'latest_version': 'Project 2',
                'is_empty_project1': None,
                'is_empty_project2': dir_info.get('is_empty', False)
            }
    
    def _compare_files(self, struct1: Dict, struct2: Dict, report: Dict):
        """Compare files recursively."""
        files1 = set(struct1['files'].keys())
        files2 = set(struct2['files'].keys())
        
        common_files = files1.intersection(files2)
        unique_files1 = files1 - files2
        unique_files2 = files2 - files1
        
        # Update summary
        report['summary']['unique_files_project1'] += len(unique_files1)
        report['summary']['unique_files_project2'] += len(unique_files2)
        
        # Compare common files
        for file_path in common_files:
            file1_info = struct1['files'][file_path]
            file2_info = struct2['files'][file_path]
            
            # Compare content if hashes are different
            content_comparison = None
            if file1_info.get('hash') != file2_info.get('hash'):
                content_comparison = self.compare_files_content(
                    Path(file1_info['path']), 
                    Path(file2_info['path'])
                )
                
                if content_comparison and content_comparison.get('identical') is False:
                    report['summary']['common_files_different_content'] += 1
                elif content_comparison and content_comparison.get('identical'):
                    report['summary']['common_files_identical_content'] += 1
            
            report['file_comparison'][file_path] = {
                'status': 'common',
                'project1_info': file1_info,
                'project2_info': file2_info,
                'content_comparison': content_comparison,
                'latest_version': self._get_latest_info(file1_info, file2_info),
                'is_empty_project1': file1_info.get('is_empty', False),
                'is_empty_project2': file2_info.get('is_empty', False)
            }
        
        # Record unique files
        for file_path in unique_files1:
            file_info = struct1['files'][file_path]
            report['file_comparison'][file_path] = {
                'status': 'only_in_project1',
                'project1_info': file_info,
                'latest_version': 'Project 1',
                'is_empty_project1': file_info.get('is_empty', False),
                'is_empty_project2': None
            }
        
        for file_path in unique_files2:
            file_info = struct2['files'][file_path]
            report['file_comparison'][file_path] = {
                'status': 'only_in_project2',
                'project2_info': file_info,
                'latest_version': 'Project 2',
                'is_empty_project1': None,
                'is_empty_project2': file_info.get('is_empty', False)
            }
        
        # Recursively compare files in subdirectories
        common_dirs = set(struct1['directories'].keys()).intersection(set(struct2['directories'].keys()))
        for dir_path in common_dirs:
            self._compare_files(
                struct1['directories'][dir_path]['contents'],
                struct2['directories'][dir_path]['contents'],
                report
            )
    
    def _format_table(self, headers: List[str], rows: List[List[str]], col_widths: List[int] = None) -> str:
        """
        Format data as a table.
        
        Args:
            headers: List of header strings
            rows: List of rows (each row is a list of strings)
            col_widths: Optional list of column widths
            
        Returns:
            Formatted table as string
        """
        if not rows:
            return "No data available\n"
            
        # Calculate column widths if not provided
        if not col_widths:
            col_widths = [len(str(h)) for h in headers]
            for row in rows:
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Add padding
        col_widths = [w + 2 for w in col_widths]
        
        # Create separator line
        separator = "+" + "+".join("-" * w for w in col_widths) + "+\n"
        
        # Build table
        table = separator
        table += "|" + "|".join(f" {h:<{col_widths[i]-2}} " for i, h in enumerate(headers)) + "|\n"
        table += separator
        
        for row in rows:
            table += "|" + "|".join(f" {str(cell):<{col_widths[i]-2}} " for i, cell in enumerate(row)) + "|\n"
        
        table += separator
        return table
    
    def _get_latest_info(self, info1: Dict, info2: Dict) -> str:
        """
        Determine which file/directory is latest based on modification time.
        
        Args:
            info1: File/directory info from project 1
            info2: File/directory info from project 2
            
        Returns:
            String indicating which is latest
        """
        if not info1 or not info2:
            return "N/A"
            
        try:
            mod1 = datetime.fromisoformat(info1.get('modified', ''))
            mod2 = datetime.fromisoformat(info2.get('modified', ''))
            
            if mod1 > mod2:
                return "Project 1"
            elif mod2 > mod1:
                return "Project 2"
            else:
                return "Same"
        except:
            return "N/A"
    
    def _get_empty_status(self, is_empty1: bool, is_empty2: bool, status: str) -> str:
        """
        Get formatted empty status for display.
        
        Args:
            is_empty1: Empty status for project 1
            is_empty2: Empty status for project 2
            status: Comparison status
            
        Returns:
            Formatted empty status string
        """
        if status == 'common':
            if is_empty1 and is_empty2:
                return "Both Empty"
            elif is_empty1:
                return "Empty in P1 Only"
            elif is_empty2:
                return "Empty in P2 Only"
            else:
                return "Both Not Empty"
        elif status == 'only_in_project1':
            return "Empty" if is_empty1 else "Not Empty"
        elif status == 'only_in_project2':
            return "Empty" if is_empty2 else "Not Empty"
        else:
            return "N/A"
    
    def generate_report(self) -> str:
        """
        Generate a comprehensive human-readable comparison report.
        
        Returns:
            str: Path to the generated report file
        """
        self.logger.info("Generating comparison report...")
        
        script_dir = Path(__file__).parent
        report_file = script_dir / "project_comparison_report.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("PROJECT COMPARISON REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Comparison Date: {self.comparison_report['comparison_timestamp']}\n")
                f.write(f"Project 1: {self.comparison_report['project1']['path']}\n")
                f.write(f"Project 2: {self.comparison_report['project2']['path']}\n\n")
                
                # Exclusion Settings Section
                f.write("EXCLUSION SETTINGS\n")
                f.write("-" * 20 + "\n")
                excl_settings = self.comparison_report['exclusion_settings']
                f.write(f"Excluded directories: {', '.join(excl_settings['excluded_directories']) or 'None'}\n")
                f.write(f"Excluded files: {', '.join(excl_settings['excluded_files']) or 'None'}\n")
                f.write(f"Excluded extensions: {', '.join(excl_settings['excluded_extensions']) or 'None'}\n\n")
                
                # Summary Section
                f.write("SUMMARY\n")
                f.write("-" * 20 + "\n")
                summary = self.comparison_report['summary']
                summary_rows = [
                    ["Unique directories in Project 1", str(summary['unique_directories_project1'])],
                    ["Unique directories in Project 2", str(summary['unique_directories_project2'])],
                    ["Unique files in Project 1", str(summary['unique_files_project1'])],
                    ["Unique files in Project 2", str(summary['unique_files_project2'])],
                    ["Common files with identical content", str(summary['common_files_identical_content'])],
                    ["Common files with different content", str(summary['common_files_different_content'])]
                ]
                f.write(self._format_table(["Metric", "Count"], summary_rows))
                f.write("\n")
                
                # Directory Comparison Section
                f.write("DIRECTORY COMPARISON\n")
                f.write("-" * 25 + "\n")
                
                # Group directories by status
                common_dirs = []
                only_in_project1_dirs = []
                only_in_project2_dirs = []
                
                for dir_path, comparison in self.comparison_report['directory_comparison'].items():
                    status = comparison['status']
                    latest = comparison.get('latest_version', 'N/A')
                    empty_status = self._get_empty_status(
                        comparison.get('is_empty_project1', False),
                        comparison.get('is_empty_project2', False),
                        status
                    )
                    
                    if status == 'common':
                        common_dirs.append([dir_path, "EXISTS IN BOTH", latest, empty_status])
                    elif status == 'only_in_project1':
                        only_in_project1_dirs.append([dir_path, "ONLY IN PROJECT 1", latest, empty_status])
                    elif status == 'only_in_project2':
                        only_in_project2_dirs.append([dir_path, "ONLY IN PROJECT 2", latest, empty_status])
                
                # Write common directories
                if common_dirs:
                    f.write("\nCOMMON DIRECTORIES (Exist in both projects):\n")
                    f.write(self._format_table(
                        ["Directory Path", "Status", "Latest Version", "Empty Status"], 
                        common_dirs
                    ))
                
                # Write unique directories
                if only_in_project1_dirs:
                    f.write("\nUNIQUE DIRECTORIES (Only in Project 1):\n")
                    f.write(self._format_table(
                        ["Directory Path", "Status", "Latest Version", "Empty Status"], 
                        only_in_project1_dirs
                    ))
                
                if only_in_project2_dirs:
                    f.write("\nUNIQUE DIRECTORIES (Only in Project 2):\n")
                    f.write(self._format_table(
                        ["Directory Path", "Status", "Latest Version", "Empty Status"], 
                        only_in_project2_dirs
                    ))
                
                if not common_dirs and not only_in_project1_dirs and not only_in_project2_dirs:
                    f.write("No directories found for comparison.\n")
                
                # File Comparison Section
                f.write("\n" + "="*80 + "\n")
                f.write("FILE COMPARISON\n")
                f.write("="*80 + "\n\n")
                
                # Group files by status
                identical_files = []
                different_content_files = []
                not_compared_files = []
                only_in_project1_files = []
                only_in_project2_files = []
                
                for file_path, comparison in self.comparison_report['file_comparison'].items():
                    status = comparison['status']
                    latest = comparison.get('latest_version', 'N/A')
                    empty_status = self._get_empty_status(
                        comparison.get('is_empty_project1', False),
                        comparison.get('is_empty_project2', False),
                        status
                    )
                    
                    if status == 'common':
                        content_comp = comparison.get('content_comparison', {}) or {}
                        if content_comp.get('identical'):
                            identical_files.append([file_path, "IDENTICAL", latest, empty_status])
                        elif content_comp.get('identical') is False:
                            diff_info = content_comp.get('differences', {})
                            changes = f"+{diff_info.get('added_lines', 0)} -{diff_info.get('removed_lines', 0)}"
                            different_content_files.append([file_path, "DIFFERENT CONTENT", latest, empty_status, changes])
                        else:
                            not_compared_files.append([file_path, "COMMON (Not Compared)", latest, empty_status])
                    elif status == 'only_in_project1':
                        only_in_project1_files.append([file_path, "ONLY IN PROJECT 1", latest, empty_status, ""])
                    elif status == 'only_in_project2':
                        only_in_project2_files.append([file_path, "ONLY IN PROJECT 2", latest, empty_status, ""])
                
                # Write files with different content
                if different_content_files:
                    f.write("FILES WITH DIFFERENT CONTENT:\n")
                    f.write("-" * 50 + "\n")
                    f.write(self._format_table(
                        ["File Path", "Status", "Latest Version", "Empty Status", "Changes"], 
                        different_content_files
                    ))
                    f.write("\n")
                
                # Write identical files
                if identical_files:
                    f.write("FILES WITH IDENTICAL CONTENT:\n")
                    f.write("-" * 40 + "\n")
                    f.write(self._format_table(
                        ["File Path", "Status", "Latest Version", "Empty Status"], 
                        identical_files
                    ))
                    f.write("\n")
                
                # Write common files not compared
                if not_compared_files:
                    f.write("COMMON FILES (Content Not Compared):\n")
                    f.write("-" * 45 + "\n")
                    f.write(self._format_table(
                        ["File Path", "Status", "Latest Version", "Empty Status"], 
                        not_compared_files
                    ))
                    f.write("\n")
                
                # Write files only in project 1
                if only_in_project1_files:
                    f.write("FILES ONLY IN PROJECT 1:\n")
                    f.write("-" * 30 + "\n")
                    f.write(self._format_table(
                        ["File Path", "Status", "Latest Version", "Empty Status", ""], 
                        only_in_project1_files
                    ))
                    f.write("\n")
                
                # Write files only in project 2
                if only_in_project2_files:
                    f.write("FILES ONLY IN PROJECT 2:\n")
                    f.write("-" * 30 + "\n")
                    f.write(self._format_table(
                        ["File Path", "Status", "Latest Version", "Empty Status", ""], 
                        only_in_project2_files
                    ))
                    f.write("\n")
                
                if not any([different_content_files, identical_files, not_compared_files, 
                           only_in_project1_files, only_in_project2_files]):
                    f.write("No files found for comparison.\n")
                
                # Detailed File Differences Section
                f.write("\n" + "="*80 + "\n")
                f.write("DETAILED FILE DIFFERENCES\n")
                f.write("="*80 + "\n\n")
                
                files_with_differences = 0
                for file_path, comparison in self.comparison_report['file_comparison'].items():
                    if (comparison['status'] == 'common' and 
                        comparison.get('content_comparison') and 
                        comparison['content_comparison'].get('identical') is False):
                        
                        files_with_differences += 1
                        f.write(f"File: {file_path}\n")
                        f.write("-" * (len(file_path) + 6) + "\n")
                        
                        diff_output = comparison['content_comparison'].get('diff_output', [])
                        lines_shown = 0
                        for line in diff_output:
                            if line.startswith('+ ') or line.startswith('- '):
                                if lines_shown < 50:  # Show first 50 differences
                                    if line.startswith('+ '):
                                        f.write(f"  + {line[2:]}")
                                    elif line.startswith('- '):
                                        f.write(f"  - {line[2:]}")
                                    lines_shown += 1
                        
                        if len(diff_output) > 50:
                            f.write(f"  ... and {len(diff_output) - 50} more differences\n")
                        
                        f.write("\n" + "-"*80 + "\n\n")
                
                if files_with_differences == 0:
                    f.write("No files with content differences found.\n")
            
            self.logger.info(f"Comparison report generated: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            raise
    
    def save_json_report(self) -> str:
        """
        Save the complete comparison data as JSON for programmatic use.
        
        Returns:
            str: Path to the JSON report file
        """
        self.logger.info("Saving JSON report...")
        
        script_dir = Path(__file__).parent
        json_report_file = script_dir / "project_comparison_detailed.json"
        
        try:
            with open(json_report_file, 'w', encoding='utf-8') as f:
                json.dump(self.comparison_report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"JSON report saved: {json_report_file}")
            return str(json_report_file)
            
        except Exception as e:
            self.logger.error(f"Error saving JSON report: {str(e)}")
            raise


# Example usage and demonstration
def main():
    """
    Example usage of the ProjectComparator class with exclusion support.
    """
    # Default project paths (can be modified by user)
    # Using forward slashes or raw strings to avoid escape issues
    default_project1 = r"C:\Users\user\Desktop\dir\d1"
    default_project2 = r"C:\Users\user\Desktop\dir\d2"
    
    print("PROJECT COMPARISON TOOL")
    print("=" * 50)
    
    # Project path selection
    print(f"\nCurrent default project paths:")
    print(f"Project 1: {default_project1}")
    print(f"Project 2: {default_project2}")
    
    use_default = input("\nUse default project paths? (y/n): ").strip().lower()
    
    if use_default == 'y':
        project1 = default_project1
        project2 = default_project2
    else:
        project1 = input("Enter path to first project: ").strip()
        project2 = input("Enter path to second project: ").strip()
    
    # Define default exclusions
    exclude_dirs = {
        '__pycache__', '.git', '.vscode', '.idea', 'node_modules', 
        'venv', 'env', '.pytest_cache', 'build', 'dist', '.temp'
    }
    
    exclude_files = {
        '.DS_Store', 'thumbs.db', 'desktop.ini'
    }
    
    exclude_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin',
        '.log', '.tmp', '.temp', '.cache'
    }
    
    # Allow user to modify exclusions
    print("\nCurrent exclusion settings:")
    print(f"Directories: {', '.join(sorted(exclude_dirs))}")
    print(f"Files: {', '.join(sorted(exclude_files))}")
    print(f"Extensions: {', '.join(sorted(exclude_extensions))}")
    
    modify_exclusions = input("\nDo you want to modify exclusion settings? (y/n): ").strip().lower()
    
    if modify_exclusions == 'y':
        print("\nModify exclusions (press Enter to keep current):")
        
        # Directories
        current_dirs = ', '.join(sorted(exclude_dirs))
        new_dirs = input(f"Excluded directories [{current_dirs}]: ").strip()
        if new_dirs:
            exclude_dirs = set([d.strip() for d in new_dirs.split(',') if d.strip()])
        
        # Files
        current_files = ', '.join(sorted(exclude_files))
        new_files = input(f"Excluded files [{current_files}]: ").strip()
        if new_files:
            exclude_files = set([f.strip() for f in new_files.split(',') if f.strip()])
        
        # Extensions
        current_extensions = ', '.join(sorted(exclude_extensions))
        new_extensions = input(f"Excluded extensions [{current_extensions}]: ").strip()
        if new_extensions:
            exclude_extensions = set([e.strip() for e in new_extensions.split(',') if e.strip()])
    
    try:
        # Initialize comparator with exclusions
        comparator = ProjectComparator(
            project1, 
            project2,
            exclude_dirs=exclude_dirs,
            exclude_files=exclude_files,
            exclude_extensions=exclude_extensions
        )
        
        # Perform comparison
        print("\nStarting project comparison...")
        comparison_result = comparator.compare_projects()
        
        # Generate reports
        print("Generating reports...")
        text_report = comparator.generate_report()
        json_report = comparator.save_json_report()
        
        # Get script directory for output files
        script_dir = Path(__file__).parent
        
        print(f"\n" + "=" * 50)
        print("COMPARISON COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Text report: {text_report}")
        print(f"JSON report: {json_report}")
        print(f"Debug logs: {script_dir / 'project_comparison_debug.log'}")
        print(f"\nAll output files are saved in: {script_dir}")
        
        # Show summary
        summary = comparison_result['summary']
        print(f"\nSUMMARY:")
        print(f"Unique directories in Project 1: {summary['unique_directories_project1']}")
        print(f"Unique directories in Project 2: {summary['unique_directories_project2']}")
        print(f"Unique files in Project 1: {summary['unique_files_project1']}")
        print(f"Unique files in Project 2: {summary['unique_files_project2']}")
        print(f"Common files with identical content: {summary['common_files_identical_content']}")
        print(f"Common files with different content: {summary['common_files_different_content']}")
        
    except Exception as e:
        print(f"\nERROR: Comparison failed: {str(e)}")
        import traceback
        print(f"Detailed error: {traceback.format_exc()}")
        print("Check the debug log for detailed error information.")


# Alternative: Direct usage without interactive prompts
def quick_compare(project1_path: str, project2_path: str, 
                  exclude_dirs: Optional[Set[str]] = None,
                  exclude_files: Optional[Set[str]] = None,
                  exclude_extensions: Optional[Set[str]] = None) -> ProjectComparator:
    """
    Quick comparison without interactive prompts.
    
    Args:
        project1_path (str): Path to first project
        project2_path (str): Path to second project
        exclude_dirs (Set[str]): Directories to exclude
        exclude_files (Set[str]): Files to exclude
        exclude_extensions (Set[str]): Extensions to exclude
        
    Returns:
        ProjectComparator: Comparator instance with completed comparison
    """
    comparator = ProjectComparator(
        project1_path, 
        project2_path,
        exclude_dirs=exclude_dirs,
        exclude_files=exclude_files,
        exclude_extensions=exclude_extensions
    )
    
    comparator.compare_projects()
    comparator.generate_report()
    comparator.save_json_report()
    
    return comparator


if __name__ == "__main__":
    # Run interactive comparison

    main()
