# Film Revive op RunPod

Deze repository bevat een eigen ComfyUI Docker-image met twee workflows. **[`film-restoration.json`](workflows/film-restoration.json) is de aanbevolen route voor oude film en clips**: SeedVR2 verwerkt de originele frames als videoreeks en verbetert scherpte en details met temporele samenhang. De opgeschoonde MiniMax H3 workflow blijft beschikbaar als creatieve optie. De image installeert ComfyUI, SeedVR2, KJNodes, VideoHelperSuite en FFmpeg. Modelbestanden komen op een persistent RunPod volume, niet in Git of de Docker-image.

## Wat de workflow doet

Importeer `workflows/film-restoration.json`, upload de clip in `LoadVideo` en start de workflow. `SeedVR2VideoUpscaler` gebruikt alle geladen frames; `CreateVideo` behoudt de originele framerate en audiotrack. De output heet `film-restored`. De meegeleverde 3B FP16 variant is gekozen voor kwaliteit en heeft circa 7,3 GB aan modelbestanden.

Sterk vervaagde of verdwenen informatie is niet exact terug te halen. AI kan aannemelijke details toevoegen; vergelijk daarom gezichten, tekst en kleine voorwerpen met het origineel.

## Clips van 1 minuut tot 60 minuten

Er is geen vaste limiet in minuten, maar de ComfyUI-canvasworkflow laadt de frames als één videobatch en is daarom vooral geschikt voor korte clips. De instelling `batch_size=17` beperkt het modelgeheugen per stap, niet automatisch het geheugen dat nodig is om de hele clip te laden. Een film van 60 minuten moet via de streamingroute hieronder; die verwerkt 170 frames per stuk en laat overlappende frames de overgangen verzachten.

Start de Pod met `DOWNLOAD_MODELS=1` en `MODEL_SET=restoration`. Upload de film naar `/workspace/ComfyUI/input`, open de Pod-terminal en voer uit:

```bash
film-revive-long "/workspace/ComfyUI/input/mijn-film.mp4" "/workspace/ComfyUI/output/mijn-film-restored.mp4"
```

Een derde argument kiest de doelresolutie aan de korte zijde, bijvoorbeeld `720` wanneer 1080 te veel GPU-geheugen of tijd kost. Het script gebruikt SeedVR2 streaming, schrijft een tijdelijke video en zet daarna de oorspronkelijke audio terug. Zorg voor genoeg vrije ruimte voor bron, tijdelijke video en resultaat; voor een uur film is 100 GB of meer op `/workspace` een verstandige start, afhankelijk van de bestandsgrootte en bitrate. De verwerkingstijd hangt sterk af van GPU, bronresolutie en gewenste uitvoer en kan voor 60 minuten lang zijn. Test eerst 1 minuut van vergelijkbare kwaliteit.

De optionele [`film-revive.json`](workflows/film-revive.json) is de aangeleverde MiniMax H3 workflow. Die gebruikt één frame als gids en genereert de rest van de clip opnieuw. Dit is minder geschikt als getrouwheid aan de originele beweging en details belangrijk is. `film-revive` is de gegenereerde video; `film-revive-compare` toont een vergelijking.

## Benodigdheden

- RunPod GPU Pod met bij voorkeur 24 GB VRAM of meer voor SeedVR2 3B FP16; geheugengebruik hangt af van resolutie en clipduur. De optionele H3 workflow kan aanzienlijk meer VRAM vragen en is niet getest.
- Een persistent volume op `/workspace` van minimaal 50 GB voor SeedVR2 modellen, input, output en tijdelijke bestanden. Neem minimaal 100 GB als je ook de drie H3 modellen wilt gebruiken.
- Toegang tot de Hugging Face modelbestanden in [`models.json`](models.json); accepteer indien nodig eerst de modellicentie op Hugging Face en voeg `HF_TOKEN` toe als Pod environment variable. Deel dat token niet in GitHub of in de workflow.

## Voorbereiden op RunPod

1. Wacht tot de GitHub Actions workflow **Build RunPod image** is geslaagd. Gebruik dan `ghcr.io/pandanyxis/runpod-revive-minimax-h3:latest` als **Container Image** in een nieuwe RunPod Pod template. Het GHCR package moet **Public** staan, zodat RunPod de image zonder registry credentials kan ophalen.
2. Stel **Expose HTTP Ports** in op `8188` en mount het persistente volume op `/workspace`.
3. Zet environment variables `DOWNLOAD_MODELS=1` en `MODEL_SET=restoration` voor de eerste start. Voeg `HF_TOKEN` toe als de modellen toegangsbeperkt zijn. De eerste start downloadt circa 7,3 GB. Hierna kun je `DOWNLOAD_MODELS=0` zetten; bestaande bestanden worden bij `1` ook overgeslagen.
4. Open de ComfyUI HTTP service op poort `8188`, importeer [`workflows/film-restoration.json`](workflows/film-restoration.json), upload je clip in `LoadVideo` en controleer de resolutie. De standaard is 1080 pixels aan de korte zijde. Begin met een korte clip om kwaliteit en geheugenverbruik te beoordelen.

Voor de H3 workflow zet je `MODEL_SET=h3` en `DOWNLOAD_MODELS=1`; dit downloadt circa 51 GB. De oorspronkelijke workflow had een platformgebonden versleutelde node, videopreviews met persoonlijke paden en een los beeldgeneratiepad met zestien LoRA’s. Deze onderdelen zijn uit de openbare workflow gehaald.

## Lokaal bouwen

```bash
docker build -t film-revive:local .
docker run --gpus all -p 8188:8188 -v film-revive-data:/workspace/ComfyUI -e DOWNLOAD_MODELS=1 -e MODEL_SET=restoration film-revive:local
```

Voor een RunPod network volume op `/workspace` schrijft de container naar `/workspace/ComfyUI`. Modellen staan in `models/text_encoders`, `models/diffusion_models` en `models/vae`. Invoer en uitvoer staan in `input` en `output`.

## Bronnen

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [ComfyUI KJNodes](https://github.com/kijai/ComfyUI-KJNodes)
- [ComfyUI VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)
- [MiniMax H3 modellen](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [Hybride H3 model](https://huggingface.co/smhfacct/Minimax-H3-fl2va-ref2va-hybrid-models)
- [SeedVR2 ComfyUI nodes en voorbeeldworkflow](https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler)
- [SeedVR2 modellen](https://huggingface.co/numz/SeedVR2_comfyUI)
- [ComfyUI gids voor video upscale en restauratie](https://docs.comfy.org/tutorials/utility/video-upscale)
- [RunPod documentatie over container images](https://docs.runpod.io/pods/templates)
