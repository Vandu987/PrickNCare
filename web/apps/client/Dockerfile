FROM node:20-alpine
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

# Copy monorepo root files
COPY ../../package.json ../../pnpm-lock.yaml ../../pnpm-workspace.yaml ./
COPY ../../packages ./packages
COPY . ./apps/client

# Install deps
RUN pnpm install --filter client...

# Build
WORKDIR /app/apps/client
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

EXPOSE 3000
ENV PORT=3000
CMD ["pnpm", "start"]
