import { api } from "../../convex/_generated/api.js";


class FilterController {

  constructor(client) {
    this.client = client;
  }

  async _delete(s_id) {
    await  this.client.mutation(api.search._delete, { id: s_id })
  }

  async save(name, searchParameters) {

    try {
      searchParameters.page = 1 
      const searchId = await this.client.mutation(api.search.create,  {
        name: name,
        filter: searchParameters
      });
      
      return searchId;
    } catch (error) {
      console.error("FilterController:save:", error);
      throw error;
    }
  }

  async getAll() {
    try {
      const searches = await this.client.query(api.search.getAll);
      return searches;
    } catch (error) {
      console.error("FilterController:getAll:", error);
      throw error;
    }
  }

  async get(id) {
    try {
      const search = await this.client.query(api.search.get, { id });
      return search;
    } catch (error) {
      console.error("FilterController:loadSearch:", error);
      throw error;
    }
  }
}

export default new FilterController();

export function createFilterController(client) {
  return new FilterController(client);
}