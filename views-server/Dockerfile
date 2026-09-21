FROM node:20-alpine
WORKDIR /app
COPY package.json index.js ./
VOLUME ["/app/data"]
ENV PORT=3000
ENV DATA_FILE=/app/data/views.json
EXPOSE 3000
CMD ["node", "index.js"]
