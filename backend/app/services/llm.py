import asyncio
import time
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
import structlog    
from app.core.config import settings

logger = structlog.get_logger(__name__)

class GeminiService:
    def __init__(self):
        self.client: genai.Client | None = None

    def get_client(self) -> genai.Client:
        if not self.client:
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
                raise ValueError("GEMINI_API_KEY is not configured in .env file.")
            logger.info("Initializing Google GenAI Client...")
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self.client

    async def generate_response(self, prompt: str, system_instruction: str | None = None) -> str:
        """
        Send a request to Gemini API using google-genai SDK, offloading to threads to keep event loop free.
        """
        client = self.get_client()

        def _call_gemini():
            config_params = {}
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            
            # Resiliency: Handle 429 Rate limits with automatic backoff
            max_retries = 3
            retry_delay = 15.0
            for attempt in range(max_retries):
                try:
                    # Using recommended production model gemini-3.1-flash-lite
                    response = client.models.generate_content(
                        model="gemini-3.1-flash-lite",
                        contents=prompt,
                        config=config_params if config_params else None
                    )
                    return response.text
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        logger.warning(
                            "Gemini API rate limit (429) hit. Retrying...",
                            attempt=attempt + 1,
                            delay=retry_delay,
                            error=str(e)
                        )
                        time.sleep(retry_delay)
                    else:
                        raise e

        try:
            logger.info("Sending content generation request to Gemini...")
            text_response = await asyncio.to_thread(_call_gemini)
            return text_response
        except Exception as e:
            logger.error("Gemini API call failed", error=str(e))
            raise e

gemini_service = GeminiService()
