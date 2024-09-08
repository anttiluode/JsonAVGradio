import os
import json
import shutil
import requests
import asyncio
import edge_tts
from transformers import pipeline
from diffusers import StableDiffusionPipeline
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import time
from datetime import datetime
import torch
import numpy as np
import gradio as gr
import cv2
from accelerate import Accelerator
from pydub import AudioSegment

# Directories to clean or create
OUTPUT_JSON_DIR = "output_json"
TTS_OUTPUT_DIR = "tts_output"
IMAGES_OUTPUT_DIR = "output_images"
ORGANIZED_ASSETS_DIR = "organized_assets"
FINAL_VIDEO_DIR = "final_output"
SAVED_PROJECTS_DIR = "saved_projects"
SILENT_MP3_PATH = "path_to_silence.mp3"

# Ensure the saved projects directory exists
if not os.path.exists(SAVED_PROJECTS_DIR):
    os.makedirs(SAVED_PROJECTS_DIR)

# Function to create silent MP3 if it doesn't exist
def create_silent_audio_if_not_exists(duration_ms=5000, path=SILENT_MP3_PATH):
    if not os.path.exists(path):
        print(f"Silent MP3 does not exist, creating {path}...", flush=True)
        silence = AudioSegment.silent(duration=duration_ms)
        silence.export(path, format="mp3")
        print(f"Silent MP3 created at {path}", flush=True)
    else:
        print(f"Silent MP3 already exists at {path}", flush=True)

# Call the function at the start of the script to ensure the silent audio file exists
create_silent_audio_if_not_exists()

# Clean up directories at the start to avoid mix-ups from old files
def cleanup_directories(directories):
    for directory in directories:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        else:
            os.makedirs(directory)

# Step to archive the project files after video creation
def archive_project(json_story_path):
    print("Archiving project files...", flush=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    project_folder = os.path.join(SAVED_PROJECTS_DIR, f"project_{timestamp}")
    
    os.makedirs(project_folder, exist_ok=True)
    
    # Create subdirectories for assets and final output
    assets_dir = os.path.join(project_folder, "assets")
    final_video_dir = os.path.join(project_folder, "final_video")
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(final_video_dir, exist_ok=True)
    
    # Copy story JSON
    shutil.copy(json_story_path, project_folder)
    
    # Copy assets (images, audio)
    for file_name in os.listdir(ORGANIZED_ASSETS_DIR):
        shutil.copy(os.path.join(ORGANIZED_ASSETS_DIR, file_name), assets_dir)
    
    # Copy final video(s)
    for file_name in os.listdir(FINAL_VIDEO_DIR):
        shutil.copy(os.path.join(FINAL_VIDEO_DIR, file_name), final_video_dir)
    
    print(f"Project archived in {project_folder}", flush=True)

# Step 1: Story Creation Node using Local AI Server
def generate_story(prompt, model='gpt-3.5-turbo', seed=42):
    print("Starting story generation with local AI server...", flush=True)
    start_time = time.time()

    # Cleanup directories before generating
    cleanup_directories([OUTPUT_JSON_DIR, TTS_OUTPUT_DIR, IMAGES_OUTPUT_DIR, ORGANIZED_ASSETS_DIR, FINAL_VIDEO_DIR])

    # Story creation using the local server
    ai_prompt = f"""
    You are an AI tasked with generating a story in JSON format. The story should be structured according to the following schema:
    
    {{
      "story_title": "Title of the Story",
      "author": "Author's Name",
      "genre": "Genre of the Story",
      "style": "Narrative Style",
      "actors": [
        {{
          "name": "Actor Name",
          "description": "Physical or behavioral description of the actor.",
          "voice_type": "Male or Female"
        }},
        ...
      ],
      "scenes": [
        {{
          "scene_number": 1,
          "description": "Description of the scene.",
          "narration": "Narrative content providing context or moving the story forward.",
          "actors_in_scene": [
            {{
              "name": "Actor Name",
              "dialogue": "Dialogue spoken by the actor."
            }},
            ...
          ]
        }},
        ...
      ]
    }}

    Do not add anything that is not JSON to your answer.

    Story prompt: "{prompt}"
    """

    # Send request to the local AI server
    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": ai_prompt}],
            "temperature": 0.7,
            "user": {"id": f"user-{seed}"}
        }
    )

    # Parse the response from the local AI server
    response_json = response.json()
    story_json = response_json["choices"][0]["message"]["content"]

    # Save structured story as a JSON file
    json_story_path = os.path.join(OUTPUT_JSON_DIR, 'story.json')
    with open(json_story_path, 'w') as json_file:
        json.dump(json.loads(story_json), json_file, indent=4)

    print(f"Story generation completed in {time.time() - start_time:.2f} seconds.", flush=True)
    return json_story_path

