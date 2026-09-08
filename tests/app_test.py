from fastapi.testclient import TestClient

from config import MAX_PAGE_SIZE


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page_size_limit(client: TestClient):
    assert client.get(f"/?page_size={MAX_PAGE_SIZE + 1}").status_code == 422
