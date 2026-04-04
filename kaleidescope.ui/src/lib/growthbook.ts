import { GrowthBook } from "@growthbook/growthbook";
import { writable, derived } from "svelte/store";
import features from "../../../release.json";

export const gb = new GrowthBook({
  features,
  attributes: { id: "user-123", plan: "free" }, // adjust attributes as needed
  enableDevMode: true,
});

// Reactive store that bumps whenever attributes change
const flagVersion = writable(0);

export function setUser(attrs: Record<string, any>) {
  gb.setAttributes(attrs);
  flagVersion.update((n) => n + 1);
}

export function featureOn(key: string) {
  return derived(flagVersion, () => gb.isOn(key));
}

export function featureValue(key: string, fallback: any) {
  return derived(flagVersion, () => gb.getFeatureValue(key, fallback));
}
