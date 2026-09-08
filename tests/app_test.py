from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_refuses_an_oversized_page(client):
    """The HTML listing had the same unbounded page_size as the LDN one."""
    from config import MAX_PAGE_SIZE

    response = client.get(f"/?page_size={MAX_PAGE_SIZE + 1}")

    assert response.status_code == 422
