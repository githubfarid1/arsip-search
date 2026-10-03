FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 8081
CMD ["npm", "start", "--", "-p", "8081"]
