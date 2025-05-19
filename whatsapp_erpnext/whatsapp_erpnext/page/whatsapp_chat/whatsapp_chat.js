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
					const chatElement = $(`
						<div class="chat-item" data-chat-id="${chat.contact}">
							<img src="/assets/whatsapp_erpnext/images/default-avatar.png" alt="Contact" class="avatar">
							<div class="chat-info">
								<h4>${chat.contact}</h4>
								<p>${chat.last_message || 'No messages'}</p>
							</div>
						</div>
					`);
					
					chatElement.on('click', () => {
						$('.chat-item').removeClass('active');
						chatElement.addClass('active');
						loadChat(chat.contact);
					});
					chatList.append(chatElement);
				});
			}
		}
	});
}

function loadChat(contact) {
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.get_messages',
		args: {
			contact: contact
		},
		callback: function(response) {
			if (response.message) {
				const messages = response.message;
				const chatMessages = $('#chat-messages');
				chatMessages.empty();
				
				messages.forEach(message => {
					const messageElement = $(`
						<div class="message ${message.direction}">
							<div class="message-content">
								${message.content}
							</div>
							<div class="message-time">
								${frappe.datetime.str_to_user(message.creation)}
							</div>
						</div>
					`);
					chatMessages.append(messageElement);
				});
				
				// Scroll to bottom
				chatMessages.scrollTop(chatMessages[0].scrollHeight);
				
				// Update current chat name
				$('#current-chat-name').text(messages[0]?.contact_name || 'Chat');
			}
		}
	});
}

function sendMessage() {
	const messageInput = $('#message-input');
	const content = messageInput.val().trim();
	
	if (!content) return;
	
	const currentChatId = $('.chat-item.active').data('chat-id');
	if (!currentChatId) {
		frappe.msgprint('Please select a chat first');
		return;
	}
	
	frappe.call({
		method: 'whatsapp_erpnext.whatsapp_erpnext.doctype.whatsapp_message.whatsapp_message.send_message',
		args: {
			contact: currentChatId,
			content: content
		},
		callback: function(response) {
			if (response.message) {
				messageInput.val('');
				loadChat(currentChatId);
			}
		}
	});
}