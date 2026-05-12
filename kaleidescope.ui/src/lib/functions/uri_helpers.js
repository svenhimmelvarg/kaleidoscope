  
export function imageFileUrl(path) {
  if (!path) return '';
  return `/images/file?path=${encodeURIComponent(path)}`;
}

export function inputImageUrl(path) {
  if (!path) return '';
  return `/images/input?path=${encodeURIComponent(path)}`;
}
