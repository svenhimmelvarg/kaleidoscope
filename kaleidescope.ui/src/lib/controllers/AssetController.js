import { api } from "../../convex/_generated/api.js";
import { getConvexUrl, replaceHostPort } from "../functions/convex_helpers.js";

class AssetController {
  constructor(client, invokeController) {
    this.client = client;
   
  }

  async upload(file, source, filename, docId, field  ) {
    try {
      console.log("AssetController:upload:", file.name, file.type, file.size);
      
      const uploadUrl = await this.client.mutation(api.assets.generateUploadUrl, {});
      
      // Parse the uploadUrl to dynamically determine the old host to replace
      const parsedUploadUrl = new URL(uploadUrl);
      const oldHost = `${parsedUploadUrl.hostname}${parsedUploadUrl.port ? ':' + parsedUploadUrl.port : ''}`;
      
      const response = await fetch(replaceHostPort(uploadUrl, oldHost, getConvexUrl()), {
        method: 'POST',
        headers: { 'Content-Type': file.type },
        body: file,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status: ${response.status}`);
      }

      const { storageId } = await response.json();
      
      const path = `input/datavelt/${filename}`;
      const assetId = await this.client.mutation(api.assets.save, {
        storageId,
        source,
        path,
        name: file.name,
        type: file.type,
        size: file.size,
      });
      
      console.log("AssetController:upload:success:", storageId, assetId);

      // Call prompt with the virtual path

      console.log("AssetController:prompt:success:");
      
      return { storageId, assetId};
    } catch (error) {
      console.error("AssetController:upload:error:", error);
      throw error;
    }
  }
}

export default new AssetController();

export function createAssetController(client) {
  return new AssetController(client);
}