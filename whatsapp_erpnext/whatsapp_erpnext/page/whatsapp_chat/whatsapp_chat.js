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
			const chatName = chat.contact_display || chat.from || chat.to || 'Unknown';
					const chatElement = $(`
						<div class="chat-item" data-from="${chat.from}" data-to="${chat.to}" data-contact-number="${chat.contact_number || chat.from || ''}" data-party-type="${chat.party_type || ''}" data-party="${chat.party || ''}">
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
						loadChat(chat.from, chat.to, chat.party_type, chat.party, chatName);
					});
					chatList.append(chatElement);
				});
			}
		}
	});
}

function loadChat(from, to, party_type, party, chatName) {
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.get_messages',
		args: {
			from_number: from,
			to_number: to,
			party_type: party_type,
			party: party
		},
		callback: function(response) {
			if (response.message !== undefined) {
				const messages = response.message || [];
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
				const displayName = messages[0]?.contact_display
					|| (messages[0]?.party ? `${messages[0].party_type || ''}: ${messages[0].party}` : null)
					|| messages[0]?.contact_name
					|| chatName
					|| 'Chat';
				$('#current-chat-name').text(displayName);
			}
		}
	});
}

function sendMessage() {
	const messageInput = $('#message-input');
	const content = messageInput.val().trim();
	if (!content) return;
	const activeChat = $('.chat-item.active');
	if (!activeChat.length) {
		frappe.msgprint('Please select a chat first');
		return;
	}
	const toNumber = activeChat.data('to');
	const fromNumber = activeChat.data('from');
	const partyType = activeChat.data('party-type');
	const party = activeChat.data('party');

	// The contact's number is the one that is NOT the business number.
	// Incoming messages: contact is in 'from', business is in 'to'
	// Outgoing messages: contact is in 'to', business is in 'from'
	// We store the contact number on the chat item for reliable lookup.
	const contactNumber = activeChat.data('contact-number') || fromNumber;

	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.send_message',
		args: {
			contact: contactNumber,
			content: content,
			party_type: partyType || '',
			party: party || ''
		},
		callback: function(response) {
			if (response.message) {
				messageInput.val('');
				loadChat(fromNumber, toNumber, partyType, party);
			}
		}
	});
}