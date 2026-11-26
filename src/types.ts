export type Source = "Hugging Face" | "Kaggle" | "UCI";

export interface Dataset {
  id: string;
  name: string;
  source: Source;
  description: string | null;
  url: string;
  task_types: string[];
  domain: string | null;
  features: string[];
  target: string | null;
  data_type: string | null;
  license: string | null;
  size_bytes: number | null;
  rows: number | null;
  downloads: number | null;
  download_url: string | null;
}

export interface Recommendation {
  dataset: Dataset;
  score: number;
  factors: Record<string, number>;
  compatibility: { status: string; compatible: boolean; details: string };
  quality: {
    score: number;
    assessment: string;
    limitations: string[];
    indicators: Record<string, boolean>;
    content_inspected: boolean;
  };
  explanation: string;
}

export interface SearchResponse {
  requirements: { task_type: string; domain: string | null; keywords: string[] };
  results: Recommendation[];
  providers: Record<string, string>;
}
