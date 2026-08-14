import hashlib


def get_md5_hash(content):
    """
    Compute MD5 hash from file-like content.
    """
    content.seek(0)
    # Read and hash in chunks.
    md5_hash = hashlib.md5()
    for chunk in iter(lambda: content.read(8192), b''):
        md5_hash.update(chunk)
    content.seek(0)
    return md5_hash.hexdigest()
