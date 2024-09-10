# This just stitches the story together if you generate it with something else than lm studio, like chatgpt.
# You can ask chatgpt to generate the story after pasting it the guide how to write a jsonav story. 
# Then just run this, open the gradio app and and enter the location of the json av story. (your drive output_json/story.json)
# it downloads the tts from edge TTS servers and then makes the images with stable diffusion 2.1 
# if you have not used stable diffusion before it will download the weights from hugginface. 

import os
import json
import shutil
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

# Directories
TTS_OUTPUT_DIR = "tts_output"
IMAGES_OUTPUT_DIR = "output_images"
ORGANIZED_ASSETS_DIR = "organized_assets"
FINAL_VIDEO_DIR = "final_output"
SAVED_PROJECTS_DIR = "saved_projects"
SILENT_MP3_PATH = "path_to_silence.mp3"

# Ensure the saved projects directory exists
if not os.path.exists(SAVED_PROJECTS_DIR):
    os.makedirs(SAVED_PROJECTS_DIR)

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

# Apply the shake effect to the scene or actor images
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

# Make sure to use this Screen class and the shake function in your stitching process


# Function to create silent MP3 if it doesn't exist
def create_silent_audio_if_not_exists(duration_ms=5000, path=SILENT_MP3_PATH):
    if not os.path.exists(path):
        print(f"Silent MP3 does not exist, creating {path}...", flush=True)
        silence = AudioSegment.silent(duration=duration_ms)
        silence.export(path, format="mp3")
        print(f"Silent MP3 created at {path}", flush=True)
    else:
        print(f"Silent MP3 already exists at {path}", flush=True)

create_silent_audio_if_not_exists()

# Archive the project files after video creation
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

# Generate TTS and image prompts
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

        # Generate narration TTS
        print(f"Generating narration TTS for scene {scene_number}...", flush=True)
        narration_audio_path = f"{TTS_OUTPUT_DIR}/scene_{scene_number:02d}_narration.mp3"
        narration_tts = edge_tts.Communicate(scene['narration'], voice_type_narration)
        await narration_tts.save(narration_audio_path)

        # Move narration TTS to organized_assets
        organized_narration_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_narration.mp3"
        shutil.move(narration_audio_path, organized_narration_path)

        # Generate actor dialogues and prepare prompts for images
        for actor in scene['actors_in_scene']:
            actor_name = actor['name'].replace(" ", "_").lower()
            print(f"Generating TTS for actor {actor_name} in scene {scene_number}...", flush=True)

            actor_voice = voice_type_male if actor.get('voice_type', 'Male') == "Male" else voice_type_female
            actor_audio_path = f"{TTS_OUTPUT_DIR}/scene_{scene_number:02d}_{actor_name}.mp3"
            dialogue_tts = edge_tts.Communicate(actor['dialogue'], actor_voice)
            await dialogue_tts.save(actor_audio_path)

            # Move actor dialogue TTS to organized_assets
            organized_dialogue_path = f"{ORGANIZED_ASSETS_DIR}/scene_{scene_number:02d}_{actor_name}.mp3"
            shutil.move(actor_audio_path, organized_dialogue_path)

            # Prepare actor portrait description
            actor_description = next((a['description'] for a in story['actors'] if a['name'] == actor['name']), "")
            text_prompts.append(f"Portrait of {actor['name']}, {actor_description}")

        # Prepare scene description for image generation
        text_prompts.append(scene['description'])

    print(f"TTS and image prompt generation completed in {time.time() - start_time:.2f} seconds.", flush=True)
    return text_prompts

