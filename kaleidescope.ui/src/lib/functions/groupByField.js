/**
 * Groups an array of items by a specified field
 * @param {Array} items - Array of items to group
 * @param {string} field - Field name to group by (defaults to "parent_id")
 * @returns {Object} Object with keys as field values and values as arrays of items
 */
export function groupByField(items, field = "parent_id") {
  return items.reduce((acc, item) => {
    const key = item[field] || 'ungrouped';
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
}
