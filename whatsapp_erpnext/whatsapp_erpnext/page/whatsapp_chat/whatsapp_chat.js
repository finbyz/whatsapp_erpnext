frappe.pages['whatsapp-chat'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Whatsapp Chat',
		single_column: true
	});

	// Create the main container
	const container = $(`<div class="whatsapp-container">
		<div class="whatsapp-sidebar">
			<div class="whatsapp-header">
				<div class="user-profile">
					<img src="/assets/whatsapp_erpnext/images/default-avatar.png" alt="Profile" class="avatar">
					<div class="user-info">
						<h3>${frappe.session.user}</h3>
					</div>
				</div>
			</div>
			<div class="chat-list" id="chat-list">
				<!-- Chat list will be populated here -->
			</div>
		</div>
		<div class="whatsapp-main">
			<div class="chat-header">
				<div class="contact-info">
					<img src="/assets/whatsapp_erpnext/images/default-avatar.png" alt="Contact" class="avatar">
					<div class="contact-details">
						<h3 id="current-chat-name">Select a chat</h3>
					</div>
				</div>
			</div>
			<div class="chat-messages" id="chat-messages">
				<!-- Messages will be populated here -->
			</div>
			<div class="chat-input">
				<div class="input-container">
					<input type="text" id="message-input" placeholder="Type a message">
					<button id="send-button">
						<i class="fa fa-paper-plane"></i>
					</button>
				</div>
			</div>
		</div>
	</div>`).appendTo(page.main);

	// Add CSS
	frappe.require('/assets/whatsapp_erpnext/css/whatsapp.css');

	// Initialize the chat functionality
	initializeChat();
}

function initializeChat() {
	// Load chats
	loadChats();
	
	// Set up message sending
	$('#send-button').on('click', sendMessage);
	$('#message-input').on('keypress', function(e) {
		if (e.which === 13) {
			sendMessage();
		}
	});
}

function loadChats() {
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.get_chats',
		callback: function(response) {
			if (response.message) {
				const chats = response.message;
				const chatList = $('#chat-list');
				chatList.empty();
				chats.forEach(chat => {
					const unreadBadge = chat.unread_count > 0 ? `<span class="unread-badge">${chat.unread_count}</span>` : '';
					const chatName = chat.contact_display || (chat.party ? `${chat.party_type || ''}: ${chat.party}` : chat.contact);
					const chatElement = $(`
						<div class="chat-item" data-from="${chat.from}" data-to="${chat.to}" data-party-type="${chat.party_type || ''}" data-party="${chat.party || ''}">
							<img src="/assets/whatsapp_erpnext/images/default-avatar.png" alt="Contact" class="avatar">
							<div class="chat-info">
								<h4>${chatName}</h4>
								<p>${chat.last_message || 'No messages'}</p>
								${unreadBadge}
							</div>
						</div>
					`);
					chatElement.on('click', () => {
						$('.chat-item').removeClass('active');
						chatElement.addClass('active');
						loadChat(chat.from, chat.to, chat.party_type, chat.party);
					});
					chatList.append(chatElement);
				});
			}
		}
	});
}

function loadChat(from, to, party_type, party) {
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.get_messages',
		args: {
			from_number: from,
			to_number: to,
			party_type: party_type,
			party: party
		},
		callback: function(response) {
			if (response.message) {
				const messages = response.message;
				const chatMessages = $('#chat-messages');
				chatMessages.empty();
				messages.forEach(message => {
					let tick = '';
					if (message.direction === 'sent') {
						if (message.status === 'Read') {
							tick = '<span class="tick blue">&#10003;&#10003;</span>';
						} else if (message.status === 'Delivered') {
							tick = '<span class="tick double">&#10003;&#10003;</span>';
						} else if (message.status === 'Success') {
							tick = '<span class="tick single">&#10003;</span>';
						} else if (message.status === 'Failed') {
							tick = '<span class="tick failed">&#10007;</span>';
						}
					}
					let contentHtml = message.content;
					if (/\.(jpg|jpeg|png|gif)$/i.test(contentHtml)) {
						contentHtml = `<img src="${contentHtml}" class="chat-image" />`;
					}
					const messageElement = $(`
						<div class="message ${message.direction}">
							<div class="message-content">
								${contentHtml} ${tick}
							</div>
							<div class="message-time">
								${frappe.datetime.str_to_user(message.creation)}
							</div>
						</div>
					`);
					chatMessages.append(messageElement);
				});
				chatMessages.scrollTop(chatMessages[0].scrollHeight);
				const chatName = messages[0]?.contact_display || (messages[0]?.party ? `${messages[0].party_type || ''}: ${messages[0].party}` : messages[0]?.contact_name || 'Chat');
				$('#current-chat-name').text(chatName);
			}
		}
	});
}

function sendMessage() {
	const messageInput = $('#message-input');
	const content = messageInput.val().trim();
	if (!content) return;
	const activeChat = $('.chat-item.active');
	const currentContact = activeChat.data('chat-id');
	const partyType = activeChat.data('party-type');
	const party = activeChat.data('party');
	if (!currentContact) {
		frappe.msgprint('Please select a chat first');
		return;
	}
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.send_message',
		args: {
			contact: currentContact,
			content: content,
			party_type: partyType,
			party: party
		},
		callback: function(response) {
			if (response.message) {
				messageInput.val('');
				loadChat(currentContact, partyType, party);
			}
		}
	});
}