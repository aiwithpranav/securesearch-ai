# The website as a container, for a real deployment (docker-compose.prod.yml). For development you do not need this:
# run `npm run dev` in the frontend folder instead.
FROM node:24-slim

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The public address of the API is built into the website. It is a URL, not a secret.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

ENV NODE_ENV=production
USER node
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
