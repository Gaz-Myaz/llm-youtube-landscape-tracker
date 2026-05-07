import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  publicChannelsSchema,
  publicRelationshipsSchema,
  publicVideosSchema,
  runMetadataSchema
} from "./schemas";

const dataDir = path.join(process.cwd(), "public", "data");

async function readJson(name: string) {
  const content = await readFile(path.join(dataDir, name), "utf-8");
  return JSON.parse(content) as unknown;
}

export async function loadSnapshots() {
  const [videos, channels, relationships, runMetadata] = await Promise.all([
    readJson("videos.json").then((data) => publicVideosSchema.parse(data)),
    readJson("channels.json").then((data) => publicChannelsSchema.parse(data)),
    readJson("relationships.json").then((data) => publicRelationshipsSchema.parse(data)),
    readJson("run-metadata.json").then((data) => runMetadataSchema.parse(data))
  ]);

  return { videos, channels, relationships, runMetadata };
}
