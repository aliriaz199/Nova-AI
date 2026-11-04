
// Save chat history in browser storage
function saveChats(chats) {
    localStorage.setItem("ai_chat_history", JSON.stringify(chats));
}

// Load saved chats from browser storage
function loadChats() {
    const savedChats = localStorage.getItem("ai_chat_history");

    return savedChats ? JSON.parse(savedChats) : [];
}
