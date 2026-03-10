import { api } from "../../convex/_generated/api.js";

class BookmarkController {
  constructor(client) {
    this.client = client;
  }

  async create(bookmarkData) {
    try {
      console.error("BookmarkController:create:", bookmarkData);
      const bookmarkId = await this.client.mutation(api.bookmarks.create, bookmarkData);
      return bookmarkId;
    } catch (error) {
      console.error("BookmarkController:create:", error);
      throw error;
    }
  }

  async update(_id, updateData) {
    try {
      const bookmark = await this.client.mutation(api.bookmarks.update, {
        _id,
        ...updateData
      });
      return bookmark;
    } catch (error) {
      console.error("BookmarkController:update:", error);
      throw error;
    }
  }

  async delete(_id) {
    try {
      await this.client.mutation(api.bookmarks._delete, { _id });
    } catch (error) {
      console.error("BookmarkController:delete:", error);
      throw error;
    }
  }

  async get(_id) {
    try {
      const bookmark = await this.client.query(api.bookmarks.get, { _id });
      return bookmark;
    } catch (error) {
      console.error("BookmarkController:get:", error);
      throw error;
    }
  }

  async getAll() {
    try {
      const bookmarks = await this.client.query(api.bookmarks.getAll);
      return bookmarks;
    } catch (error) {
      console.error("BookmarkController:getAll:", error);
      throw error;
    }
  }
}

export default new BookmarkController();

export function createBookmarkController(client) {
  return new BookmarkController(client);
}