
# JSONAV: Story-to-Video Pipeline

Overview: 

[![Overview Video](https://img.youtube.com/vi/gdUFP1PiTAI/0.jpg)](https://youtu.be/gdUFP1PiTAI)

Now you too can make horrible AI videos with Gradio interface like this "spongebob" episode from heck: 

[![Watch the demo on YouTube](https://img.youtube.com/vi/U5LVftuDb5g/0.jpg)](https://youtu.be/U5LVftuDb5g)

JSONAV is an Gradio based automated app that generates a complete video with AI-generated narration, actor voices, and images based on a story structure provided in JSON format. The app combines several AI tools to bring a text-based story to life, including text-to-speech (TTS), image generation (using Stable Diffusion), and JSON-based structured storytelling.

## Overview of How It Works

### 1. **Story Creation: LM Studio as a Local AI Server**
The core of the app revolves around the structured JSON format for storytelling. To generate the initial story, you need a local AI model that can convert a story prompt into a JSON format. 

We recommend using **LM Studio** with a model such as `gemma-2-9b-it-Q4_K_M.gguf` to act as a local server for text generation. 

Here’s how to set up LM Studio:
- Download and install [LM Studio](https://lmstudio.ai/).
- Load a compatible model (e.g., `gemma-2-9b-it-Q4_K_M.gguf`) into LM Studio.
- The app will send requests to the local server to generate the structured JSON story based on the provided prompt.

The JSON output follows this structure:

```json
{
  "story_title": "Title of the Story",
  "author": "Author's Name",
  "genre": "Genre of the Story",
  "style": "Narrative Style",
  "actors": [
    {
      "name": "Actor Name",
      "description": "Physical or behavioral description of the actor.",
      "voice_type": "Male or Female"
    }
  ],
  "scenes": [
    {
      "scene_number": 1,
      "description": "Description of the scene.",
      "narration": "Narrative content providing context or moving the story forward.",
      "actors_in_scene": [
        {
          "name": "Actor Name",
          "dialogue": "Dialogue spoken by the actor."
        }
      ]
    }
  ]
}
```

Each story is divided into scenes, with characters, dialogues, and descriptions. The AI server produces this JSON format from the story prompt provided by the user.

### 2. **Image Generation with Stable Diffusion**
Once the story is generated, the app uses Stable Diffusion to create images for each scene and portraits for the actors. By default, **Stable Diffusion v2.1** is used to generate the images based on scene descriptions and character descriptions.

- The image creation process loads the required models automatically from Hugging Face when the app is first run.
- **Important:** These files are large and may take some time to download, so patience is required during the first execution.
  
For each scene, the app generates:
- **Scene Images:** Based on the description provided in the JSON.
- **Actor Portraits:** Generated from the descriptions of the actors in the JSON file.

### 3. **Voice Generation with Edge TTS**
For narration and character dialogue, the app uses **Edge TTS**. This enables realistic voice synthesis based on the character's gender and the voice type specified in the JSON. Here’s how it works:
- The narration for each scene is generated using a neutral voice.
- Each character in the scene has their own voice (male or female) based on the `voice_type` field in the JSON.
  
Edge TTS processes both the narration and dialogue, generating MP3 files for each character and scene.

### 4. **Stitching It All Together**
Once the assets are generated:
- The scene images, actor portraits, and audio files are stitched together into a final video using `moviepy`.
- The duration of each scene is determined by the length of the narration.
- Actor dialogues are layered on top of the scene, with the respective actor portraits displayed while the dialogue plays.

The app also supports an optional **screen shake effect**, which can be enabled or disabled during video generation. The screen shake adds intensity to certain scenes or actor portraits for dramatic effect.

### 5. **Archiving the Project**
After the video is created, the app automatically archives all project files (story JSON, images, and audio) and stores them in a timestamped folder under the `saved_projects` directory. This way, you can revisit and modify the project if needed.

---

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/anttiluode/jsonavgradio.git
   cd jsonavgradio
   ```

2. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install and set up LM Studio (required for story generation):
   - Download and install [LM Studio](https://lmstudio.ai/).
   - Load a compatible model (e.g., `gemma-2-9b-it-Q4_K_M.gguf`).

4. Run the app:
   ```bash
   python app.py

   ```
   Open http://127.0.0.1:7860/ web page to see the gradio app. 


   When running for the first time, the app will automatically download necessary models from Hugging Face, including the Stable Diffusion model used for image generation.

## I added stitch.py - What it does. 

Stitch.py is another way of doing stories. You can generate the story with AI like ChatGPT (that understands the format the best when you 
copy and paste to it example of how the schema works). Then you can put that to output_json/story.json folder. Then once you load stitch.py
with python stitch.py and open the http://127.0.0.1:7860/ gradio page. You can generate stories without using LM Studio, but do note if you 
have files in organized_assets tts_output output_images empty them first so the stitching process wont use images / sounds from previous 
projects as the stitch.py does not clean folders like the app.py in the beginning (beacuse we want to have story.json for example if 
app.py could not read it. I use this because lm studio does not always produce good story.json files and i can ask chatgpt to fix them 
and generate the story even when lm_studio story.json is erronous. 

---

## Prompting tips

If you want the ai to write a long story, describe how many scenes you want. Like 30 scenes. To have that 
long script, you have to have really long context window though. You can change that in LM studio. If you 
have trouble with running out of memory, you can turn off lm studio (eject ai model) after the story has been 
generated as the lm studio ai model is not needed when images are being generated. 

---

## What should be implemented

This version uses stable diffusion 2-1 just for easy install. But naturally it would work better with flux. 
On the comfyui version I usually use fluxNF4 for image generation. My graphics card (3060ti 12 gigs) puts a 
upper limit on what i can use for generation. But if you have a beefy card, feel free to replace the image 
generation with what ever - even video generation AI. ChatGPT can easily change the app to do that if you 
paste or attach the app.py to it. It is good idea to use the mp3 length to set the length of the scene. 

It would be cool if the jsonav format files could be shared, if there was some sort of web page perhaps 
where they could be re rendered, forked, where AI would understand the scheme well enough that it could be 
told to change X. Where AI voices were perhaps deepfake voices that could be changed etc. It is all doable, 
just takes time. 

---

## JSONAV Format

The entire process revolves around the **JSON** structure, which consists of:
- **Title, Author, Genre, Style**: Metadata about the story.
- **Actors**: List of characters in the story with descriptions and voice types.
- **Scenes**: Contains scene descriptions, narration, and character dialogues.

The JSON structure allows the app to generate media assets that match the content of the story precisely.

---

### External Tools
- **LM Studio**: A local AI server to handle story generation.
- **Stable Diffusion**: For image generation.
  
You can find all dependencies in the `requirements.txt` file.

---

### Possible Errors and their causes

Errors usually are either due to AI served by LM studio not following the JsonAV schema such as adding text to the beginning 
or to the ending. There was a error that AI might write dialogue to be empty "". In those bits the stiching would fail. I 
added a thing to the code where pydub creates a silent mp3 and those are stitched togeter where the mp3 fails (is 0 bytes)


---

## Conclusion

The JSONAV app is a complete pipeline for turning a story prompt into an engaging video with AI-generated narration, dialogue, and images. By leveraging state-of-the-art AI tools like LM Studio, Stable Diffusion, and Edge TTS, JSONAV automates the entire process while allowing users to archive and revisit their projects at any time. 
