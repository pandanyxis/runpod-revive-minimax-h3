# SeedVR2 Film Revive op RunPod

Deze repository bouwt een ComfyUI Docker-image voor het herstellen van oude films en clips met SeedVR2. De image bevat ComfyUI, SeedVR2, een Film Revive streaming-node, VideoHelperSuite en FFmpeg. De twee benodigde SeedVR2-modelbestanden worden op het persistente RunPod-volume opgeslagen; de image zelf bevat geen modelgewichten.

## Aanbevolen: streaming in ComfyUI

Importeer [`workflows/film-restoration-streaming.json`](workflows/film-restoration-streaming.json). Upload het hoofdbestand met `LoadVideo` links; deze node is alleen een uploadhulp en is niet verbonden met de verwerking. Ververs ComfyUI, kies hetzelfde bestand in `Film Revive • 15s streaming` en klik **Run**. De voortgangsbalk toont de delen. De nieuwe node leest rechtstreeks vanaf schijf, verwerkt maximaal 15 seconden per deel (maximaal 450 frames), schrijft doorlopend één MP4 en voegt de oorspronkelijke audio toe. Het resultaat verschijnt in `/workspace/ComfyUI/output` en in de videovoorvertoning van de node.

Deze route voorkomt dat alle frames tegelijk in ComfyUI-RAM blijven staan. Chunking vermindert het geheugengebruik; het verlaagt niet het aantal SeedVR2-berekeningen. Test eerst een kort fragment. De streamingroute gebruikt hetzelfde 3B FP16-model en de standaard doelresolutie van 1080 pixels aan de korte zijde. Sterk vervaagde of verdwenen details zijn niet exact terug te halen; vergelijk gezichten, tekst en achtergrond met het origineel.

## Oude canvasworkflow voor zeer korte clips

[`workflows/film-restoration.json`](workflows/film-restoration.json) laadt de hele video als beeldtensor. Gebruik deze workflow alleen voor zeer korte tests. Een clip van 1 minuut 50 seconden liet het systeemgeheugen oplopen en de Pod herstarten. De streamingworkflow hierboven is de standaard voor langere clips.

De standaard doelresolutie is 1080 pixels aan de korte zijde. AI kan aannemelijke details toevoegen; beoordeel de kwaliteit daarom altijd met een vergelijking met het origineel.

ComfyUI is ingesteld op een maximale upload van 4 GB (`--max-upload-size 4096`). Als de webupload toch HTTP 413 geeft of de video groter is, gebruik dan [RunPod-bestandsoverdracht](https://docs.runpod.io/pods/storage/transfer-files) om de video in `/workspace/ComfyUI/input` te zetten. De uploadgrens bepaalt niet hoeveel frames tegelijk in het geheugen passen.

## Terminalroute voor lange clips en films

Dezelfde streamingverwerking is ook beschikbaar in de Pod-terminal. Bij een normale framerate werkt die met stukken van ongeveer 15 seconden en overlappende frames tussen de delen:

```bash
film-revive-long "/workspace/ComfyUI/input/mijn-film.mp4" "/workspace/ComfyUI/output/mijn-film-restored.mp4"
```

Optioneel kies je met het derde argument de doelresolutie en met het vierde het aantal seconden per deel, bijvoorbeeld `film-revive-long INPUT OUTPUT 1080 15`. Het script zet na verwerking de oorspronkelijke audio terug. Houd genoeg vrije ruimte voor bron, tijdelijke video en resultaat; voor een uur film is 100 GB of meer op `/workspace` een verstandige start, afhankelijk van bitrate en bestandsgrootte. Test eerst één minuut van vergelijkbare kwaliteit.

## RunPod instellen

1. Wacht tot GitHub Actions **Build RunPod image** succesvol is. Gebruik daarna `ghcr.io/pandanyxis/runpod-seedvr2-film-revive:latest` als **Container Image**. Zet het GHCR-package op **Public**, zodat RunPod de image kan ophalen.
2. Stel **Expose HTTP Ports** in op `8188` en mount een persistent volume op `/workspace`. Neem minimaal 50 GB voor modellen, input en output; gebruik meer voor lange films.
3. Zet `DOWNLOAD_MODELS=1` voor de eerste start. De download is ongeveer 7,3 GB. Bestaande bestanden met de verwachte grootte worden overgeslagen. Voeg indien nodig `HF_TOKEN` als Pod environment variable toe, nooit aan Git of de workflow.
4. Open ComfyUI op poort `8188` en importeer de streamingworkflow. Een GPU met 24 GB VRAM of meer is aanbevolen voor het 3B FP16 model; het geheugenverbruik hangt ook af van de resolutie.

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
