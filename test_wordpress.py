from services.wordpress_fetcher import test_connection, fetch_posts, fetch_pages

test_connection()

posts = fetch_posts()
for p in posts:
    print(f"Post: {p['title']}")

pages = fetch_pages()
for p in pages:
    print(f"Page: {p['title']}")