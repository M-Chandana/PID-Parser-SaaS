# PID Parser

**WORK IN PROGRESS**

The master branch is protected. 

The development happens in dev branch.

## Git LFS Setup and Workflow

### Initial Setup
1. Install Git LFS: https://git-lfs.com
2. Run: `git lfs install`

### Cloning and Setup
1. If first time, clone the git in a folder (e.g., "C:/dev"):
    ```
    git lfs clone https://gitlab.com/giza-admin/giza-pidparser.git
    cd giza-pidparser
    git checkout dev
    ```
2. From 2nd time, you could just pull from "C:/dev/giza-pidparser" to update your local repo:
    ```
    git pull origin dev
    ```

### Typical Workflow
1. Create your local branch, e.g., "bugfix/zoom-loses-graph":
    ```
    git checkout -b "bugfix/zoom-loses-graph"
    ```
2. Do your changes. Test.
3. Once ready, stage and commit:
    ```
    git add .
    git commit -m "comment about your change briefly in few words"
    ```
4. Push to raise MR:
    ```
    git push origin "bugfix/zoom-loses-graph"
    ```
5. Go to GitLab web. You will see an MR popup in merge requests. Click to create a new MR.
6. Update the MR form and submit. Your lead would check changes and approve. If auto merge is enabled, merge to dev happens.

### LFS-specific Commands
- Check LFS status: `git lfs status`
- Fetch LFS objects: `git lfs fetch`
- Push LFS objects: `git lfs push origin branch-name`

### Notes
- Large files (.pt, .jpg, .png, etc.) are automatically handled by LFS
- Cloning/pulling may be slower due to large file downloads
- Use `git lfs locks` for binary files that can't be merged

### Troubleshooting
- If LFS files are not downloading: `git lfs pull`
- To force download all LFS objects: `git lfs fetch --all`
- If experiencing issues with pushing large files, increase the Git buffer size:
    ```
    git config --global http.postBuffer 524288000
    ```
    
For more details on Git LFS, visit: https://git-lfs.com