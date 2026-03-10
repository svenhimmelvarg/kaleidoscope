  
  export function fixImageUrl(url, source){
    if (!url) return '';
    
    // Convert absolute paths to relative paths by finding known ComfyUI directories
    const knownDirs = ['output', 'input', 'release', 'prerelease'];
    const parts = url.split('/');
    
    let cleanUrl = url;
    
    for (let i = 0; i < parts.length; i++) {
        if (knownDirs.includes(parts[i])) {
            // We found a known directory. 
            // The directory immediately before it is the instance name.
            if (i > 0) {
                // Join from the instance name onwards
                cleanUrl = parts.slice(i - 1).join('/');
            } else {
                // If it's the very first part, just use it from here
                cleanUrl = parts.slice(i).join('/');
            }
            break;
        }
    }

    if (source && cleanUrl.startsWith(source + "/")) {
      return `/images/${cleanUrl}`
    }
    
    if (source) {
      return `/images/${source}/${cleanUrl}`
    }
    
    // If we have no source, just prepend /images/ so it doesn't become a relative URL
    return `/images/${cleanUrl}`
  }