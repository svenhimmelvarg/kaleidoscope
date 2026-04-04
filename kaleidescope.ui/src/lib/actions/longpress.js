export function longpress(node, duration = 500) {
  let timer;
  let isLongPress = false;

  const handlePointerDown = (e) => {
    isLongPress = false;
    timer = setTimeout(() => {
      isLongPress = true;
      node.dispatchEvent(new CustomEvent('longpress'));
    }, duration);
  };

  const cancelPress = () => {
    if (timer) clearTimeout(timer);
  };

  const handlePointerUp = (e) => {
    cancelPress();
    if (isLongPress) {
      const captureClick = (e) => {
        e.stopPropagation();
        e.preventDefault();
        node.removeEventListener('click', captureClick, true);
      };
      node.addEventListener('click', captureClick, true);
      
      setTimeout(() => node.removeEventListener('click', captureClick, true), 50);
    }
  };

  node.addEventListener('pointerdown', handlePointerDown);
  node.addEventListener('pointerup', handlePointerUp);
  node.addEventListener('pointercancel', cancelPress);
  node.addEventListener('pointerleave', cancelPress);

  return {
    update(newDuration) {
      duration = newDuration;
    },
    destroy() {
      node.removeEventListener('pointerdown', handlePointerDown);
      node.removeEventListener('pointerup', handlePointerUp);
      node.removeEventListener('pointercancel', cancelPress);
      node.removeEventListener('pointerleave', cancelPress);
    }
  };
}