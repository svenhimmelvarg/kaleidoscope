import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const generateUploadUrl = mutation({
  handler: async (ctx) => {
    
    const url = await ctx.storage.generateUploadUrl();
    console.log("Asset:generateUploadURLs", url )
    return url 
  },
});

export const save = mutation({
  args: {
    storageId: v.id("_storage"),
    source: v.string(),
    path: v.string(),
    name: v.string(),
    type: v.string(),
    size: v.number(),
  },
  handler: async (ctx, args) => {
    const assetId = await ctx.db.insert("assets", {
      storageId: args.storageId,
      source: args.source,
      path: args.path,
      name: args.name,
      type: args.type,
      size: args.size,
      createdAt: Date.now(),
    });
    return assetId;
  },
});

export const get = query({
  args: { storageId: v.string() },
  handler: async (ctx, args) => {
    const asset = await ctx.db
      .query("assets")
      .filter((q) => q.eq("storageId", args.storageId))
      .first();
    return asset;
  },
});

export const getUrl = query({
  args: { storageId: v.string() },
  handler: async (ctx, args) => {
    const url = await ctx.storage.getUrl(args.storageId);
    return url;
  },
});

export const getImageUrl = query({
  args: { storageId: v.string() },
  handler: async (ctx, args) => {
    const url = await ctx.storage.getUrl(args.storageId);
    return url;
  },
});
