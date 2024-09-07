
# JSONAV: Story-to-Video Pipeline

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
   git clone https://github.com/yourusername/jsonav.git
   cd jsonav
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

   When running for the first time, the app will automatically download necessary models from Hugging Face, including the Stable Diffusion model used for image generation.

---

## JSONAV Format

The entire process revolves around the **JSON** structure, which consists of:
- **Title, Author, Genre, Style**: Metadata about the story.
- **Actors**: List of characters in the story with descriptions and voice types.
- **Scenes**: Contains scene descriptions, narration, and character dialogues.

The JSON structure allows the app to generate media assets that match the content of the story precisely.

---

## Requirements

The app relies on several Python libraries and AI models. Here's an updated list of the main requirements:

### Python Packages
- `gradio`: For the user interface.
- `edge-tts`: For text-to-speech functionality.
- `diffusers`: For Stable Diffusion image generation.
- `moviepy`: For video stitching and rendering.
- `torch`, `accelerate`: For handling AI model inference.
- `requests`, `shutil`: For downloading models from Hugging Face.

### External Tools
- **LM Studio**: A local AI server to handle story generation.
- **Stable Diffusion**: For image generation.
  
You can find all dependencies in the `requirements.txt` file.

---

## Conclusion

The JSONAV app is a complete pipeline for turning a story prompt into an engaging video with AI-generated narration, dialogue, and images. By leveraging state-of-the-art AI tools like LM Studio, Stable Diffusion, and Edge TTS, JSONAV automates the entire process while allowing users to archive and revisit their projects at any time.
