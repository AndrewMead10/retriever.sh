#!/bin/bash

# build-and-upload.sh - Build and upload Docker images to Docker Hub
# NOTE: Docker-based deployments are deprecated for this repo.
# Usage: ./build-and-upload.sh [--no-cache] [--tag TAG]

set -e

# Default values
DOCKER_REPO="dysondunbar/retriever"
TAG="latest"
NO_CACHE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--no-cache] [--tag TAG]"
            echo "  --no-cache    Build without using cache"
            echo "  --tag TAG     Use specific tag (default: latest)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Building and uploading Docker images to Docker Hub${NC}"
echo -e "${BLUE}Repository: ${DOCKER_REPO}${NC}"
echo -e "${BLUE}Tag: ${TAG}${NC}"
echo ""

# Check if user is logged into Docker Hub
echo -e "${YELLOW}Checking Docker Hub authentication...${NC}"
if ! docker info | grep -q "Username"; then
    echo -e "${RED}❌ Not logged into Docker Hub. Please run 'docker login' first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Hub authentication confirmed${NC}"
echo ""

# Build the backend image
echo -e "${YELLOW}🔨 Building backend image...${NC}"
docker build ${NO_CACHE} -t "${DOCKER_REPO}:${TAG}" .
echo -e "${GREEN}✅ Backend image built successfully${NC}"

# Also tag as latest if different tag is provided
if [[ "$TAG" != "latest" ]]; then
    echo -e "${YELLOW}🏷️  Tagging image as latest...${NC}"
    docker tag "${DOCKER_REPO}:${TAG}" "${DOCKER_REPO}:latest"
    echo -e "${GREEN}✅ Image tagged as latest${NC}"
fi

echo ""

# Push images to Docker Hub
echo -e "${YELLOW}📤 Pushing ${DOCKER_REPO}:${TAG} to Docker Hub...${NC}"
docker push "${DOCKER_REPO}:${TAG}"
echo -e "${GREEN}✅ Successfully pushed ${DOCKER_REPO}:${TAG}${NC}"

if [[ "$TAG" != "latest" ]]; then
    echo -e "${YELLOW}📤 Pushing ${DOCKER_REPO}:latest to Docker Hub...${NC}"
    docker push "${DOCKER_REPO}:latest"
    echo -e "${GREEN}✅ Successfully pushed ${DOCKER_REPO}:latest${NC}"
fi

echo ""
echo -e "${GREEN}🎉 All images successfully built and uploaded to Docker Hub!${NC}"
echo -e "${BLUE}You can now pull the image with: docker pull ${DOCKER_REPO}:${TAG}${NC}"

# Display image size
echo ""
echo -e "${BLUE}📊 Image information:${NC}"
docker images "${DOCKER_REPO}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
