import re
import unicodedata
from loguru import logger
from ..translate.translate_interface import TranslateInterface


def tts_filter(
    text: str,
    remove_special_char: bool,
    ignore_brackets: bool,
    ignore_parentheses: bool,
    ignore_asterisks: bool,
    ignore_angle_brackets: bool,
    translator: TranslateInterface | None = None,
) -> str:
    """
    Filter or do anything to the text before TTS generates the audio.
    Changes here do not affect subtitles or LLM's memory. The generated audio is
    the only affected thing.

    Args:
        text (str): The text to filter.
        remove_special_char (bool): Whether to remove special characters.
        ignore_brackets (bool): Whether to ignore text within brackets.
        ignore_parentheses (bool): Whether to ignore text within parentheses.
        ignore_asterisks (bool): Whether to ignore text within asterisks.
        translator (TranslateInterface, optional):
            The translator to use. If None, we'll skip the translation. Defaults to None.

    Returns:
        str: The filtered text.
    """
    if ignore_asterisks:
        try:
            text = filter_asterisks(text)
        except Exception as e:
            logger.warning(f"Error ignoring asterisks: {e}")
            logger.warning(f"Text: {text}")
            logger.warning("Skipping...")

    if ignore_brackets:
        try:
            text = filter_brackets(text)
        except Exception as e:
            logger.warning(f"Error ignoring brackets: {e}")
            logger.warning(f"Text: {text}")
            logger.warning("Skipping...")
    if ignore_parentheses:
        try:
            text = filter_parentheses(text)
        except Exception as e:
            logger.warning(f"Error ignoring parentheses: {e}")
            logger.warning(f"Text: {text}")
            logger.warning("Skipping...")
    if remove_special_char:
        try:
            text = remove_special_characters(text)
        except Exception as e:
            logger.warning(f"Error removing special characters: {e}")
            logger.warning(f"Text: {text}")
            logger.warning("Skipping...")
    if ignore_angle_brackets:
        try:
            text = filter_angle_brackets(text)
        except Exception as e:
            logger.warning(f"Error ignoring angle brackets: {e}")
            logger.warning(f"Text: {text}")
            logger.warning("Skipping...")
    if translator:
        try:
            logger.info("Translating...")
            text = translator.translate(text)
            logger.info(f"Translated: {text}")
        except Exception as e:
            logger.critical(f"Error translating: {e}")
            logger.critical(f"Text: {text}")
            logger.warning("Skipping...")

    logger.debug(f"Filtered text: {text}")
    return text


def remove_special_characters(text: str) -> str:
    """
    Filter text to remove all non-letter, non-number, and non-punctuation characters.
    Special handling for Malayalam text.
    """
    # Use NFD normalization for better handling of Malayalam combining characters
    normalized_text = unicodedata.normalize("NFD", text)

    def is_valid_char(char: str) -> bool:
        if char == "*":
            return False

        category = unicodedata.category(char)
        # Include Malayalam specific categories
        return (
            category.startswith("L")  # Letters
            or category.startswith("N")  # Numbers
            or category.startswith("P")  # Punctuation
            or char.isspace()
            # Malayalam Unicode range
            or ('\u0D00' <= char <= '\u0D7F')
            # Malayalam numbers range
            or ('\u0D66' <= char <= '\u0D6F')
            # Hindi Unicode range (Devanagari)
            or ('\u0900' <= char <= '\u097F')
            # Hindi numbers range
            or ('\u0966' <= char <= '\u096F')
            # Extended Devanagari
            or ('\uA8E0' <= char <= '\uA8FF')
            # Devanagari Extended
            or ('\u11B00' <= char <= '\u11B4F')
        )

    filtered_text = "".join(char for char in normalized_text if is_valid_char(char))
    # Final normalization to compose characters
    return unicodedata.normalize("NFC", filtered_text)


def _filter_nested(text: str, left: str, right: str) -> str:
    """
    Generic function to handle nested symbols.

    Args:
        text (str): The text to filter.
        left (str): The left symbol (e.g. '[' or '(').
        right (str): The right symbol (e.g. ']' or ')').

    Returns:
        str: The filtered text.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    if not text:
        return text

    result = []
    depth = 0
    for char in text:
        if char == left:
            depth += 1
        elif char == right:
            if depth > 0:
                depth -= 1
        else:
            if depth == 0:
                result.append(char)
    filtered_text = "".join(result)
    filtered_text = re.sub(r"\s+", " ", filtered_text).strip()
    return filtered_text


def filter_brackets(text: str) -> str:
    """
    Filter text to remove all text within brackets, handling nested cases.

    Args:
        text (str): The text to filter.

    Returns:
        str: The filtered text.
    """
    return _filter_nested(text, "[", "]")


def filter_parentheses(text: str) -> str:
    """
    Filter text to remove all text within parentheses, handling nested cases.

    Args:
        text (str): The text to filter.

    Returns:
        str: The filtered text.
    """
    return _filter_nested(text, "(", ")")


def filter_angle_brackets(text: str) -> str:
    """
    Filter text to remove all text within angle brackets, handling nested cases.

    Args:
        text (str): The text to filter.

    Returns:
        str: The filtered text.
    """
    return _filter_nested(text, "<", ">")


def filter_asterisks(text):
    """
    Removes text enclosed within both single (*) and double (**) asterisks from a string.

    Args:
      text: The input string.

    Returns:
      The string with asterisk-enclosed text removed.

    Examples:
        >>> filter_asterisks("Mix of *single* and **double** asterisks")
        'Mix of  and  asterisks'
    """
    # First remove double asterisks pattern
    # \*\*([^*]+)\*\* matches text between double asterisks
    filtered_text = re.sub(r"\*\*([^*]+)\*\*", "", text)

    # Then remove single asterisks pattern
    # \*([^*]+)\* matches text between single asterisks
    filtered_text = re.sub(r"\*([^*]+)\*", "", filtered_text)

    # Clean up any extra spaces
    filtered_text = re.sub(r"\s+", " ", filtered_text).strip()

    return filtered_text
