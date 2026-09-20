FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04
LABEL org.opencontainers.image.source="https://github.com/pandanyxis/runpod-seedvr2-film-revive"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    COMFYUI_DIR=/opt/ComfyUI \
    DATA_DIR=/workspace/ComfyUI

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git ffmpeg ca-certificates tini \
    libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/* && \
    python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

RUN pip install --upgrade pip && \
    pip install torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 \
      --index-url https://download.pytorch.org/whl/cu128

ARG COMFYUI_REF=5ba116a40f1944f64e2e4a8ace826656e6293bf4
ARG VHS_REF=4d907bee61e92c2e65af3bd6383a4e4d356126d1
ARG SEEDVR2_REF=4490bd1f482e026674543386bb2a4d176da245b9

RUN git clone https://github.com/Comfy-Org/ComfyUI.git "$COMFYUI_DIR" && \
    git -C "$COMFYUI_DIR" checkout "$COMFYUI_REF" && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git "$COMFYUI_DIR/custom_nodes/ComfyUI-VideoHelperSuite" && \
    git -C "$COMFYUI_DIR/custom_nodes/ComfyUI-VideoHelperSuite" checkout "$VHS_REF" && \
    git clone https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git "$COMFYUI_DIR/custom_nodes/ComfyUI-SeedVR2_VideoUpscaler" && \
    git -C "$COMFYUI_DIR/custom_nodes/ComfyUI-SeedVR2_VideoUpscaler" checkout "$SEEDVR2_REF" && \
    pip install -r "$COMFYUI_DIR/requirements.txt" && \
    pip install -r "$COMFYUI_DIR/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt" && \
    pip install -r "$COMFYUI_DIR/custom_nodes/ComfyUI-SeedVR2_VideoUpscaler/requirements.txt" && \
    pip install 'huggingface_hub[cli]>=0.35,<2' copyparty==1.20.24

COPY scripts/entrypoint.sh /usr/local/bin/film-revive-entrypoint
COPY scripts/download-models.py /usr/local/bin/film-revive-download-models
COPY scripts/restore-long-video.sh /usr/local/bin/film-revive-long
COPY scripts/restore-long-video.py /usr/local/bin/film-revive-long.py
COPY custom_nodes/ComfyUI-FilmRevive "$COMFYUI_DIR/custom_nodes/ComfyUI-FilmRevive"
COPY models.json /opt/film-revive/models.json
RUN chmod +x /usr/local/bin/film-revive-entrypoint /usr/local/bin/film-revive-download-models /usr/local/bin/film-revive-long /usr/local/bin/film-revive-long.py

WORKDIR /opt/ComfyUI
EXPOSE 8188 3923
ENTRYPOINT ["/usr/bin/tini", "-s", "--", "/usr/local/bin/film-revive-entrypoint"]
