from platform_sdk.catalog_content_service_repositories import custom_book_catalog_service


append_catalog_content_custom_book_chapters_response = (
    custom_book_catalog_service.append_custom_book_chapters_response
)
create_catalog_content_custom_book_response = custom_book_catalog_service.create_custom_book_response
get_catalog_content_custom_book_response = custom_book_catalog_service.get_custom_book_response
list_catalog_content_custom_books_response = custom_book_catalog_service.list_custom_books_response


__all__ = [
    'append_catalog_content_custom_book_chapters_response',
    'create_catalog_content_custom_book_response',
    'get_catalog_content_custom_book_response',
    'list_catalog_content_custom_books_response',
]
