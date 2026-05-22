"""Gradio UI for the RAG Platform search."""

import os

import gradio as gr
import httpx

API_BASE = os.getenv("API_BASE_URL", "http://api:8000/api/v1")


async def search_articles(
    query: str,
    mode: str,
    tags: str,
    size: int,
    page: int,
    sort_by_date: bool,
) -> str:
    """Call the search API and format results."""
    if not query.strip():
        return "Please enter a search query."

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    payload = {
        "query": query,
        "mode": mode,
        "size": int(size),
        "page": int(page),
        "sort_by_date": sort_by_date,
    }
    if tag_list:
        payload["tags"] = tag_list

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{API_BASE}/search", json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"API error: {e.response.status_code} - {e.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to API at {API_BASE}"

    data = response.json()
    return _format_results(data)


def _escape_markdown_fences(text: str) -> str:
    """Escape backtick fences in text so they don't break surrounding markdown."""
    return text.replace("```", r"\`\`\`")


def _format_results(data: dict) -> str:
    """Format search results as markdown."""
    total = data.get("total", 0)
    hits = data.get("hits", [])
    mode = data.get("mode", "unknown")
    query = data.get("query", "")

    if not hits:
        return f"No results found for '{query}' ({mode} search)."

    lines = [f"**{total} results** for '{query}' ({mode} search)\n"]

    for i, hit in enumerate(hits, 1):
        score = hit.get("score", 0)
        title = hit.get("title", "Untitled")
        author = hit.get("author", "Unknown")
        url = hit.get("url", "")
        tags = ", ".join(hit.get("tags", []))
        chunk_text = hit.get("chunk_text", "")
        chunk_index = hit.get("chunk_index", 0)
        published = hit.get("published_date", "")[:10] if hit.get("published_date") else ""

        highlights = hit.get("highlights", {})
        display_text = ""
        if highlights and "chunk_text" in highlights:
            display_text = " ... ".join(highlights["chunk_text"])
        else:
            display_text = chunk_text[:300] + ("..." if len(chunk_text) > 300 else "")

        display_text = _escape_markdown_fences(display_text)

        lines.append(f"### {i}. [{title}]({url})")
        lines.append(
            f"**Author:** {author} | **Score:** {score:.4f} | **Chunk:** {chunk_index} | **Published:** {published}"
        )
        if tags:
            lines.append(f"**Tags:** {tags}")
        lines.append(f"\n{display_text}\n")
        lines.append("---")

    return "\n".join(lines)


async def ask_question(
    question: str,
    mode: str,
    tags: str,
    num_chunks: int,
):
    """Stream a RAG answer via SSE, yielding progressively to Gradio."""
    import json

    if not question.strip():
        yield "Please enter a question."
        return

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    payload = {
        "question": question,
        "mode": mode,
        "num_chunks": int(num_chunks),
    }
    if tag_list:
        payload["tags"] = tag_list

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{API_BASE}/ask/stream",
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    yield f"API error: {response.status_code}"
                    return

                answer = ""
                sources = []
                chunks_used = 0

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data = json.loads(line[6:])

                    # Error event
                    if "error" in data:
                        yield f"**Error:** {data['error']}"
                        return

                    # Metadata event (sources arrive first)
                    if "sources" in data and "chunk" not in data:
                        sources = data["sources"]
                        chunks_used = data.get("chunks_used", 0)
                        yield _format_streaming_answer(answer, sources, chunks_used)
                        continue

                    # Token chunk
                    if "chunk" in data:
                        answer += data["chunk"]
                        yield _format_streaming_answer(answer, sources, chunks_used)
                        continue

                    # Done or single-shot answer (no results case)
                    if "answer" in data:
                        answer = data["answer"]
                        sources = data.get("sources", sources)
                        chunks_used = data.get("chunks_used", chunks_used)
                        yield _format_streaming_answer(answer, sources, chunks_used)
                        return

                    if data.get("done"):
                        return

    except httpx.ConnectError:
        yield f"Could not connect to API at {API_BASE}"
    except httpx.TimeoutException:
        yield "Request timed out. The LLM may be slow or unavailable."


def _format_streaming_answer(answer: str, sources: list, chunks_used: int) -> str:
    """Format the progressively-built answer with sources as markdown."""
    if not answer and not sources:
        return "Searching..."

    lines = [answer]

    if sources:
        lines.append("\n\n---")
        lines.append(f"**Sources** ({chunks_used} chunks used):\n")
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            author = source.get("author", "")
            author_str = f" by {author}" if author else ""
            lines.append(f"{i}. [{title}]({url}){author_str}")

    return "\n".join(lines)


def build_app() -> gr.Blocks:
    """Build the Gradio interface."""
    with gr.Blocks(title="RAG Platform - Search") as app:
        gr.Markdown("# RAG Platform - Article Search")

        with gr.Tabs():
            with gr.TabItem("Search"):
                with gr.Row():
                    with gr.Column(scale=3):
                        query_input = gr.Textbox(
                            label="Search Query",
                            placeholder="e.g. Python error handling best practices",
                            lines=1,
                        )
                    with gr.Column(scale=1):
                        mode_input = gr.Dropdown(
                            choices=["hybrid", "bm25", "vector"],
                            value="hybrid",
                            label="Search Mode",
                        )

                with gr.Row():
                    tags_input = gr.Textbox(
                        label="Tags (comma-separated)",
                        placeholder="e.g. python, webdev",
                        lines=1,
                    )
                    size_input = gr.Slider(minimum=1, maximum=50, value=10, step=1, label="Results")
                    page_input = gr.Slider(minimum=1, maximum=20, value=1, step=1, label="Page")
                    sort_date = gr.Checkbox(label="Sort by date", value=False)

                search_btn = gr.Button("Search", variant="primary")
                results_output = gr.Markdown(label="Results")

                search_btn.click(
                    fn=search_articles,
                    inputs=[query_input, mode_input, tags_input, size_input, page_input, sort_date],
                    outputs=results_output,
                )

                query_input.submit(
                    fn=search_articles,
                    inputs=[query_input, mode_input, tags_input, size_input, page_input, sort_date],
                    outputs=results_output,
                )

            with gr.TabItem("RAG"):
                with gr.Row():
                    with gr.Column(scale=3):
                        question_input = gr.Textbox(
                            label="Question",
                            placeholder="e.g. What are the best practices for error handling in Python?",
                            lines=2,
                        )
                    with gr.Column(scale=1):
                        rag_mode_input = gr.Dropdown(
                            choices=["hybrid", "bm25", "vector"],
                            value="hybrid",
                            label="Search Mode",
                        )

                with gr.Row():
                    rag_tags_input = gr.Textbox(
                        label="Tags (comma-separated)",
                        placeholder="e.g. python, webdev",
                        lines=1,
                    )
                    num_chunks_input = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1, label="Context chunks"
                    )

                ask_btn = gr.Button("Ask", variant="primary")
                answer_output = gr.Markdown(label="Answer")

                ask_btn.click(
                    fn=ask_question,
                    inputs=[question_input, rag_mode_input, rag_tags_input, num_chunks_input],
                    outputs=answer_output,
                )

                question_input.submit(
                    fn=ask_question,
                    inputs=[question_input, rag_mode_input, rag_tags_input, num_chunks_input],
                    outputs=answer_output,
                )

    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
