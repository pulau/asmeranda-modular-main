"use client";

/**
 * Workflow store - menggantikan st.session_state.
 * Disimpan ke localStorage agar tidak hilang saat refresh.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

const DEFAULTS = {
  datasetId: null,
  datasetName: null,
  targetColumn: null,
  problemType: null,
  numericalColumns: [],
  categoricalColumns: [],
  featureNames: [],
  stateId: null, // hasil preprocessing
  nSamplesTrain: 0,
  nSamplesTest: 0,
  nFeatures: 0,
  modelId: null,
  modelType: null,
  metrics: null,
  cvScores: null,
  language: "id",
  clusteringResults: null,
  optimizationResults: null,
  advancedMLResults: null,
};

export const useWorkflow = create(
  persist(
    (set, get) => ({
      ...DEFAULTS,

      set: (patch) => set(patch),
      reset: () => set({ ...DEFAULTS }),
      resetPreprocessing: () =>
        set({
          stateId: null,
          targetColumn: null,
          problemType: null,
          numericalColumns: [],
          categoricalColumns: [],
          featureNames: [],
          nSamplesTrain: 0,
          nSamplesTest: 0,
          nFeatures: 0,
          modelId: null,
          modelType: null,
          metrics: null,
          cvScores: null,
          clusteringResults: null,
          optimizationResults: null,
          advancedMLResults: null,
        }),
      resetTraining: () =>
        set({
          modelId: null,
          modelType: null,
          metrics: null,
          cvScores: null,
          clusteringResults: null,
          optimizationResults: null,
          advancedMLResults: null,
        }),

      canProceedTo: (step) => {
        const s = get();
        switch (step) {
          case "eda":
            return !!s.datasetId;
          case "preprocessing":
            return (
              !!s.datasetId &&
              (s.numericalColumns.length > 0 || s.categoricalColumns.length > 0)
            );
          case "clustering":
            return !!s.stateId && !!s.problemType;
          case "training":
            return !!s.stateId && !!s.problemType;
          case "optimization":
            return !!s.stateId && !!s.problemType;
          case "shap":
          case "lime":
            return !!s.modelId;
          case "timeseries":
            return !!s.datasetId;
          case "advanced_ml":
            return !!s.stateId; // Advanced ML requires preprocessing
          default:
            return false;
        }
      },
    }),
    {
      name: "asmeranda-workflow",
      skipHydration: true,
    }
  )
);

/** Panggil sekali di client agar state localStorage termuat tanpa hydration mismatch. */
export function rehydrateWorkflow() {
  if (typeof window !== "undefined") {
    useWorkflow.persist.rehydrate();
  }
}
