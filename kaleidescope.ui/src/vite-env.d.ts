/// <reference types="vite/client" />

declare global {
  interface Window {
    ENV?: {
      [key: string]: string;
    };
  }
}

export {}
