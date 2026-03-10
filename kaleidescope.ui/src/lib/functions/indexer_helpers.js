/**
 * @typedef {Object} FacetDistribution
 * @property {Object.<string, number>} facets
 */

/**
 * @param {Object.<string, Object.<string, number>>} facetDistribution
 * @returns {Object.<string, Object.<string, number>>}
 */
export function reduceFacetDistribution(facetDistribution) {
  /** @type {Object.<string, Object.<string, number>>} */
  const result = {};

  if (!facetDistribution || typeof facetDistribution !== 'object') {
    return result;
  }

  for (const [facetKey, facets] of Object.entries(facetDistribution)) {
    const counts = Object.values(facets);
    
    if (counts.length <= 1) {
      continue;
    }

    const hasSignificantCount = counts.some(count => count > 1);

    if (hasSignificantCount) {
      result[facetKey] = facets;
    }
  }

  return result;
}
