// GitHub API integration for fetching git data
// Environment variables are accessed using import.meta.env in Astro

// Helper function to get GitHub credentials
const getGitHubCredentials = () => {
  return {
    username: import.meta.env.PUBLIC_GITHUB_USERNAME || 'nickberens360',
    repo: import.meta.env.PUBLIC_GITHUB_REPO || 'nickberens-astro',
    token: import.meta.env.GITHUB_TOKEN
  };
};

export async function getGitBranch() {
  try {
    const { username, repo, token } = getGitHubCredentials();

    // First try to get the default branch
    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}`, { headers });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    const repoData = await response.json();
    return repoData.default_branch;
  } catch (error) {
    console.error('Error fetching branch:', error);
    return 'main'; // Fallback to a common default branch name
  }
}

export async function getLatestCommitHash() {
  try {
    const { username, repo, token } = getGitHubCredentials();

    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}/commits?per_page=1`, { headers });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    const commits = await response.json();
    return commits[0].sha.substring(0, 7); // Short hash (first 7 characters)
  } catch (error) {
    console.error('Error fetching commit hash:', error);
    return 'unknown';
  }
}

export async function getLatestCommitMessage() {
  try {
    const { username, repo, token } = getGitHubCredentials();

    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}/commits?per_page=1`, { headers });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    const commits = await response.json();
    return commits[0].commit.message;
  } catch (error) {
    console.error('Error fetching commit message:', error);
    return 'Error fetching commit message';
  }
}

export function getGitHubRepoUrl() {
  const { username, repo } = getGitHubCredentials();
  return `https://github.com/${username}/${repo}`;
}
