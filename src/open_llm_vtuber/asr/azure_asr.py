import os
from typing import Callable
import numpy as np
from loguru import logger
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.audio import AudioConfig
from .asr_interface import ASRInterface
from src.open_llm_vtuber.global_config import Config

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


class VoiceRecognition(ASRInterface):
    def __init__(
        self,
        subscription_key=os.getenv("AZURE_API_Key"),
        region=os.getenv("AZURE_REGION"),
        callback: Callable = logger.info,
    ):
        self.subscription_key = subscription_key
        self.region = region

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key, region=self.region
        )

        if not self.subscription_key or not self.region:
            logger.error(
                "Please provide a valid subscription key and region for Azure Speech Recognition or use faster-whisper local speech recognition by changing the STT model option in the conf.yaml."
            )
            logger.error(
                'To provide the API keys, follow the instructions in the Readme.md documentation "Azure API for Speech Recognition and Speech to Text" to create api_keys.py. Alternatively, you may run the following command: \n`export AZURE_API_Key=<your-subscription-key>`\n`export AZURE_REGION=<your-azure-region-code>` with your API keys'
            )

        self.callback = callback

    def _create_speech_recognizer(self, uses_default_microphone: bool = True):
        logger.debug(f"Sub: {self.subscription_key}, Reg: {self.region}")
        assert isinstance(
            self.subscription_key, str
        ), "subscription_key must be a string"

        audio_config = AudioConfig(use_default_microphone=uses_default_microphone)
        return speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, audio_config=audio_config
        )

    def transcribe_np(self, audio: np.ndarray) -> str:
        """Transcribe audio using the given parameters.

        Args:
            audio: The numpy array of the audio data to transcribe.
        """
        import soundfile as sf

        temp_file = os.path.join(CACHE_DIR, "temp.wav")

        # Make sure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)

        # Properly save as WAV file - needs sample rate
        sf.write(temp_file, audio, 16000)  # Assuming 16kHz sample rate

        audio_config = AudioConfig(filename=temp_file)
        auto_detect_source_language_config = (
            speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                languages=["en-US", "hi-IN", "ml-IN"]
            )
        )
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config,
            auto_detect_source_language_config=auto_detect_source_language_config,
        )

        logger.info("Starting recognition")
        result = speech_recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            auto_detect_result = speechsdk.AutoDetectSourceLanguageResult(result)
            logger.info(f"Recognized language: {auto_detect_result.language}")

            config = Config.get_instance()
            config.current_language = auto_detect_result.language

            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            logger.warning("No speech could be recognized")
            return ""
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.CancellationDetails(result)
            logger.error(f"Recognition canceled: {cancellation.reason}")
            logger.error(f"Error details: {cancellation.error_details}")
            return ""


if __name__ == "__main__":
    service = VoiceRecognition()
