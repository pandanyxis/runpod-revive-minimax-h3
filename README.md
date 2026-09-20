# SeedVR2 Film Revive op RunPod

Deze repository bouwt een ComfyUI Docker-image voor het herstellen van oude films en clips met SeedVR2. De image bevat ComfyUI, SeedVR2, VideoHelperSuite en FFmpeg. De twee benodigde SeedVR2-modelbestanden worden op het persistente RunPod-volume opgeslagen; de image zelf bevat geen modelgewichten.

## Korte clips in ComfyUI

Importeer [`workflows/film-restoration.json`](workflows/film-restoration.json), kies je video in `LoadVideo` en start de workflow. `SeedVR2VideoUpscaler` verwerkt de frames als videoreeks. `CreateVideo` neemt de oorspronkelijke framerate en audio over. De output heet `film-restored`.

De standaard doelresolutie is 1080 pixels aan de korte zijde. Test eerst een kort fragment en vergelijk vooral gezichten, tekst, achtergronden en kleine voorwerpen met het origineel. Sterk vervaagde of verdwenen details zijn niet exact terug te halen; AI kan aannemelijke details toevoegen.

ComfyUI is ingesteld op een maximale upload van 4 GB (`--max-upload-size 4096`). Als de webupload toch HTTP 413 geeft of de video groter is, gebruik dan [RunPod-bestandsoverdracht](https://docs.runpod.io/pods/storage/transfer-files) om de video in `/workspace/ComfyUI/input` te zetten. De uploadgrens bepaalt niet hoeveel frames tegelijk in het geheugen passen.

## Lange clips en films

De ComfyUI-workflow laadt alle videoframes als één batch. Voor lange clips, bijvoorbeeld 60 minuten, gebruik je de streamingroute in de Pod-terminal. Die verwerkt 170 frames per deel met overlappende frames tussen de delen:

```bash
film-revive-long "/workspace/ComfyUI/input/mijn-film.mp4" "/workspace/ComfyUI/output/mijn-film-restored.mp4"
```

Optioneel kun je als derde argument een lagere doelresolutie aan de korte zijde kiezen, bijvoorbeeld `720`. Het script zet na verwerking de oorspronkelijke audio terug. Houd genoeg vrije ruimte voor bron, tijdelijke video en resultaat; voor een uur film is 100 GB of meer op `/workspace` een verstandige start, afhankelijk van bitrate en bestandsgrootte. Test eerst één minuut van vergelijkbare kwaliteit.

## RunPod instellen

1. Wacht tot GitHub Actions **Build RunPod image** succesvol is. Gebruik daarna `ghcr.io/pandanyxis/runpod-seedvr2-film-revive:latest` als **Container Image**. Zet het GHCR-package op **Public**, zodat RunPod de image kan ophalen.
2. Stel **Expose HTTP Ports** in op `8188` en mount een persistent volume op `/workspace`. Neem minimaal 50 GB voor modellen, input en output; gebruik meer voor lange films.
3. Zet `DOWNLOAD_MODELS=1` voor de eerste start. De download is ongeveer 7,3 GB. Bestaande bestanden met de verwachte grootte worden overgeslagen. Voeg indien nodig `HF_TOKEN` als Pod environment variable toe, nooit aan Git of de workflow.
4. Open ComfyUI op poort `8188` en importeer de workflow. Een GPU met 24 GB VRAM of meer is aanbevolen voor het 3B FP16 model; het geheugenverbruik hangt ook af van de resolutie.

## Lokaal bouwen

```bash
docker build -t seedvr2-film-revive:local .
docker run --gpus all -p 8188:8188 -v film-revive-data:/workspace/ComfyUI -e DOWNLOAD_MODELS=1 seedvr2-film-revive:local
```

Het model staat in `/workspace/ComfyUI/models/SEEDVR2`; input en output staan in `/workspace/ComfyUI/input` en `/workspace/ComfyUI/output`.

## Bronnen

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [SeedVR2 ComfyUI nodes](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler)
- [SeedVR2 modellen](https://huggingface.co/numz/SeedVR2_comfyUI)
- [RunPod bestandsoverdracht](https://docs.runpod.io/pods/storage/transfer-files)
