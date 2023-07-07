class ImageDownloadException(Exception):
    def __init__(self, url, cause):
        super().__init__(f"Failure of image download at {url} caused by {cause}")
        self.__cause__ = cause
