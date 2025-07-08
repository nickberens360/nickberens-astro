import { execSync } from 'child_process';

export function getGitBranch() {
  try {
    // Get current branch name
    const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
    return branch;
  } catch (error) {
    console.error('Error getting git branch:', error);
    return 'unknown';
  }
}