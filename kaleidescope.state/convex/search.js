import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// Create a new search
export const create = mutation({
  args: {
    key: v.optional(v.string()),
    name: v.string(),
    filter: v.object({
      indexName: v.string(),
      q: v.string(),
      filters: v.array(v.object({
        attribute: v.string(),
        value: v.string()
      })),
      // currentPage: v.optional(v.number()), 
      facets: v.array(v.string()),
      page: v.number(),
      pageLimit: v.optional(v.number())
    })
  },
  handler: async (ctx, args) => {
    const searchId = await ctx.db.insert("searches", {
      key: args.key,
      name: args.name,
      filter: args.filter
    });
    return searchId;
  },
});

// Get a single search by ID
export const get = query({
  args: { searchId: v.id("searches") },
  handler: async (ctx, args) => {
    const search = await ctx.db.get(args.searchId);
    return search;
  },
});

// Get searches for a specific date range
export const getForDate = query({
  args: {
    startTime: v.number(),
    endTime: v.number(),
  },
  handler: async (ctx, args) => {
    const { startTime, endTime } = args;
    
    const searches = await ctx.db
      .query("searches")
      .filter((q) =>
        q.and(
          q.gt(q.field("_creationTime"), startTime),
          q.lt(q.field("_creationTime"), endTime)
        )
      )
      .collect();
    
    return searches;
  },
});

// Get all searches
export const getAll = query({
  args: {},
  handler: async (ctx) => {
    const searches = await ctx.db.query("searches").collect();
    return searches;
  },
});

// Update an existing search
export const update = mutation({
  args: {
    id: v.id("searches"),
    key: v.optional(v.string()),
    name: v.optional(v.string()),
    filter: v.optional(v.object({})), 
    
  },
  handler: async (ctx, args) => {
    const { id, ...updateData } = args;
    
    // Remove undefined fields from update data
    const filteredUpdateData = Object.fromEntries(
      Object.entries(updateData).filter(([_, value]) => value !== undefined)
    );
    
    await ctx.db.patch(id, filteredUpdateData);
    return await ctx.db.get(id);
  },
});

// Delete a search
export const _delete = mutation({
  args: { id: v.id("searches") },
  handler: async (ctx, args) => {
    await ctx.db.delete(args.id);
  },
});
