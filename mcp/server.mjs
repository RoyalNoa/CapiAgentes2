import { McpServer, ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ErrorCode, McpError } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const server = new McpServer({
  name: 'capi-mcp-server',
  version: '0.1.0'
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

const CANDIDATE_ROOTS = [
  { id: 'docs', title: 'Project documentation', description: 'Markdown docs in the repo docs directory', absolutePath: path.join(REPO_ROOT, 'docs') },
  { id: 'backend', title: 'Backend sources', description: 'Python services under Backend/src', absolutePath: path.join(REPO_ROOT, 'Backend', 'src') },
  { id: 'frontend', title: 'Frontend sources', description: 'Next.js app under Frontend/src', absolutePath: path.join(REPO_ROOT, 'Frontend', 'src') }
];

const allowedRoots = [];
for (const root of CANDIDATE_ROOTS) {
  try {
    const stats = await fs.stat(root.absolutePath);
    if (stats.isDirectory()) {
      allowedRoots.push(root);
    }
  } catch (error) {
    // Directory not present; ignore
  }
}

if (allowedRoots.length === 0) {
  console.warn('[capi-mcp-server] No candidate directories were found. Tools will error until at least one root exists.');
}

const ROOT_MAP = new Map(allowedRoots.map(root => [root.id, root]));

const TEXT_EXTENSIONS = new Set([
  '.md',
  '.mdx',
  '.txt',
  '.json',
  '.yaml',
  '.yml',
  '.toml',
  '.ini',
  '.cfg',
  '.py',
  '.ts',
  '.tsx',
  '.js',
  '.jsx',
  '.mjs',
  '.cjs'
]);

const DEFAULT_MAX_BYTES = 20000;
const DEFAULT_LIST_LIMIT = 50;
const DEFAULT_MAX_SEARCH_RESULTS = 25;
const DEFAULT_MAX_SEARCH_FILES = 150;

server.registerTool(
  'list-project-files',
  {
    title: 'List project files',
    description: 'List directory entries from selected project roots to help the model navigate the repository.',
    inputSchema: {
      root: z.string().optional(),
      relativePath: z.string().optional(),
      includeSubdirectories: z.boolean().optional(),
      limit: z.number().int().min(1).max(500).optional()
    },
    outputSchema: {
      root: z.string(),
      relativePath: z.string(),
      truncated: z.boolean(),
      items: z.array(
        z.object({
          type: z.enum(['file', 'directory']),
          name: z.string(),
          path: z.string(),
          size: z.number().int().nullable(),
          modified: z.string().nullable()
        })
      )
    }
  },
  async ({ root, relativePath = '.', includeSubdirectories = false, limit = DEFAULT_LIST_LIMIT }) => {
    const targetRoot = getRoot(root);
    const normalizedRelative = normalizeRelativePath(relativePath);
    const resolvedPath = path.resolve(targetRoot.absolutePath, normalizedRelative || '.');

    const stats = await safeStat(resolvedPath);
    if (!stats || !stats.isDirectory()) {
      throw new McpError(ErrorCode.InvalidParams, `The path \'${normalizedRelative || '.'}\' is not a directory within the ${targetRoot.id} root.`);
    }

    const { items, truncated } = await listDirectoryEntries({
      basePath: targetRoot.absolutePath,
      startPath: resolvedPath,
      relativeBase: normalizedRelative || '',
      includeSubdirectories,
      limit
    });

    const displayPath = normalizedRelative === '' ? '.' : normalizedRelative;

    return {
      content: [
        {
          type: 'text',
          text: `Listed ${items.length} entr${items.length === 1 ? 'y' : 'ies'} under ${targetRoot.id}:${displayPath}${truncated ? ' (results truncated)' : ''}.`
        }
      ],
      structuredContent: {
        root: targetRoot.id,
        relativePath: displayPath,
        truncated,
        items
      }
    };
  }
);

server.registerTool(
  'read-project-file',
  {
    title: 'Read project file',
    description: 'Load the contents of a text file from the configured project roots with size safeguards.',
    inputSchema: {
      root: z.string().optional(),
      relativePath: z.string(),
      maxBytes: z.number().int().min(256).max(200000).optional()
    },
    outputSchema: {
      root: z.string(),
      relativePath: z.string(),
      truncated: z.boolean(),
      size: z.number().int(),
      content: z.string()
    }
  },
  async ({ root, relativePath, maxBytes = DEFAULT_MAX_BYTES }) => {
    const targetRoot = getRoot(root);
    const normalizedRelative = normalizeRelativePath(relativePath);
    const resolvedPath = path.resolve(targetRoot.absolutePath, normalizedRelative);

    if (!isPathWithinRoot(resolvedPath, targetRoot.absolutePath)) {
      throw new McpError(ErrorCode.InvalidParams, 'Requested path is outside the allowed root directory.');
    }

    const fileStats = await safeStat(resolvedPath);
    if (!fileStats || !fileStats.isFile()) {
      throw new McpError(ErrorCode.InvalidParams, `The path \'${normalizedRelative}\' is not a readable file.`);
    }

    if (!isRecognizedTextFile(resolvedPath)) {
      throw new McpError(ErrorCode.InvalidParams, 'Only text-based files can be read through this tool.');
    }

    const size = fileStats.size;
    let content = await fs.readFile(resolvedPath, 'utf-8');
    let truncated = false;
    if (Buffer.byteLength(content, 'utf-8') > maxBytes) {
      content = content.slice(0, maxBytes);
      truncated = true;
    }

    return {
      content: [
        {
          type: 'text',
          text: truncated
            ? `Read first ${Buffer.byteLength(content, 'utf-8')} bytes from ${targetRoot.id}:${normalizedRelative} (file is ${size} bytes).`
            : `Read ${size} bytes from ${targetRoot.id}:${normalizedRelative}.`
        },
        {
          type: 'text',
          text: content
        }
      ],
      structuredContent: {
        root: targetRoot.id,
        relativePath: normalizedRelative,
        size,
        truncated,
        content
      }
    };
  }
);

server.registerTool(
  'search-project-files',
  {
    title: 'Search project files',
    description: 'Search for a text fragment inside text files under the configured project roots.',
    inputSchema: {
      root: z.string().optional(),
      relativePath: z.string().optional(),
      query: z.string().min(2),
      caseSensitive: z.boolean().optional(),
      maxResults: z.number().int().min(1).max(100).optional(),
      maxFiles: z.number().int().min(1).max(500).optional()
    },
    outputSchema: {
      root: z.string(),
      relativePath: z.string(),
      query: z.string(),
      matches: z.array(
        z.object({
          path: z.string(),
          lineNumber: z.number().int(),
          preview: z.string()
        })
      ),
      truncated: z.boolean()
    }
  },
  async ({
    root,
    relativePath = '.',
    query,
    caseSensitive = false,
    maxResults = DEFAULT_MAX_SEARCH_RESULTS,
    maxFiles = DEFAULT_MAX_SEARCH_FILES
  }) => {
    const targetRoot = getRoot(root);
    const normalizedRelative = normalizeRelativePath(relativePath);
    const resolvedPath = path.resolve(targetRoot.absolutePath, normalizedRelative || '.');

    const stats = await safeStat(resolvedPath);
    if (!stats || !stats.isDirectory()) {
      throw new McpError(ErrorCode.InvalidParams, `The path \'${normalizedRelative || '.'}\' is not a directory within the ${targetRoot.id} root.`);
    }

    const { items } = await listDirectoryEntries({
      basePath: targetRoot.absolutePath,
      startPath: resolvedPath,
      relativeBase: normalizedRelative || '',
      includeSubdirectories: true,
      limit: maxFiles
    });

    const needle = caseSensitive ? query : query.toLowerCase();
    const matches = [];
    for (const item of items) {
      if (item.type !== 'file') {
        continue;
      }
      const absoluteFile = path.resolve(targetRoot.absolutePath, item.path.replace(/\\/g, path.sep));
      if (!isRecognizedTextFile(absoluteFile)) {
        continue;
      }

      const content = await fs.readFile(absoluteFile, 'utf-8');
      const lines = content.split(/\r?\n/);
      for (let index = 0; index < lines.length; index += 1) {
        const line = lines[index];
        const haystack = caseSensitive ? line : line.toLowerCase();
        if (haystack.includes(needle)) {
          matches.push({
            path: toPosixPath(path.join(targetRoot.id, item.path)),
            lineNumber: index + 1,
            preview: extractSnippet(line, needle, caseSensitive)
          });
          if (matches.length >= maxResults) {
            break;
          }
        }
      }
      if (matches.length >= maxResults) {
        break;
      }
    }

    const truncated = matches.length >= maxResults;
    return {
      content: [
        {
          type: 'text',
          text: matches.length
            ? `Found ${matches.length} match${matches.length === 1 ? '' : 'es'} for \"${query}\" under ${targetRoot.id}:${normalizedRelative || '.'}.`
            : `No matches for \"${query}\" under ${targetRoot.id}:${normalizedRelative || '.'}.`
        }
      ],
      structuredContent: {
        root: targetRoot.id,
        relativePath: normalizedRelative || '.',
        query,
        matches,
        truncated
      }
    };
  }
);

for (const root of allowedRoots) {
  server.registerResource(
    root.id,
    new ResourceTemplate(`${root.id}://{+path}`),
    {
      title: root.title,
      description: `Base URI for files in ${root.description}.`
    },
    async (uri, variables) => {
      const requestedPath = typeof variables.path === 'string' ? variables.path : '';
      const normalized = normalizeRelativePath(requestedPath || '.');
      const resolved = path.resolve(root.absolutePath, normalized || '.');
      const stats = await safeStat(resolved);
      if (!stats) {
        throw new McpError(ErrorCode.InvalidParams, 'Resource path not found.');
      }
      if (stats.isDirectory()) {
        const { items } = await listDirectoryEntries({
          basePath: root.absolutePath,
          startPath: resolved,
          relativeBase: normalized || '',
          includeSubdirectories: false,
          limit: DEFAULT_LIST_LIMIT
        });
        return {
          contents: [
            {
              uri: uri.href,
              text: JSON.stringify({ type: 'directory', items }, null, 2)
            }
          ]
        };
      }
      if (!isRecognizedTextFile(resolved)) {
        throw new McpError(ErrorCode.InvalidParams, 'Only text files are exposed as resources.');
      }
      const text = await fs.readFile(resolved, 'utf-8');
      return {
        contents: [
          {
            uri: uri.href,
            text
          }
        ]
      };
    }
  );
}

const transport = new StdioServerTransport();
await server.connect(transport);

process.on('SIGINT', async () => {
  await transport.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await transport.close();
  process.exit(0);
});

function getRoot(requestedRoot) {
  if (requestedRoot) {
    const root = ROOT_MAP.get(requestedRoot);
    if (!root) {
      throw new McpError(ErrorCode.InvalidParams, `The root \'${requestedRoot}\' is not available.`);
    }
    return root;
  }
  if (!allowedRoots.length) {
    throw new McpError(ErrorCode.InternalError, 'No project roots are configured for this server.');
  }
  return allowedRoots[0];
}

function normalizeRelativePath(relativePath) {
  const replaced = (relativePath ?? '.').replace(/\\/g, '/');
  if (!replaced || replaced === '.') {
    return '';
  }
  if (replaced.startsWith('/')) {
    throw new McpError(ErrorCode.InvalidParams, 'Paths must be relative to the selected root.');
  }
  const segments = [];
  for (const segment of replaced.split('/')) {
    if (!segment || segment === '.') {
      continue;
    }
    if (segment === '..') {
      throw new McpError(ErrorCode.InvalidParams, 'Path traversal is not allowed.');
    }
    segments.push(segment);
  }
  return segments.join('/');
}

async function safeStat(targetPath) {
  try {
    return await fs.stat(targetPath);
  } catch (error) {
    return undefined;
  }
}

function isPathWithinRoot(targetPath, rootPath) {
  const normalizedRoot = path.resolve(rootPath);
  const normalizedTarget = path.resolve(targetPath);
  return normalizedTarget === normalizedRoot || normalizedTarget.startsWith(`${normalizedRoot}${path.sep}`);
}

function isRecognizedTextFile(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (!extension) {
    return false;
  }
  return TEXT_EXTENSIONS.has(extension);
}

function toPosixPath(value) {
  return value.replace(/\\/g, '/');
}

async function listDirectoryEntries({ basePath, startPath, relativeBase, includeSubdirectories, limit }) {
  const queue = [
    {
      directory: startPath,
      relative: relativeBase ? relativeBase : ''
    }
  ];
  const items = [];
  let truncated = false;

  while (queue.length > 0 && items.length < limit) {
    const { directory, relative } = queue.shift();
    const entries = await fs.readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));

    for (const entry of entries) {
      if (items.length >= limit) {
        truncated = true;
        break;
      }

      const entryRelative = relative ? path.join(relative, entry.name) : entry.name;
      const entryAbsolute = path.resolve(basePath, entryRelative);
      const entryStats = await safeStat(entryAbsolute);
      const item = {
        type: entry.isDirectory() ? 'directory' : 'file',
        name: entry.name,
        path: toPosixPath(entryRelative),
        size: entryStats && entryStats.isFile() ? entryStats.size : null,
        modified: entryStats ? entryStats.mtime.toISOString() : null
      };
      items.push(item);

      if (entry.isDirectory() && includeSubdirectories) {
        queue.push({ directory: entryAbsolute, relative: entryRelative });
      }
    }
  }

  if (queue.length > 0) {
    truncated = true;
  }

  return { items, truncated };
}

function extractSnippet(line, needle, caseSensitive) {
  const haystack = caseSensitive ? line : line.toLowerCase();
  const index = haystack.indexOf(needle);
  if (index === -1) {
    return line.trim().slice(0, 200);
  }
  const start = Math.max(0, index - 40);
  const end = Math.min(line.length, index + needle.length + 40);
  const snippet = line.slice(start, end).trim();
  return snippet.length > 200 ? `${snippet.slice(0, 200)}…` : snippet;
}