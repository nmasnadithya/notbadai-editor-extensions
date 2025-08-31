import time
import os
from common.api import ExtensionAPI
from common.secrets import DEEP_INFRA_API_KEY
from openai import OpenAI



def extension(api: ExtensionAPI):
    audio_read_start = time.time()
    audio_data = open(api.audio_blob_path, 'rb')
    api.log(f"Audio file read completed in {time.time() - audio_read_start:.3f} seconds")

    transcription_start = time.time()
    client = OpenAI(api_key=DEEP_INFRA_API_KEY, base_url='https://api.deepinfra.com/v1/openai')
    transcription = client.audio.transcriptions.create(model='openai/whisper-large-v3-turbo', file=audio_data, language='en')
    api.log(f"Transcription completed in {time.time() - transcription_start:.3f} seconds")
    
    api.send_audio_transcription(transcription.text)
    os.remove(api.audio_blob_path)
    