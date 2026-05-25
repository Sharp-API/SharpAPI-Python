from sharpapi import AsyncSharpAPI, SharpAPI


def test_sync_client_accepts_api_v1_base_url_without_double_prefix():
    client = SharpAPI("sk_test", base_url="https://api.sharpapi.io/api/v1/")

    assert str(client._http.base_url) == "https://api.sharpapi.io/api/v1/"
    assert client._base_url == "https://api.sharpapi.io"

    stream = client.stream.odds()
    assert stream._url.startswith("https://api.sharpapi.io/api/v1/stream?")
    assert "/api/v1/api/v1/" not in stream._url

    client.close()


async def test_async_client_accepts_api_v1_base_url_without_double_prefix():
    client = AsyncSharpAPI("sk_test", base_url="https://api.sharpapi.io/api/v1/")

    assert str(client._http.base_url) == "https://api.sharpapi.io/api/v1/"
    assert client._base_url == "https://api.sharpapi.io"

    await client.close()
