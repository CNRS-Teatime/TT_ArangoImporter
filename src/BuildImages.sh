docker buildx build -t arango-importer ArangoInporter/. --platform linux/amd64,linux/arm64
docker buildx build -t clustering-utility Clustering/. --platform linux/amd64,linux/arm64