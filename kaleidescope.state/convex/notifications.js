import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

export const getPending = query({
  args: {
    workflow_id: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const { workflow_id } = args;
    let result
    if (workflow_id) {
      result =  await ctx.db
        .query("notifications")
        .withIndex("by_workflow_status", (q) =>
          q.eq("workflow_id", workflow_id).eq("status", "pending")
        )
        .collect();
    } else {
      result =  await ctx.db
        .query("notifications")
        .withIndex("by_status", (q) => q.eq("status", "pending"))
        .collect();
    }
    console.log("notifications:getPending:result", result.length )
    return result 
  },

  
});

export const getCompleted = query({
  args: {
    start: v.optional(v.number()),
    end: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const { start, end } = args;
    
    const now = Date.now();
    const todayStart = start || new Date(now).setHours(0, 0, 0, 0);
    const todayEnd = end || new Date(now).setHours(23, 59, 59, 999);
    
    let result =  await ctx.db
      .query("notifications")
      .withIndex("by_status", (q) => q.eq("status", "completed"))
      .filter((q) =>
        q.and(
          q.gte(q.field("_creationTime"), todayStart),
          q.lte(q.field("_creationTime"), todayEnd)
        )
      )
      .collect();

    console.log("notifications:getCompleted:result", result.length )
    return result 

  },
});

export const create = mutation({
  args: {
    user_id: v.optional(v.string()),
    prompt_id: v.string(),
    workflow_id: v.string(),
    status: v.string(),
    payload: v.object({
      input: v.any(),
      output: v.optional(v.any()),
    }),
  },
  handler: async (ctx, args) => {
    const notificationId = await ctx.db.insert("notifications", {
      user_id: args.user_id,
      prompt_id: args.prompt_id,
      workflow_id: args.workflow_id,
      status: args.status,
      payload: args.payload,
    });
    return notificationId;
  },
});

export const update = mutation({
  args: {
    id: v.id("notifications"),
    user_id: v.optional(v.string()),
    prompt_id: v.optional(v.string()),
    workflow_id: v.optional(v.string()),
    status: v.optional(v.string()),
    payload: v.optional(v.object({
      input: v.any(),
      output: v.any(),
    })),
  },
  handler: async (ctx, args) => {
    const { id, ...updateData } = args;
    
    const filteredUpdateData = Object.fromEntries(
      Object.entries(updateData).filter(([_, value]) => value !== undefined)
    );
    
    await ctx.db.patch(id, filteredUpdateData);
    return await ctx.db.get(id);
  },
});

export const get = query({
  args: { notificationId: v.id("notifications") },
  handler: async (ctx, args) => {
    const notification = await ctx.db.get(args.notificationId);
    return notification;
  },
});

export const getByUser = query({
  args: { user_id: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("notifications")
      .withIndex("by_user_id", (q) => q.eq("user_id", args.user_id))
      .collect();
  },
});

export const getByPrompt = query({
  args: { prompt_id: v.string() },
  handler: async (ctx, args) => {
    const ret =  await ctx.db
      .query("notifications")
      .withIndex("by_prompt_id", (q) => q.eq("prompt_id", args.prompt_id))
      .collect();
    console.log("notifications:getByPrompt", `${args.prompt_id}  --> ${JSON.stringify(ret)}`)
    return ret
  },
});

export const getRelatedByPrompt = query({
  args: { prompt_id: v.string() },
  handler: async (ctx, args) => {
    const results = await ctx.db
      .query("notifications")
      .withIndex("by_prompt_status", (q) =>
        q.eq("prompt_id", args.prompt_id).eq("status", "completed")
      )
      .collect();
    return results.sort((a, b) => b._creationTime - a._creationTime).slice(0, 3);
  },
});

export const getAllByDocId = query({
  args: { ids: v.array(v.string()) },
  handler: async (ctx, args) => {
    console.log("notifications.getAllByDocId:ids", args.ids)
    let results = [] 
    for( const id of args.ids){
          results.concat(await ctx.db
      .query("notifications")
      .withIndex("by_doc_id", (q) => q.eq("doc_id", id))
      .collect());
    }
    console.log("notifications.getAllByPrompt:ids", results.length)
    return results 
  },
});


export const getAll = query({
  args: { ids: v.optional(v.array(v.id("notifications"))) },
  handler: async (ctx, args) => {
    // If ids is not provided, return all pending notifications for today
    if (!args.ids || args.ids.length === 0) {
      const now = Date.now();
      const todayStart = new Date(now).setHours(0, 0, 0, 0);
      const todayEnd = new Date(now).setHours(23, 59, 59, 999);
      
      return await ctx.db
        .query("notifications")
        .withIndex("by_status", (q) => q.eq("status", "pending"))
        .filter((q) =>
          q.and(
            q.gte(q.field("_creationTime"), todayStart),
            q.lte(q.field("_creationTime"), todayEnd)
          )
        )
        .collect();
    }
    
    // If ids are provided, return those specific notifications
    const notifications = [];
    for (const id of args.ids) {
      const notification = await ctx.db.get(id);
      if (notification) {
        notifications.push(notification);
      }
    }
    return notifications;
  },
});

export const _delete = mutation({
  args: { id: v.id("notifications") },
  handler: async (ctx, args) => {
    await ctx.db.delete(args.id);
  },
});
