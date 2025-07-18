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
    const commitData = await getLatestCommit();
    return commitData.hash;
  } catch (error) {
    console.error('Error fetching commit hash:', error);
    return 'unknown';
  }
}

export async function getLatestCommitMessage() {
  try {
    return await getLatestCommit();
  } catch (error) {
    console.error('Error fetching commit message:', error);
    return {
      hash: 'unknown',
      message: 'Error fetching commit message',
      url: null
    };
  }
}

export function getGitHubRepoUrl() {
  const { username, repo } = getGitHubCredentials();
  return `https://github.com/${username}/${repo}`;
}

// Shared function to fetch latest commit data
export async function getLatestCommit() {
  try {
    const { username, repo, token } = getGitHubCredentials();

    // Check if we have valid cached data
    const now = Date.now();
    if (latestCommitCache.data && (now - latestCommitCache.timestamp) < latestCommitCache.expiryTime) {
      console.log('Using cached latest commit data');
      return latestCommitCache.data;
    }

    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}/commits?per_page=1`, { headers });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status}`);
    }

    const commits = await response.json();
    const commitData = {
      hash: commits[0].sha.substring(0, 7),
      message: commits[0].commit.message,
      url: commits[0].html_url
    };

    // Cache the successful result
    latestCommitCache.data = commitData;
    latestCommitCache.timestamp = now;

    return commitData;
  } catch (error) {
    console.error('Error fetching latest commit:', error);
    return {
      hash: 'unknown',
      message: 'Error fetching commit message',
      url: null
    };
  }
}

// Cache for code frequency data
let codeFrequencyCache = {
  data: null,
  timestamp: 0,
  expiryTime: 5 * 60 * 1000 // 5 minutes in milliseconds
};

// Cache for commit history data
let commitHistoryCache = {
  data: null,
  timestamp: 0,
  expiryTime: 5 * 60 * 1000 // 5 minutes in milliseconds
};

// Cache for latest commit data
let latestCommitCache = {
  data: null,
  timestamp: 0,
  expiryTime: 5 * 60 * 1000 // 5 minutes in milliseconds
};

export async function getCommitHistory(limit = 10) {
  try {
    const { username, repo, token } = getGitHubCredentials();

    // Check if we have valid cached data
    const now = Date.now();
    if (commitHistoryCache.data && (now - commitHistoryCache.timestamp) < commitHistoryCache.expiryTime) {
      console.log('Using cached commit history data');
      return commitHistoryCache.data;
    }

    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}/commits?per_page=${limit}`, { headers });

    if (!response.ok) {
      let errorMessage = `GitHub API error: ${response.status}`;

      if (response.status === 403) {
        errorMessage = 'Rate limit exceeded. Please try again later or use a GitHub token.';
      } else if (response.status === 404) {
        errorMessage = 'Repository not found. Please check the repository name and username.';
      } else if (response.status === 401) {
        errorMessage = 'Authentication failed. Please check your GitHub token.';
      }

      throw new Error(errorMessage);
    }

    const commits = await response.json();

    // Format the commits to match the desired output format
    const formattedCommits = commits.map(commit => {
      return {
        hash: commit.sha.substring(0, 7),
        message: commit.commit.message.split('\n')[0], // Get first line of commit message
        url: commit.html_url
      };
    });

    // Cache the successful result
    commitHistoryCache.data = formattedCommits;
    commitHistoryCache.timestamp = now;

    return formattedCommits;
  } catch (error) {
    console.error('Error fetching commit history:', error);
    return {
      error: true,
      message: error.message || 'An error occurred while fetching commit history'
    };
  }
}

export async function getCodeFrequency(retryCount = 0, maxRetries = 3) {
  try {
    const { username, repo, token } = getGitHubCredentials();

    // Check if we have valid cached data
    const now = Date.now();
    if (codeFrequencyCache.data && (now - codeFrequencyCache.timestamp) < codeFrequencyCache.expiryTime) {
      console.log('Using cached code frequency data');
      return codeFrequencyCache.data;
    }

    const headers = token ? { Authorization: `token ${token}` } : {};
    const response = await fetch(`https://api.github.com/repos/${username}/${repo}/stats/code_frequency`, { headers });

    // Handle 202 Accepted response with retry logic
    if (response.status === 202) {
      if (retryCount < maxRetries) {
        console.log(`GitHub is computing statistics. Retry ${retryCount + 1}/${maxRetries} in 2 seconds...`);

        // Wait for 2 seconds before retrying
        return new Promise(resolve => {
          setTimeout(() => {
            resolve(getCodeFrequency(retryCount + 1, maxRetries));
          }, 2000);
        });
      } else {
        return {
          computing: true,
          message: "GitHub is still calculating statistics. Please try again later."
        };
      }
    }

    // Handle different error cases with specific messages
    if (!response.ok) {
      let errorMessage = `GitHub API error: ${response.status}`;

      if (response.status === 403) {
        errorMessage = 'Rate limit exceeded. Please try again later or use a GitHub token.';
      } else if (response.status === 404) {
        errorMessage = 'Repository not found. Please check the repository name and username.';
      } else if (response.status === 401) {
        errorMessage = 'Authentication failed. Please check your GitHub token.';
      }

      throw new Error(errorMessage);
    }

    // GitHub returns an array of weekly data points
    // Each data point is [timestamp, additions, deletions]
    const frequencyData = await response.json();

    // Ensure we always return an array
    if (!Array.isArray(frequencyData)) {
      console.error('Unexpected response format from GitHub API:', frequencyData);
      return [];
    }

    // Cache the successful result
    codeFrequencyCache.data = frequencyData;
    codeFrequencyCache.timestamp = now;

    return frequencyData;
  } catch (error) {
    console.error('Error fetching code frequency:', error);
    return {
      error: true,
      message: error.message || 'An error occurred while fetching code frequency data'
    };
  }
}
