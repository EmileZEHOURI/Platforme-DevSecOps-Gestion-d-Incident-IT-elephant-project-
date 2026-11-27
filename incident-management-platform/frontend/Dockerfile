
FROM node:22-alpine

WORKDIR /app

# Installation reproductible des dépendances
COPY package.json package-lock.json ./

RUN npm ci

# Copie du projet frontend
COPY . .

# Adresse du backend depuis le réseau Docker
ARG API_URL=http://backend:8000
ENV API_URL=${API_URL}

# Désactiver la télémétrie Next.js
ENV NEXT_TELEMETRY_DISABLED=1

# Compilation de l'application
RUN npm run build

# Démarrage du serveur Next.js
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

EXPOSE 3000

CMD ["npm", "run", "start"]
