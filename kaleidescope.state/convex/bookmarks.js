import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const create = mutation({
  args: {
    id: v.optional(v.string()),
    name: v.optional(v.string()),
    asset_id: v.object({
      _id:v.optional(v.string()),
      id: v.string(),
      type: v.string()
    }),
    indexName: v.string(),
  },
  handler: async (ctx, args) => {
    const bookmark = {
      ...args,
      name: args.name || "default"
    };
    const id = await ctx.db.insert("bookmarks", bookmark);
    return id;
  },
});

export const update = mutation({
  args: {
    _id: v.id("bookmarks"),
    id: v.optional(v.string()),
    name: v.optional(v.string()),
    asset_id: v.optional(v.object({
      _id: v.string(),
      id: v.optional(v.string()),
      type: v.string()
    })),
    indexName: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const { _id, ...updateData } = args;
    
    const filteredUpdateData = Object.fromEntries(
      Object.entries(updateData).filter(([_, value]) => value !== undefined)
    );
    
    await ctx.db.patch(_id, filteredUpdateData);
    return await ctx.db.get(_id);
  },
});

export const _delete = mutation({
  args: { _id: v.id("bookmarks") },
  handler: async (ctx, args) => {
    await ctx.db.delete(args._id);
  },
});

export const get = query({
  args: { _id: v.id("bookmarks") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args._id);
  },
});

export const getAll = query({
  args: {
    indexName: v.optional(v.string()),
    name: v.optional(v.string())
  },
  handler: async (ctx,args) => {
    let bookmarks = []
    
    if(!args?.indexName && !args?.name){
      bookmarks  = await ctx.db.query("bookmarks").collect()
      return bookmarks
    }
    
    let query = ctx.db.query("bookmarks");
    
    if (args?.indexName && args?.name) {
      // Filter by both indexName and name
      bookmarks = await query.filter(q =>
        q.and(q.eq(q.field("indexName"), args.indexName), q.eq(q.field("name"), args.name))
      ).collect();
    } else if (args?.indexName) {
      // Filter by indexName only
      bookmarks = await query.filter(q =>
        q.eq(q.field("indexName"), args.indexName)
      ).collect();
    } else if (args?.name) {
      // Filter by name only
      bookmarks = await query.filter(q =>
        q.eq(q.field("name"), args.name)
      ).collect();
    }
    
    return bookmarks;
  },
});

