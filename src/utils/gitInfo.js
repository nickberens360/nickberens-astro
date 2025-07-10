import { execSync } from 'child_process';

export function getGitBranch() {
  try {
    // On Netlify, use the BRANCH environment variable
    if (process.env.BRANCH) {
      // Check if it's a pull request preview (format: pull/X/head)
      if (process.env.BRANCH.startsWith('pull/') && process.env.HEAD) {
        // HEAD contains the actual branch name for pull requests
        return process.env.HEAD;
      }
      return process.env.BRANCH;
    }

    // Fallback to git command for local development
    const branch = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();
    return branch;
  } catch (error) {
    console.error('Error getting git branch:', error);
    return 'unknown';
  }
}

export function getLatestCommitHash() {
  try {
    // Get latest commit hash (short version)
    const commitHash = execSync('git rev-parse --short HEAD').toString().trim();
    return commitHash;
  } catch (error) {
    console.error('Error getting latest commit hash:', error);
    return 'unknown';
  }
}

export function getLatestCommitMessage() {
  try {
    // Get latest commit message
    const commitMessage = execSync('git log -1 --pretty=%B').toString().trim();
    return commitMessage;
  } catch (error) {
    console.error('Error getting latest commit message:', error);
    return 'unknown';
  }
}

export function getGitHubRepoUrl() {
  try {
    // Get the remote URL
    const remoteUrl = execSync('git config --get remote.origin.url').toString().trim();

    // Convert SSH URL to HTTPS URL if needed
    let httpsUrl = remoteUrl;
    if (remoteUrl.startsWith('git@github.com:')) {
      httpsUrl = remoteUrl.replace('git@github.com:', 'https://github.com/').replace(/\.git$/, '');
    } else if (remoteUrl.startsWith('https://') && remoteUrl.endsWith('.git')) {
      httpsUrl = remoteUrl.replace(/\.git$/, '');
    }

    return httpsUrl;
  } catch (error) {
    console.error('Error getting GitHub repo URL:', error);
    return 'https://github.com';
  }
}
