def validate_upload(filename: str) -> None:
    if not filename:
        raise ValueError("filename is required")
