/**
 * ADR Educational Portal Routes (server/routes/adrs.js)
 * Reads markdown files in docs/adr/ and returns structured ADR metadata & content.
 */

const fs = require("fs");
const path = require("path");

const ADR_DIR = path.resolve(__dirname, "../../docs/adr");

function listAdrs() {
  if (!fs.existsSync(ADR_DIR)) {
    return [];
  }
  const files = fs
    .readdirSync(ADR_DIR)
    .filter((f) => f.toLowerCase().endsWith(".md"))
    .sort();

  return files.map((filename, index) => {
    const fullPath = path.join(ADR_DIR, filename);
    const content = fs.readFileSync(fullPath, "utf8");
    const firstHeading = content
      .split(/\r?\n/)
      .find((line) => line.startsWith("# "));
    const title = firstHeading
      ? firstHeading.replace(/^#\s+/, "").trim()
      : filename.replace(/\.md$/i, "");

    const statusMatch = content.match(/\*\*Trạng thái:\*\*\s*([^\n\r]+)/i);
    const authorMatch = content.match(/\*\*Tác giả:\*\*\s*([^\n\r]+)/i);

    return {
      id: `ADR-00${index + 1}`,
      filename,
      title,
      status: statusMatch ? statusMatch[1].trim() : "Accepted",
      author: authorMatch ? authorMatch[1].trim() : "Multi_Emulator Team",
      content,
    };
  });
}

module.exports = {
  listAdrs,
};
