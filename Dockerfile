# FunPod — RunPod gaming pod manager
FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client libgl1-mesa-glx libglib2.0-0 libegl1 \
    libxkbcommon0 libdbus-1-3 xvfb && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
VOLUME ["/workspace"]
ENV DISPLAY=:99
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & python funpod.py"]
