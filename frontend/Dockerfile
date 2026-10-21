FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN --mount=type=secret,id=platform_ca if [ -f /run/secrets/platform_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/platform_ca; fi; npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node","server.js"]
