export function getDateHeader(yy: any, mm: any, dd: any) {
  if (!yy || !mm || !dd) return null;
  const d = new Date(yy, mm - 1, dd);
  const today = new Date();
  
  if (
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()
  ) {
    return "Today";
  }
  
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  
  return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]}`;
}

export function groupIntelligently(items: any[], isGroupingEnabled: boolean) {
  if (!isGroupingEnabled) {
     // Return dummy grouping format if grouping disabled: {"ungrouped": items}
     return { ungrouped: items };
  }

  const idMap = new Map();
  items.forEach(item => idMap.set(item.id, item));

  // 1. Identify all Roots
  const roots = items.filter(item => {
    if (!item.parent_id) return true;
    if (!idMap.has(item.parent_id)) return true;
    return false;
  });

  // Group them mapping: rootId -> [Root, ...Children]
  const finalGroups: Record<string, any[]> = {};
  
  roots.forEach(r => {
    finalGroups[r.id] = [r]; // First element is always the Root
  });

  // Elements that are not roots
  const nonRoots = items.filter(item => !roots.includes(item));

  // 2. Attach children to their corresponding Root
  nonRoots.forEach(item => {
    let currentParentId = item.parent_id;
    let rootFoundId = null;

    // Trace up to max depth to avoid infinite loops
    let depth = 0;
    while (currentParentId && depth < 20) {
      if (finalGroups[currentParentId]) {
        rootFoundId = currentParentId;
        break;
      }
      const parentItem = idMap.get(currentParentId);
      if (parentItem && parentItem.parent_id) {
        currentParentId = parentItem.parent_id;
      } else {
         break;
      }
      depth++;
    }

    if (rootFoundId) {
       finalGroups[rootFoundId].push(item);
    } else {
       // Fallback
       finalGroups[item.id] = [item];
    }
  });

  // Now ensure within each group, the Root (index 0) is followed by children sorted newest to oldest
  Object.keys(finalGroups).forEach(k => {
      if (finalGroups[k].length > 1) {
          const root = finalGroups[k][0];
          const children = finalGroups[k].slice(1).sort((a,b) => b.created - a.created);
          finalGroups[k] = [root, ...children];
      }
  });

  return finalGroups;
}

export function groupByDateAndIntelligence(items: any[], isGroupingEnabled: boolean) {
  const dates: any[] = [];
  if (items.length === 0) return dates;
  
  let currentDateKey: string | null = null;
  let currentItems: any[] = [];
  
  for (const r of items) {
    const dateKey = r.yy && r.mm && r.dd ? `${r.yy}-${r.mm}-${r.dd}` : 'unknown';
    
    if (currentDateKey === null) {
      currentDateKey = dateKey;
    }
    
    if (dateKey !== currentDateKey) {
      dates.push({
        header: currentDateKey !== 'unknown' && currentItems.length > 0 ? getDateHeader(currentItems[0].yy, currentItems[0].mm, currentItems[0].dd) : null,
        dateKey: currentDateKey,
        groupedItems: groupIntelligently(currentItems, isGroupingEnabled)
      });
      currentDateKey = dateKey;
      currentItems = [];
    }
    currentItems.push(r);
  }
  
  if (currentItems.length > 0) {
    dates.push({
      header: currentDateKey !== 'unknown' ? getDateHeader(currentItems[0].yy, currentItems[0].mm, currentItems[0].dd) : null,
      dateKey: currentDateKey,
      groupedItems: groupIntelligently(currentItems, isGroupingEnabled)
    });
  }
  
  return dates;
}