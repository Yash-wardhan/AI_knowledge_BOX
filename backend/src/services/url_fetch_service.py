import httpx
from bs4 import BeautifulSoup


async def fetch_url_content(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; KnowledgeInbox/1.0)"
    }

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type:
        raise ValueError("URL must return HTML content")

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    content = soup.get_text(separator="\n", strip=True)

    if not content:
        raise ValueError("No readable content found at URL")

    return content