# Step 2: Generate TTS and Image Prompts
async def generate_tts_and_prompts(json_story_path):
    print("Starting TTS and image prompt generation...", flush=True)
    start_time = time.time()

    with open(json_story_path, 'r') as f:
        story = json.load(f)

    # Define TTS voices
    voice_type_male = "en-US-GuyNeural"
    voice_type_female = "en-US-AriaNeural"
    voice_type_narration = "en-US-JennyNeural"

    text_prompts = []

    # TTS generation for narration and actor dialogues
    for scene in story['scenes']:
        scene_number = scene['scene_number']

        # Generate and move the narration TTS
        print(f"Generating narration TTS for scene {scene['scene_number']}...", flush=True)
        narration_audio_path = f"{TTS_OUTPUT_DIR}/scene_{scene_number:02d}_narration.mp3"
        narration_tts = edge_tts.Communicate(scene['narration'], voice_type_narration)
        await narration_tts.save(narration_audio_path)

        # Move narration TTS to organized_assets
        organized_narration_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_narration.mp3"
        shutil.move(narration_audio_path, organized_narration_path)

        for actor in scene['actors_in_scene']:
            actor_name = actor.get('name', 'Unknown').replace(" ", "_").lower()
            print(f"Generating TTS for actor {actor_name} in scene {scene['scene_number']}...", flush=True)

            actor_voice_type = actor.get('voice_type', 'Male')
            actor_voice = voice_type_male if actor_voice_type == "Male" else voice_type_female

            actor_dialogue = actor.get('dialogue', "No dialogue")
            actor_audio_path = f"{TTS_OUTPUT_DIR}/scene_{scene_number:02d}_{actor_name}.mp3"
            dialogue_tts = edge_tts.Communicate(actor_dialogue, actor_voice)
            await dialogue_tts.save(actor_audio_path)

            # Move actor dialogue TTS to organized_assets
            organized_dialogue_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_{actor_name}.mp3"
            shutil.move(actor_audio_path, organized_dialogue_path)

            # Fetch the actor's description from the main actors list
            actor_description = story['actors'][0]['description']
            print(f"Using description: {actor_description}")

            # Add actor description as prompt for image generation
            text_prompts.append(f"Portrait of {actor['name']}, {actor_description}")

        # Add scene description to prompts for image generation
        text_prompts.append(scene['description'])

    print(f"TTS and image prompt generation completed in {time.time() - start_time:.2f} seconds.", flush=True)
    return text_prompts


# image generation
def generate_and_organize_images(json_story_path):
    print("Starting image generation and organization based on story.json...", flush=True)
    start_time = time.time()

    # Load the Stable Diffusion model with acceleration
    accelerator = Accelerator()
    pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-2-1", torch_dtype=torch.float16)
    pipe = pipe.to(accelerator.device)

    # Load the story JSON to access scene numbers and prompts
    with open(json_story_path, 'r') as f:
        story = json.load(f)

    # Iterate through scenes in the story to generate images
    for scene in story['scenes']:
        scene_number = scene['scene_number']

        # Generate the scene description image
        scene_description = scene['description']
        scene_image_name = f"scene_{scene_number:02d}_description.png"
        print(f"Generating scene image for scene {scene_number}: {scene_description}")
        
        # Generate the scene image
        with accelerator.autocast():
            scene_image = pipe(scene_description).images[0]
        
        # Save and move the scene image to organized assets
        scene_image_path = f"{IMAGES_OUTPUT_DIR}/{scene_image_name}"
        scene_image.save(scene_image_path)
        shutil.move(scene_image_path, f"{ORGANIZED_ASSETS_DIR}/{scene_image_name}")
        print(f"Scene image saved as {scene_image_name}")

        # Generate and move actor portrait images for each actor in the scene
        for actor in scene['actors_in_scene']:
            actor_name = actor['name'].replace(" ", "_").lower()
            actor_description = next((a['description'] for a in story['actors'] if a['name'] == actor['name']), None)

            if actor_description:
                actor_portrait_prompt = f"Portrait of {actor['name']}, {actor_description}"
                actor_image_name = f"scene_{scene_number:02d}_{actor_name}_portrait.png"
                print(f"Generating actor portrait for {actor['name']}: {actor_description}")

                # Generate the actor portrait image
                with accelerator.autocast():
                    actor_image = pipe(actor_portrait_prompt).images[0]

                # Save and move the actor portrait to organized assets
                actor_image_path = f"{IMAGES_OUTPUT_DIR}/{actor_image_name}"
                actor_image.save(actor_image_path)
                shutil.move(actor_image_path, f"{ORGANIZED_ASSETS_DIR}/{actor_image_name}")
                print(f"Actor portrait saved as {actor_image_name}")

    print(f"Image generation and organization completed in {time.time() - start_time:.2f} seconds.", flush=True)


