/**
 * Get environment variable value, checking window.ENV first (injected by FastAPI in production)
 * then falling back to import.meta.env for development
 * @param {string} key - The environment variable key (e.g., 'VITE_CONVEX_URL')
 * @returns {string|undefined} The environment variable value
 */
function getEnv(key) {
  // Production: window.ENV injected by FastAPI
  if (typeof window !== 'undefined' && window.ENV && window.ENV[key]) {
    return window.ENV[key];
  }
  // Development: import.meta.env
  if (import.meta.env[key]) {
    return import.meta.env[key];
  }
  return undefined;
}

/**
 * Calculate the Convex URL based on environment variable or fallback
 * Uses VITE_CONVEX_URL if it contains localhost/127.0.0.1, otherwise falls back to window-based logic
 * @returns {string} The Convex URL
 */
export function getConvexUrl() {
  let envUrl = getEnv('VITE_CONVEX_URL') || 'http://127.0.0.1:3214';
  
  if (typeof window !== 'undefined') {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocalhost) {
      // Replace localhost/127.0.0.1/0.0.0.0 with the actual hostname used to access the app
      envUrl = envUrl.replace(/localhost|127\.0\.0\.1|0\.0\.0\.0/g, window.location.hostname);
    }
  }
  
  return envUrl.replace(/^https?:\/\//, '');
}

export function getSearchHost() {
  let envUrl = getEnv('VITE_MEILISEARCH_HOST') || 'http://127.0.0.1:7700';

  if (typeof window !== 'undefined') {
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocalhost) {
      // Replace localhost/127.0.0.1/0.0.0.0 with the actual hostname used to access the app
      envUrl = envUrl.replace(/localhost|127\.0\.0\.1|0\.0\.0\.0/g, window.location.hostname);
    }
  }

  // Ensure it starts with http/https
  if (!envUrl.startsWith('http')) {
    envUrl = `http://${envUrl}`;
  }
  return envUrl;
}

export function getMeilisearchUrl() {
  const host = getSearchHost();
  return host.replace(/^https?:\/\//, '');
}

/**
 * Replace the host and port in a URL
 * @param {string} url - The original URL
 * @param {string} oldHost - The old host:port to replace
 * @param {string} newHost - The new host:port to use
 * @returns {string} The URL with the replaced host:port
 */
export function replaceHostPort(url, oldHost, newHost) {
  if (!url || !oldHost || !newHost) {
    return url;
  }
  
  // Create a URL object to parse the URL
  try {
    const urlObj = new URL(url);
    
    // Check if the hostname and port match the old host
    const currentHostPort = `${urlObj.hostname}${urlObj.port ? ':' + urlObj.port : ''}`;
    
    if (currentHostPort === oldHost) {
      // Parse the new host and port
      const [newHostname, newPort] = newHost.split(':');
      
      // Update the hostname and port
      urlObj.hostname = newHostname;
      if (newPort) {
        urlObj.port = newPort;
      } else {
        urlObj.port = '';
      }
    }
    
    return urlObj.toString();
  } catch (e) {
    // If URL parsing fails, fall back to string replacement
    return url.replace(oldHost, newHost);
  }
}

/**
 * Format a facet value by removing path and extension
 * @param {any} value - The value to format
 * @returns {string} The formatted value
 */
export function formatFacetValue(value) {
  if (!value) return '';
  
  if (typeof value !== 'string') {
    value = value.value || value.name || value.type || JSON.stringify(value);
    if (typeof value !== 'string') {
        value = String(value);
    }
  }

  const withoutPath = value.includes('/') ? value.split('/').pop() : value;
  return withoutPath ? withoutPath.replace(/\.[^/.]+$/, '') : '';
}