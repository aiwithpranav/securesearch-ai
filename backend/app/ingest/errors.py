"""Fixed error codes for ingestion. The text shown to admins comes from this table, NEVER from the
file's content, so an error message cannot leak document text."""

MESSAGES: dict[str, str] = {
    "UNSUPPORTED_TYPE": "This file type is not supported. Use PDF, DOCX, TXT or MD, and make sure the file is really that type.",
    "EMPTY": "The file is empty.",
    "NO_TEXT": "No readable text was found. Scanned documents (images) are not supported.",
    "PARSE_ERROR": "The file could not be read. It may be damaged or protected.",
    "TOO_LARGE": "The file is too large or has too much content.",
    "STORAGE_ERROR": "The file store could not be reached. The job can be retried.",
    "EMBEDDING_ERROR": "The text could not be turned into vectors. The job can be retried.",
    "INTEGRITY_ERROR": "The stored file does not match its recorded fingerprint.",
    "TIMEOUT": "Processing took too long and was stopped.",
    "DELETED": "The document was deleted before processing finished.",
    "INTERNAL": "An unexpected error occurred. The job can be retried.",
}


class IngestError(Exception):
    """Raised for any ingestion problem. `retryable` means trying again may help (storage, database)."""

    def __init__(self, code: str, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable

    @property
    def message(self) -> str:
        return MESSAGES.get(self.code, MESSAGES["INTERNAL"])
