class InvokeController {
  constructor() {
    this.baseUrl = '';
  }

  async prompt(id, { _id, field, value }) {
    try {
      const requestBody = [
        {
          id: _id,
          [field]: value
        }
      ];

      const invokeMethod = import.meta.env.VITE_INVOKE_METHOD || 'invoke';

      const response = await fetch(`${this.baseUrl}/workflow/${id}/${invokeMethod}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('InvokeController:prompt:', error);
      throw error;
    }
  }
}

export default new InvokeController();

export function createInvokeController() {
  return new InvokeController();
}