# Skill versions are pinned by git tags, not copied snapshots

Each released version of a skill is marked with a git tag named `<skill>-v<version>`, and skevals runs old versions by checking out that tag into a temporary worktree. We chose this over copying each version into a `versions/` folder, so that a version exists once, in git history, and cannot drift from the real skill. The cost is that a version only exists once it is tagged, and that runs of uncommitted edits are labelled as working tree runs rather than versions.
