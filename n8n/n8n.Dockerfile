FROM n8nio/n8n:latest

USER root
# Alpine: ставим ffmpeg через apk
RUN apk add --no-cache ffmpeg
USER node
