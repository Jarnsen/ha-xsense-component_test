import { copyFile, readFile, writeFile } from "node:fs/promises";

const source = "node_modules/hls.js/dist/hls.light.min.js";
const destination =
  "custom_components/xsense/frontend/vendor/hls.light.min.js";
const sourceMapComment = "//# sourceMappingURL=hls.light.min.js.map\n";

await copyFile(source, destination);
const bundledSource = await readFile(destination, "utf8");
await writeFile(destination, bundledSource.replace(sourceMapComment, ""));
