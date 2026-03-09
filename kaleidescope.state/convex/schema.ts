import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  searches: defineTable({    
    key: v.optional(v.string()),
    indexName: v.optional(v.string()), 
    name: v.string(),
    filter: v.object({
      indexName: v.string(),
      q: v.string(),
      filters: v.array(v.object({
        attribute: v.string(),
        value: v.string()
      })),
      facets: v.array(v.string()),
      page: v.number(),
      pageLimit: v.optional(v.number())
    }),
  }),
  tasks: defineTable({
    id: v.string(),
    indexName: v.optional(v.string()), 
    status: v.union(v.literal("pending"), v.literal("running"), v.literal("done")),
    payload: v.object({}),
  }),
  bookmarks: defineTable({
    id: v.optional(v.string()),
    name: v.string(),
    asset_id: v.object({
      _id: v.optional(v.string()),
      id: v.optional(v.string()),
      type: v.string()
    }),
    indexName: v.string(),
  }),
  assets: defineTable({
    storageId: v.id("_storage"),
    source: v.string(),
    path: v.string(),
    name: v.string(),
    type: v.string(),
    size: v.optional(v.number()),
    createdAt: v.number(),
  }),
  notifications: defineTable({
    user_id: v.optional(v.string()),
    prompt_id: v.string(),
    doc_id: v.optional(v.string()),
    workflow_id: v.string(),
    status: v.string(),
    payload: v.object({
      input: v.any(),
      output: v.any(),
    }),

  })
    .index("by_prompt_id", ["prompt_id"])
    .index("by_doc_id", ["doc_id"])
    .index("by_doc_id_status", ["doc_id","status"])
    .index("by_status", ["status"])
    .index("by_user_id", ["user_id"])
    .index("by_workflow_status", ["workflow_id", "status"])
    .index("by_prompt_status", ["prompt_id", "status"]),

});
