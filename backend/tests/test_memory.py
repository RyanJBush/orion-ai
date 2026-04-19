def test_vector_memory_write_and_search(client):
    write = client.post("/api/v1/memory/vector/write", json={"namespace": "n1", "text": "agent workflow task"})
    assert write.status_code == 200

    search = client.post("/api/v1/memory/vector/search", json={"namespace": "n1", "query": "workflow"})
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 1
    assert results[0]["score"] >= 0