# Custom Screen Shake Effect Class and Function
class Screen:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.shaking = False
        self.shake_duration = 0
        self.shake_intensity = 0
        self.shake_counter = 0

    def shake(self, duration, intensity):
        self.shaking = True
        self.shake_duration = duration
        self.shake_intensity = intensity
        self.shake_counter = 0

    def update_shake(self, delta_time):
        if not self.shaking:
            return

        if self.shake_counter >= self.shake_duration:
            self.shaking = False
            self.shake_intensity = 0
            self.shake_counter = 0
            self.shake_duration = 0
            self.x = 0
            self.y = 0
            return

        shake_x = (np.random.uniform(-0.5, 0.5)) * self.shake_intensity
        shake_y = (np.random.uniform(-0.5, 0.5)) * self.shake_intensity

        self.x += shake_x
        self.y += shake_y

        self.shake_intensity *= 0.995

        self.shake_counter += delta_time

def apply_screen_shake(clip, screen, fps=24, intensity=5):
    duration = clip.duration
    screen.shake(duration=duration, intensity=intensity)
    
    def shake_frame(get_frame, t):
        frame = get_frame(t)
        screen.update_shake(1/fps)
        height, width, _ = frame.shape
        
        zoom_factor = 1.15  # Increased zoom to prevent edge visibility
        zoomed_frame = cv2.resize(frame, (0, 0), fx=zoom_factor, fy=zoom_factor)

        translation_matrix = np.float32([[1, 0, screen.x], [0, 1, screen.y]])
        shaken_frame = cv2.warpAffine(zoomed_frame, translation_matrix, (width, height))
        
        return shaken_frame
    
    return clip.fl(shake_frame)

# Step 5: Stitch assets and ensure the narration and actor audio are properly layered