# Generate images using Stable Diffusion
def generate_and_organize_images(json_story_path):
    print("Starting image generation and organization based on story.json...", flush=True)
    start_time = time.time()

    # Load the Stable Diffusion model
    accelerator = Accelerator()
    pipe = StableDiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-2-1", torch_dtype=torch.float16)
    pipe = pipe.to(accelerator.device)

    # Load the story JSON to access scene numbers and prompts
    with open(json_story_path, 'r') as f:
        story = json.load(f)

    # Iterate through scenes to generate images
    for scene in story['scenes']:
        scene_number = scene['scene_number']

        # Generate the scene description image
        scene_description = scene['description']
        scene_image_name = f"scene_{scene_number:02d}_description.png"
        print(f"Generating scene image for scene {scene_number}: {scene_description}")
        
        with accelerator.autocast():
            scene_image = pipe(scene_description).images[0]
        
        scene_image_path = f"{IMAGES_OUTPUT_DIR}/{scene_image_name}"
        scene_image.save(scene_image_path)
        shutil.move(scene_image_path, f"{ORGANIZED_ASSETS_DIR}/{scene_image_name}")
        print(f"Scene image saved as {scene_image_name}")

        # Generate actor portrait images
        for actor in scene['actors_in_scene']:
            actor_name = actor['name'].replace(" ", "_").lower()
            actor_description = next((a['description'] for a in story['actors'] if a['name'] == actor['name']), None)

            if actor_description:
                actor_portrait_prompt = f"Portrait of {actor['name']}, {actor_description}"
                actor_image_name = f"scene_{scene_number:02d}_{actor_name}_portrait.png"
                print(f"Generating actor portrait for {actor['name']}: {actor_description}")

                with accelerator.autocast():
                    actor_image = pipe(actor_portrait_prompt).images[0]

                actor_image_path = f"{IMAGES_OUTPUT_DIR}/{actor_image_name}"
                actor_image.save(actor_image_path)
                shutil.move(actor_image_path, f"{ORGANIZED_ASSETS_DIR}/{actor_image_name}")
                print(f"Actor portrait saved as {actor_image_name}")

    print(f"Image generation and organization completed in {time.time() - start_time:.2f} seconds.", flush=True)

# Stitch the assets
def stitch_assets(json_story_path, apply_shake_effect=False):
    print("Starting video stitching...", flush=True)
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
            narration_audio_clip = AudioFileClip(SILENT_MP3_PATH).set_duration(scene_duration)

        # Create the scene image clip with the same duration as the narration
        scene_image_clip = ImageClip(image_path).set_duration(scene_duration)
        scene_image_clip = scene_image_clip.set_audio(narration_audio_clip)

        # Apply shake effect to the scene image clip if enabled
        if apply_shake_effect:
            print("Applying shake effect to scene image...")
            screen = Screen()
            scene_image_clip = apply_screen_shake(scene_image_clip, screen, intensity=5)

        actor_clips = []

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
                    actor_audio_clip = AudioFileClip(actor_audio_path)
                    dialogue_duration = actor_audio_clip.duration
                    print(f"Setting actor portrait duration to match dialogue length: {dialogue_duration} seconds")
                else:
                    raise FileNotFoundError(f"Dialogue audio file {actor_audio_path} not found.")
            except Exception as e:
                print(f"[ERROR] Dialogue audio error for {actor_name} in scene {scene_number}: {e}. Using silent audio.")
                dialogue_duration = 5  # Set a default duration for actor portrait
                actor_audio_clip = AudioFileClip(SILENT_MP3_PATH).set_duration(dialogue_duration)

            # Create the actor portrait image clip
            actor_image_clip = ImageClip(actor_image_path).set_duration(dialogue_duration)
            actor_image_clip = actor_image_clip.set_audio(actor_audio_clip)

            # Apply shake effect to the actor portrait clip if enabled
            if apply_shake_effect:
                print("Applying shake effect to actor clip...")
                screen = Screen()
                actor_image_clip = apply_screen_shake(actor_image_clip, screen, intensity=5)

            actor_clips.append(actor_image_clip)

        if actor_clips:
            actor_sequence_clip = concatenate_videoclips(actor_clips)
            final_scene_clip = concatenate_videoclips([scene_image_clip, actor_sequence_clip])
        else:
            final_scene_clip = scene_image_clip

        scene_clips.append(final_scene_clip)

    final_video_path = f"{FINAL_VIDEO_DIR}/final_story_video_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
    final_video = concatenate_videoclips(scene_clips)
    final_video.write_videofile(final_video_path, fps=24)

    print(f"Video stitching completed in {time.time() - start_time:.2f} seconds.", flush=True)
    return final_video_path

# Main pipeline function
def run_pipeline(json_story_path, apply_shake):
    print("Pipeline started.", flush=True)
    asyncio.run(generate_tts_and_prompts(json_story_path))
    generate_and_organize_images(json_story_path)
    final_video_path = stitch_assets(json_story_path, apply_shake.lower() == 'yes')
    
    archive_project(json_story_path)
    
    return final_video_path

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# 🎬 Story to Video Generator")
    gr.Markdown("Select an existing `story.json` and generate a video with narration and images.")

    with gr.Row():
        with gr.Column():
            json_story_path = gr.Textbox(label="Path to Story JSON", placeholder="Enter the path to your story.json file", lines=1)
            apply_shake = gr.Radio(choices=["yes", "no"], label="Apply shake effect?", value="no")
            submit_button = gr.Button("Stitch Video 🎥")
        with gr.Column():
            video_output = gr.Video(label="Generated Story Video")

    submit_button.click(fn=run_pipeline, inputs=[json_story_path, apply_shake], outputs=video_output)

# Launch the app
demo.launch()
