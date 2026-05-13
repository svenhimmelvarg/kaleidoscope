  
export function imageFileUrl(path) {
  if (!path) return '';
  return `/images/file?path=${encodeURIComponent(path)}`;
}

export function inputImageUrl(path) {
  if (!path) return '';
  return `/images/input?path=${encodeURIComponent(path)}`;
}

export function isVideoDoc(doc) {
  return doc?.type === 'video' || doc?.content_type?.includes('video') || doc?.image_url?.toLowerCase().endsWith('.mp4');
}