# Stitch assets and ensure the narration and actor audio are properly layered
def stitch_assets(json_story_path, apply_shake_effect=False):
    print("Starting video stitching with proper audio layering...", flush=True)
    start_time = time.time()

    with open(json_story_path, 'r') as file:
        story = json.load(file)

    scene_clips = []

    # Iterate through each scene
    for scene in story['scenes']:
        scene_number = scene['scene_number']
        print(f"Stitching scene {scene_number}...", flush=True)

        # Load the scene description image
        image_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_description.png"
        if not os.path.exists(image_path):
            print(f"[ERROR] Scene image not found: {image_path}")
            continue

        # Load the narration audio
        narration_audio_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_narration.mp3"
        try:
            if os.path.exists(narration_audio_path):
                # Try to load the narration audio to get its duration
                narration_audio_clip = AudioFileClip(narration_audio_path)
                scene_duration = narration_audio_clip.duration
                print(f"Setting scene duration to match narration length: {scene_duration} seconds")
            else:
                raise FileNotFoundError(f"Narration audio file {narration_audio_path} not found.")
        except Exception as e:
            # If there's any issue with the narration audio, fallback to silent audio
            print(f"[ERROR] Narration audio error for scene {scene_number}: {e}. Using silent audio.")
            scene_duration = 5  # Set a default duration for the scene
            narration_audio_clip = AudioFileClip("path_to_silence.mp3").set_duration(scene_duration)

        # Create the scene image clip with the same duration as the narration
        scene_image_clip = ImageClip(image_path).set_duration(scene_duration)
        scene_image_clip = scene_image_clip.set_audio(narration_audio_clip)

        # Apply shake effect to the scene image clip if enabled
        if apply_shake_effect:
            print("Applying shake effect to scene image...")
            screen = Screen()
            scene_image_clip = apply_screen_shake(scene_image_clip, screen, intensity=5)  # Set shake intensity here

        # List to hold the actor dialogue clips
        actor_clips = []

        # Add each actor's dialogue with their portrait
        for actor in scene['actors_in_scene']:
            actor_name = actor['name'].replace(" ", "_").lower()

            # Load the actor's portrait
            actor_image_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_{actor_name}_portrait.png"
            if not os.path.exists(actor_image_path):
                print(f"[ERROR] Actor portrait not found: {actor_image_path}")
                continue

            # Load the actor's dialogue audio
            actor_audio_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_{actor_name}.mp3"
            try:
                if os.path.exists(actor_audio_path):
                    # Try to load the dialogue audio to get its duration
                    actor_audio_clip = AudioFileClip(actor_audio_path)
                    dialogue_duration = actor_audio_clip.duration
                    print(f"Setting actor portrait duration to match dialogue length: {dialogue_duration} seconds")
                else:
                    raise FileNotFoundError(f"Dialogue audio file {actor_audio_path} not found.")
            except Exception as e:
                # If there's any issue with the actor dialogue audio, fallback to silent audio
                print(f"[ERROR] Dialogue audio error for {actor_name} in scene {scene_number}: {e}. Using silent audio.")
                dialogue_duration = 5  # Set a default duration for actor portrait
                actor_audio_clip = AudioFileClip("path_to_silence.mp3").set_duration(dialogue_duration)

            # Create the actor portrait image clip with the same duration as the dialogue
            actor_image_clip = ImageClip(actor_image_path).set_duration(dialogue_duration)
            actor_image_clip = actor_image_clip.set_audio(actor_audio_clip)

            # Apply shake effect to the actor portrait clip if enabled
            if apply_shake_effect:
                print("Applying shake effect to actor clip...")
                screen = Screen()
                actor_image_clip = apply_screen_shake(actor_image_clip, screen, intensity=5)  # Set shake intensity here

            # Add actor clip to the list
            actor_clips.append(actor_image_clip)

        # Concatenate actor clips after the scene image
        if actor_clips:
            # Concatenate all actor dialogue clips
            actor_sequence_clip = concatenate_videoclips(actor_clips)
            final_scene_clip = concatenate_videoclips([scene_image_clip, actor_sequence_clip])
        else:
            final_scene_clip = scene_image_clip

        # Add the stitched scene clip to the list of scene clips
        scene_clips.append(final_scene_clip)

    # Concatenate all the scenes into the final video
    final_video_path = f"{FINAL_VIDEO_DIR}/final_story_video_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
    final_video = concatenate_videoclips(scene_clips)
    final_video.write_videofile(final_video_path, fps=24)

    print(f"Video stitching completed in {time.time() - start_time:.2f} seconds.", flush=True)
    return final_video_path

# Main pipeline function
def run_pipeline(story_prompt, apply_shake):
    print("Pipeline started.", flush=True)
    json_story_path = generate_story(story_prompt)
    text_prompts = asyncio.run(generate_tts_and_prompts(json_story_path))
    generate_and_organize_images(json_story_path)  # Use the correct function
    final_video_path = stitch_assets(json_story_path, apply_shake.lower() == 'yes')
    
    # Archive the project files
    archive_project(json_story_path)
    
    return final_video_path


# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# 🎬 Story to Video Generator")
    gr.Markdown("Enter a prompt, and the pipeline will generate a video with narration and images based on the story.")

    with gr.Row():
        with gr.Column():
            story_prompt = gr.Textbox(label="Enter Story Prompt", placeholder="Once upon a time in a faraway land...", lines=5)
            apply_shake = gr.Radio(choices=["yes", "no"], label="Apply shake effect?", value="no")
            submit_button = gr.Button("Generate Video 🎥")
        with gr.Column():
            video_output = gr.Video(label="Generated Story Video")

    submit_button.click(fn=run_pipeline, inputs=[story_prompt, apply_shake], outputs=video_output)

# Launch the app
demo.launch()
