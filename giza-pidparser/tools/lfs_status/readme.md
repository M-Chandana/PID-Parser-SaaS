# LFS Status Checker

This tool provides a detailed view of your repository's files, their sizes, and LFS tracking status.

## Usage

From the root of your repository, run:
> $./tools/lfs_status/lfs_status.sh [options]


Options:
- `-lfs_only`: Shows only LFS-tracked files
- `-level=X`: Sets the directory depth to search (X is a number, default is 4)

Examples:
- For all files (default 4 levels): `./tools/lfs_status/lfs_status.sh`
- For LFS-tracked files only: `./tools/lfs_status/lfs_status.sh -lfs_only`
- For a custom depth (e.g., 5 levels): `./tools/lfs_status/lfs_status.sh -level=5`
- Combine options: `./tools/lfs_status/lfs_status.sh -lfs_only -level=3`

## Output

The script will display:
- Each file (up to the specified depth in the directory structure)
- Its size
- Whether it's tracked by LFS

Files in the .git folder and those specified in .gitignore will be excluded from this list.

## Note

Ensure the script is executable:
> $chmod +x tools/lfs_status/lfs_status.sh

This tool is designed to be run from the root of your git repository.