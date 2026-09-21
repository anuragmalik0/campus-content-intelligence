"""
Campus Content Intelligence Agent — Chat Interface
Layer 4 — Interface
Owner: Person 5 (UI, Testing, Documentation)

A Streamlit web application providing a natural-language Q&A interface across
lecture slide decks, notes, and uploaded documents.

Core UX and Safety principles (system-design.md & security.md):
1. Glanceable, prominent citations: Clear badge cards for exact page numbers and document sections.
2. Deliberate refusal state: Declining out-of-scope questions is styled as a confident Responsible AI
   safeguard rather than an error or crash.
3. No raw HTML injection: Model output rendered safely.
4. One-click demo test prompts in sidebar for live presentations.
"""

import os
import sys
import streamlit as st

# Ensure project root is available in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.orchestrator import answer_question, Answer, Citation

# Page setup
st.set_page_config(
    page_title="Campus Content Intelligence Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling for citation cards and refusal boxes
st.markdown("""
<style>
    .citation-chip {
        display: inline-block;
        padding: 4px 10px;
        margin: 4px 4px 4px 0px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .citation-slide {
        background-color: #1e293b;
        color: #facc15;
        border: 1px solid #ca8a04;
    }
    .citation-pdf {
        background-color: #1e293b;
        color: #4ade80;
        border: 1px solid #16a34a;
    }
    .refusal-box {
        padding: 12px 16px;
        border-radius: 8px;
        background-color: #1e1e2e;
        border-left: 4px solid #f97316;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.title("🎓 Campus Content Intelligence Agent")
st.caption(
    "Query across multi-format course materials (Slides, Notes, Documents) "
    "with verified page and section citations."
)

# Sidebar: Topic Info & Demo Presets
with st.sidebar:
    st.header("📚 Topic Knowledge Base")
    st.markdown("**CS103: Lecture 3 — Gradient Descent & Optimization**")
    st.markdown("""
    - **📊 Slide Deck:** 6 slides (Optimization Landscape, LR, AdamW)
    - **📄 Notes PDF:** 4 pages (Formulations, Convergence, Batch sizes)
    - **🗂 Total Chunks:** Grounded academic knowledge
    """)
    st.divider()

    st.subheader("💡 Demo Question Presets")
    st.caption("Click to evaluate live grounded retrieval and refusal safety:")

    demo_questions = [
        ("💡 Momentum Intuition", "What physical intuition is given for Momentum in the notes?"),
        ("📄 GD Update Formula", "What is the mathematical update rule for gradient descent parameter updates?"),
        ("📊 AdamW vs Adam", "Why does AdamW decouple weight decay from gradient updates?"),
        ("🔄 Batch vs Mini-batch Tradeoffs", "Compare the memory complexity and GPU hardware trade-offs between Full Batch and Mini-batch."),
        ("🛑 Refusal Test: Australia", "What is the capital city of Australia?"),
        ("🛑 Refusal Test: Dijkstra", "What is Dijkstra's algorithm and what is its time complexity?")
    ]

    selected_demo_q = None
    for label, prompt in demo_questions:
        if st.button(label, use_container_width=True):
            selected_demo_q = prompt

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# Initialize session state for conversation history
if "history" not in st.session_state:
    st.session_state.history = []

# Main Chat Display
for item in st.session_state.history:
    user_q = item["question"]
    ans = item["answer"]

    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(user_q)

    with st.chat_message("assistant", avatar="🤖"):
        if ans["answered"]:
            st.markdown(ans["text"])
            if ans["citations"]:
                st.markdown("##### 📌 Verified Citations:")
                citation_md_list = []
                for c in ans["citations"]:
                    stype = c.get("source_type", "").lower()
                    if stype == "slide":
                        badge_icon = "📊 Slide"
                    else:
                        badge_icon = "📄 Page"
                    citation_md_list.append(f"- **{c['source_name']}** (`{badge_icon} {c['location']}`)")
                st.markdown("\n".join(citation_md_list))
        else:
            st.warning(f"🛡️ **Responsible AI — Scope Boundary Enforcement**\n\n{ans['text']}")
            if ans.get("reason"):
                st.caption(f"**Safeguard Diagnostic:** {ans['reason']}")

# Chat Input handling
query_input = st.chat_input("Ask a question about gradient descent, learning rates, or momentum...")
active_query = selected_demo_q or query_input

if active_query:
    # Process query
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(active_query)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analyzing lecture notes, slides, and documents..."):
            ans_result: Answer = answer_question(active_query)

        if ans_result["answered"]:
            st.markdown(ans_result["text"])
            if ans_result["citations"]:
                st.markdown("##### 📌 Verified Citations:")
                citation_md_list = []
                for c in ans_result["citations"]:
                    stype = c.get("source_type", "").lower()
                    if stype == "slide":
                        badge_icon = "📊 Slide"
                    else:
                        badge_icon = "📄 Page"
                    citation_md_list.append(f"- **{c['source_name']}** (`{badge_icon} {c['location']}`)")
                st.markdown("\n".join(citation_md_list))
        else:
            st.warning(f"🛡️ **Responsible AI — Scope Boundary Enforcement**\n\n{ans_result['text']}")
            if ans_result.get("reason"):
                st.caption(f"**Safeguard Diagnostic:** {ans_result['reason']}")

    st.session_state.history.append({"question": active_query, "answer": ans_result})
    if selected_demo_q:
        st.rerun()
