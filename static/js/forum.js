async function createTopic() {
    const title = document.getElementById("topicTitle").value;
    const category = document.getElementById("topicCategory").value;
    const description = document.getElementById("topicDescription").value;
    const imageInput = document.getElementById("topicImage");

    const form = new FormData();
    form.append("title", title);
    form.append("category", category);
    form.append("description", description);
    if (imageInput.files[0]) form.append("image", imageInput.files[0]);

    const response = await fetch(apiUrl + "/topics", {
        method: "POST",
        headers: { "Authorization": "Bearer " + token },
        body: form
    });

    const data = await response.json();

    if (response.ok) {
        document.getElementById("topicMessage").innerText = "Frågan publicerades!";
        document.getElementById("topicTitle").value = "";
        document.getElementById("topicDescription").value = "";
        imageInput.value = "";
        document.getElementById("filterCategory").value = "";
        document.getElementById("filterSearch").value = "";
        getTopics();
        showView("home");
    } else {
        document.getElementById("topicMessage").innerText = data.error;
    }
}

let searchTimer = null;
function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(getTopics, 300);
}

async function getTopics() {
    const category = document.getElementById("filterCategory")?.value || "";
    const q = document.getElementById("filterSearch")?.value.trim() || "";
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    const qs = params.toString();
    const url = apiUrl + "/topics" + (qs ? "?" + qs : "");
    const response = await fetch(url);
    const topics = await response.json();

    const topicsDiv = document.getElementById("topics");
    topicsDiv.innerHTML = "";

    if (topics.length === 0) {
        const empty = document.createElement("p");
        empty.className = "emptyState";
        empty.innerText = q || category
            ? "Inga frågor matchade din sökning."
            : "Inga frågor publicerade ännu.";
        topicsDiv.appendChild(empty);
        return;
    }

    for (let topic of topics) {
        const div = document.createElement("div");
        div.className = "topic minimized";
        div.dataset.topicId = topic.id;
        const imgHtml = topic.image_path
            ? `<img class="topicImage" src="/static/${escapeHtml(topic.image_path)}" alt="">`
            : "";
        const isOwner = token && String(topic.user_id) === currentUserId();
        const deleteBtnHtml = isOwner
            ? `<button class="deleteBtn" data-action="delete-topic">Ta bort</button>`
            : "";
        div.innerHTML = `
            <div class="topicHeader" onclick="toggleTopic(${topic.id})">
                <h3>${escapeHtml(topic.title)}</h3>
                <div class="topicHeaderRight">
                    <span>${escapeHtml(topic.category)}</span>
                    ${deleteBtnHtml}
                </div>
            </div>
            <div class="topicBody">
                <p class="topicDescription">${escapeHtml(topic.description)}</p>
                ${imgHtml}
                <div class="topicFooter">Skapad av ${escapeHtml(topic.username)}</div>
                <div class="replies" id="replies-${topic.id}"></div>
            </div>
        `;
        if (isOwner) {
            const delBtn = div.querySelector('[data-action="delete-topic"]');
            delBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteResource(
                    "/topics/" + topic.id,
                    "Ta bort frågan och alla svar?",
                    () => getTopics()
                );
            });
        }
        topicsDiv.appendChild(div);
    }
}

function toggleTopic(topicId) {
    const topic = document.querySelector(`[data-topic-id="${topicId}"]`);
    if (!topic) return;
    const wasMinimized = topic.classList.contains("minimized");
    topic.classList.toggle("minimized");
    if (wasMinimized) {
        loadReplies(topicId);
    }
}

async function loadReplies(topicId) {
    const response = await fetch(apiUrl + "/topics/" + topicId + "/replies");
    const replies = await response.json();

    const container = document.getElementById("replies-" + topicId);
    container.innerHTML = "";
    renderReplies(container, topicId, replies, null, 0);

    if (token) {
        container.appendChild(buildReplyForm(topicId, null));
    } else {
        const note = document.createElement("p");
        note.className = "loginNote";
        note.innerText = "Logga in för att svara";
        container.appendChild(note);
    }
}

function renderReplies(container, topicId, replies, parentId, depth) {
    const children = replies.filter(r => r.parent_reply_id === parentId);

    for (let reply of children) {
        const div = document.createElement("div");
        div.className = "reply";
        div.dataset.replyId = reply.id;
        div.style.marginLeft = (depth * 20) + "px";
        div.innerHTML = `
            <div class="replyHeader">
                <strong>${escapeHtml(reply.username)}</strong>
                <span class="replyTime">${escapeHtml(reply.created_at)}</span>
            </div>
            <p>${escapeHtml(reply.content)}</p>
        `;

        if (token) {
            const replyBtn = document.createElement("button");
            replyBtn.className = "replyToggle";
            replyBtn.innerText = "Svara";
            const formHolder = document.createElement("div");
            replyBtn.onclick = () => {
                if (formHolder.childNodes.length === 0) {
                    formHolder.appendChild(buildReplyForm(topicId, reply.id));
                } else {
                    formHolder.innerHTML = "";
                }
            };
            div.appendChild(replyBtn);

            if (String(reply.user_id) === currentUserId()) {
                const delBtn = document.createElement("button");
                delBtn.className = "deleteBtn";
                delBtn.innerText = "Ta bort";
                delBtn.onclick = () => deleteResource(
                    "/replies/" + reply.id,
                    "Ta bort svaret och alla underliggande svar?",
                    () => loadReplies(topicId)
                );
                div.appendChild(delBtn);
            }

            div.appendChild(formHolder);
        }

        container.appendChild(div);
        renderReplies(container, topicId, replies, reply.id, depth + 1);
    }
}

function buildReplyForm(topicId, parentReplyId) {
    const wrapper = document.createElement("div");
    wrapper.className = "replyForm";

    const textarea = document.createElement("textarea");
    textarea.placeholder = parentReplyId === null
        ? "Skriv ett svar..."
        : "Svara på det här inlägget...";

    const button = document.createElement("button");
    button.innerText = "Publicera svar";

    const message = document.createElement("p");
    message.className = "replyMessage";

    button.onclick = async () => {
        const content = textarea.value;
        if (!content.trim()) {
            message.innerText = "Du måste skriva något";
            return;
        }
        await postReply(topicId, content, parentReplyId);
        textarea.value = "";
    };

    wrapper.appendChild(textarea);
    wrapper.appendChild(button);
    wrapper.appendChild(message);
    return wrapper;
}

async function postReply(topicId, content, parentReplyId) {
    const response = await fetch(apiUrl + "/topics/" + topicId + "/replies", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({
            content: content,
            parent_reply_id: parentReplyId
        })
    });

    if (response.ok) {
        loadReplies(topicId);
    } else {
        const data = await response.json();
        alert(data.error || "Något gick fel");
    }
}
