# Film Revive op RunPod

Deze repository bevat een eigen ComfyUI Docker-image en een opgeschoonde versie van de aangeleverde MiniMax H3 video workflow. De image installeert ComfyUI, KJNodes, VideoHelperSuite en FFmpeg. De drie benodigde modelbestanden komen op een persistent RunPod volume, niet in Git of de Docker-image.

## Wat de workflow doet

Upload een oude clip via `VHS_LoadVideo`, pas desgewenst de prompt aan en start de workflow. De `film-revive` output is de gegenereerde video; `film-revive-compare` toont een vergelijking. De originele audiotrack wordt doorgegeven aan de video-outputs.

**Belangrijke beperking:** de originele workflow gebruikt één frame uit de clip als beeldgids voor MiniMax H3. De rest van de frames wordt niet afzonderlijk gerestaureerd. Dit is daarom een AI reconstructie van een korte clip, geen framegetrouwe restauratie. Gezichten, beweging of details kunnen veranderen. Bekijk het resultaat per clip voordat je het gebruikt.

## Benodigdheden

- RunPod GPU Pod met bij voorkeur 80 GB VRAM voor de meegeleverde 768p workflow. Lagere resolutie of kortere clips kunnen op minder VRAM werken, maar zijn hier niet getest.
- Een persistent volume van minimaal 100 GB op `/workspace` voor circa 51 GB modellen, input, output en tijdelijke bestanden.
- Toegang tot de drie Hugging Face modelbestanden in [`models.json`](models.json); accepteer indien nodig eerst de modellicentie op Hugging Face en voeg `HF_TOKEN` toe als Pod environment variable. Deel dat token niet in GitHub of in de workflow.

## Voorbereiden op RunPod

1. Wacht tot de GitHub Actions workflow **Build RunPod image** is geslaagd. Gebruik dan `ghcr.io/pandanyxis/runpod-revive-minimax-h3:latest` als **Container Image** in een nieuwe RunPod Pod template. Het GHCR package moet **Public** staan, zodat RunPod de image zonder registry credentials kan ophalen.
2. Stel **Expose HTTP Ports** in op `8188` en mount het persistente volume op `/workspace`.
3. Zet environment variable `DOWNLOAD_MODELS=1` voor de eerste start. Voeg `HF_TOKEN` toe als de modellen toegangsbeperkt zijn. De eerste start downloadt circa 51 GB en kan lang duren. Hierna kun je `DOWNLOAD_MODELS=0` zetten; bestaande bestanden worden bij `1` ook overgeslagen.
4. Open de ComfyUI HTTP service op poort `8188`, importeer [`workflows/film-revive.json`](workflows/film-revive.json), upload je clip in `VHS_LoadVideo` en controleer de video-instellingen voor je de run start.

De oorspronkelijke workflow had een platformgebonden versleutelde node, videopreviews met persoonlijke paden en een los beeldgeneratiepad met zestien LoRA’s. Deze onderdelen zijn uit de openbare workflow gehaald. De drie H3 modellen en het pad van de clip worden na het importeren via ComfyUI geselecteerd.

## Lokaal bouwen

```bash
docker build -t film-revive:local .
docker run --gpus all -p 8188:8188 -v film-revive-data:/workspace/ComfyUI -e DOWNLOAD_MODELS=1 film-revive:local
```

Voor een RunPod network volume op `/workspace` schrijft de container naar `/workspace/ComfyUI`. Modellen staan in `models/text_encoders`, `models/diffusion_models` en `models/vae`. Invoer en uitvoer staan in `input` en `output`.

## Bronnen

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [ComfyUI KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- [ComfyUI VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [MiniMax H3 modellen](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [Hybride H3 model](https://huggingface.co/smhfacct/Minimax-H3-fl2va-ref2va-hybrid-models)
- [RunPod documentatie over container images](https://docs.runpod.io/pods/templates)
