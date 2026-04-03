#!/bin/bash

# Change to the root directory of the git repository
cd "$(git rev-parse --show-toplevel)" || exit 1

# Default values
lfs_only=0
level=4

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -lfs_only) lfs_only=1 ;;
        -level=*) level="${1#*=}" ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Function to check if a file is ignored by git
is_ignored() {
    git check-ignore -q "$1"
    return $?
}

# Function to get LFS status
get_lfs_status() {
    if git check-attr filter "$1" | grep -q "lfs"; then
        echo "Yes"
    else
        echo "No"
    fi
}

# Print header
printf "%-60s %-10s %-10s\n" "File" "Size" "LFS"
echo "------------------------------------------------------------ ---------- ----------"

# Find files up to specified level, excluding .git folder and those in .gitignore
find . -maxdepth $level -type f -not -path "./.git/*" | while read -r file; do
    # Remove leading './' from file path
    file="${file#./}"
    
    # Skip if file is ignored by git
    if is_ignored "$file"; then
        continue
    fi

    # Get LFS status
    lfs_status=$(get_lfs_status "$file")
    
    # Skip if we're only showing LFS files and this isn't one
    if [ $lfs_only -eq 1 ] && [ "$lfs_status" != "Yes" ]; then
        continue
    fi

    # Get file size
    size=$(du -sh "$file" | cut -f1)
    
    # Print file info
    printf "%-60s %-10s %-10s\n" "$file" "$size" "$lfs_status"
done