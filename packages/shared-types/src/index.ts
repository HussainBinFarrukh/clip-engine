export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  database: string;
  redis: string;
};
