# Professional multi-stage Dockerfile for Next.js
FROM node:20-bullseye AS deps
RUN corepack enable
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
COPY yarn.lock* pnpm-lock.yaml* ./

RUN npm install --legacy-peer-deps --no-audit --no-fund --include=optional
RUN npm cache clean --force

FROM node:20-bullseye AS builder
RUN corepack enable
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git build-essential python3
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE:-http://localhost:8000}
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=${NEXT_PUBLIC_GOOGLE_MAPS_API_KEY:-}
ENV NEXT_TELEMETRY_DISABLED=1
ENV GENERATE_SOURCEMAP=false
ENV LIGHTNINGCSS_IGNORE_NODE_ERROR=1
ENV NEXT_DISABLE_LIGHTNINGCSS=1

COPY --from=deps /app/package*.json ./
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm rebuild sharp --foreground-scripts || true
RUN npm run build && mkdir -p .next/static

FROM node:20-bullseye AS runner
RUN groupadd -g 1001 nodejs && useradd -m -u 1001 -g nodejs nextjs
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl tini
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV LIGHTNINGCSS_IGNORE_NODE_ERROR=1
ENV NEXT_DISABLE_LIGHTNINGCSS=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE:-http://localhost:8000}
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=${NEXT_PUBLIC_GOOGLE_MAPS_API_KEY:-}

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

RUN mkdir -p /.next && chown nextjs:nodejs /.next
RUN mkdir -p /tmp && chown nextjs:nodejs /tmp

USER nextjs

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000 || exit 1

EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "server.js"]
