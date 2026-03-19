# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

COPY adminfrontend/package.json adminfrontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY adminfrontend/ .
RUN yarn build

# Stage 2: Serve
FROM node:20-alpine

RUN npm install -g serve

WORKDIR /app
COPY --from=build /app/build ./build

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]
