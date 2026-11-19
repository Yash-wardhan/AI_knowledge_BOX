
import httpx
import pytest

from services.url_fetch_service import fetch_url_content


@pytest.mark.asyncio
async def test_fetch_url_content_success(monkeypatch):
    html = """
    <html>
        <head><title>FastAPI Tutorial</title></head>
        <body>
            <nav>Navigation</nav>
            <h1>FastAPI</h1>
            <p>FastAPI is a Python framework for building APIs.</p>
            <script>alert("test")</script>
        </body>
    </html>
    """

    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            headers={"content-type": "text/html"},
            text=html,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await fetch_url_content(
        "https://fastapi.tiangolo.com/tutorial/"
    )

    assert "FastAPI" in result
    assert "Python framework" in result
    assert "Navigation" not in result
    assert "alert" not in result


@pytest.mark.asyncio
async def test_fetch_url_content_http_error(monkeypatch):
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            404,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_url_content("https://example.com/missing")


@pytest.mark.asyncio
async def test_fetch_url_content_non_html(monkeypatch):
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            headers={"content-type": "application/pdf"},
            content=b"PDF content",
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    with pytest.raises(ValueError, match="URL must return HTML"):
        await fetch_url_content("https://example.com/file.pdf")