function showProfile() {
    if (!token) {
        showView("login");
        return;
    }
    showView("profile");
    loadProfile();
}

async function loadProfile() {
    const headers = { "Authorization": "Bearer " + token };
    const [meRes, topicsRes, repliesRes] = await Promise.all([
        fetch(apiUrl + "/me", { headers }),
        fetch(apiUrl + "/me/topics", { headers }),
        fetch(apiUrl + "/me/replies", { headers })
    ]);

    const infoDiv = document.getElementById("profileInfo");
    if (meRes.ok) {
        const me = await meRes.json();
        infoDiv.innerHTML = `
            <p><strong>Användarnamn:</strong> ${escapeHtml(me.username)}</p>
            <p><strong>Namn:</strong> ${escapeHtml(me.name)}</p>
        `;
    } else {
        infoDiv.innerHTML = '<p class="emptyState">Kunde inte ladda profil.</p>';
    }

    const topicsDiv = document.getElementById("profileTopics");
    topicsDiv.innerHTML = "";
    if (topicsRes.ok) {
        const topics = await topicsRes.json();
        if (topics.length === 0) {
            topicsDiv.innerHTML = '<p class="emptyState">Du har inte skapat några frågor ännu.</p>';
        } else {
            for (const t of topics) {
                const item = document.createElement("div");
                item.className = "profileItem";
                item.innerHTML = `
                    <a href="#" class="profileLink">${escapeHtml(t.title)}</a>
                    <span class="profileItemMeta">${escapeHtml(t.category)} · ${escapeHtml(t.created_at)}</span>
                    <button class="deleteBtn">Ta bort</button>
                `;
                item.querySelector("a").addEventListener("click", (e) => {
                    e.preventDefault();
                    openTopic(t.id);
                });
                item.querySelector("button").addEventListener("click", () => {
                    deleteResource(
                        "/topics/" + t.id,
                        "Ta bort frågan och alla svar?",
                        () => loadProfile()
                    );
                });
                topicsDiv.appendChild(item);
            }
        }
    }

    const repliesDiv = document.getElementById("profileReplies");
    repliesDiv.innerHTML = "";
    if (repliesRes.ok) {
        const replies = await repliesRes.json();
        if (replies.length === 0) {
            repliesDiv.innerHTML = '<p class="emptyState">Du har inte skrivit några svar ännu.</p>';
        } else {
            for (const r of replies) {
                const item = document.createElement("div");
                item.className = "profileItem";
                item.innerHTML = `
                    <a href="#" class="profileLink">På: ${escapeHtml(r.topic_title)}</a>
                    <p class="profileReplyContent">${escapeHtml(r.content)}</p>
                    <span class="profileItemMeta">${escapeHtml(r.created_at)}</span>
                    <button class="deleteBtn">Ta bort</button>
                `;
                item.querySelector("a").addEventListener("click", (e) => {
                    e.preventDefault();
                    openTopic(r.topic_id, r.id);
                });
                item.querySelector("button").addEventListener("click", () => {
                    deleteResource(
                        "/replies/" + r.id,
                        "Ta bort svaret och alla underliggande svar?",
                        () => loadProfile()
                    );
                });
                repliesDiv.appendChild(item);
            }
        }
    }
}
