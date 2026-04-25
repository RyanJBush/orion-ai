def test_vector_memory_write_and_search(client):
    write = client.post(
        "/api/v1/memory/vector/write",
        json={
            "namespace": "n1",
            "text": "agent workflow task",
            "scope": "short_term",
            "memory_type": "tool_result",
            "source_ref": "run:1:step:1",
            "metadata": {"step_id": "step-1"},
        },
    )
    assert write.status_code == 200

    search = client.post("/api/v1/memory/vector/search", json={"namespace": "n1", "query": "workflow"})
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 1
    assert results[0]["score"] >= 0
    assert results[0]["scope"] == "short_term"
    assert results[0]["memory_type"] == "tool_result"


def test_vector_memory_search_filters_scope_and_type(client):
    alpha = client.post(
        "/api/v1/memory/vector/write",
        json={
            "namespace": "n2",
            "text": "workflow memory alpha",
            "scope": "short_term",
            "memory_type": "tool_result",
        },
    )
    beta = client.post(
        "/api/v1/memory/vector/write",
        json={
            "namespace": "n2",
            "text": "workflow memory beta",
            "scope": "long_term",
            "memory_type": "fact",
        },
    )
    assert alpha.status_code == 200
    assert beta.status_code == 200

    filtered = client.post(
        "/api/v1/memory/vector/search",
        json={"namespace": "n2", "query": "workflow", "scope": "long_term", "memory_type": "fact"},
    )
    assert filtered.status_code == 200
    rows = filtered.json()
    assert len(rows) == 1
    assert rows[0]["scope"] == "long_term"
    assert rows[0]["memory_type"] == "fact"


def test_basic_memory_correction_and_summary(client):
    created = client.post(
        "/api/v1/memory/basic/write",
        json={
            "namespace": "team:alpha",
            "key": "k1",
            "text": "The user likes dark mode",
            "scope": "long_term",
            "memory_type": "preference",
            "source_ref": "ticket-1",
        },
    )
    assert created.status_code == 200
    created_id = created.json()["id"]

    corrected = client.post(
        f"/api/v1/memory/basic/{created_id}/correct",
        json={"replacement_text": "The user prefers light mode", "source_ref": "ticket-2"},
    )
    assert corrected.status_code == 200

    summary = client.get("/api/v1/memory/summary/team:alpha")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_entries"] == 1
    assert payload["by_scope"]["long_term"] == 1
    assert payload["by_type"]["preference"] == 1
    assert payload["latest_texts"][0] == "The user prefers light mode"
