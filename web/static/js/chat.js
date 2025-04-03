document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatStatus = document.getElementById('chat-status');
    
    // 检查marked是否已加载
    if (typeof marked === 'undefined') {
        // 如果marked未加载，动态加载它
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
        script.onload = function() {
            // marked加载完成后配置
            configureMarked();
            init();
        };
        document.head.appendChild(script);
    } else {
        // marked已加载，直接配置
        configureMarked();
        init();
    }
    
    // 配置marked.js
    function configureMarked() {
        marked.setOptions({
            sanitize: false,  // 注意：最新版本的marked已弃用sanitize选项
            gfm: true,        // 启用GitHub风格Markdown
            breaks: true,     // 将换行符转换为<br>
            highlight: function(code, lang) {
                // 如果需要代码高亮，可以在这里集成highlight.js等库
                return code;
            }
        });
    }
    
    // 存储会话ID
    let conversationId = null;
    // WebSocket连接
    let ws = null;
    
    // 初始化函数
    function init() {
        // 绑定发送按钮点击事件
        sendButton.addEventListener('click', sendMessage);
        
        // 绑定输入框回车事件
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // 自动聚焦到输入框
        userInput.focus();
    }
    
    // 发送消息函数
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
           // 删除所有具有特定类名的div
        const elements = document.getElementsByClassName('streaming-container'); 
        while (elements.length  > 0) {
        elements[0].parentNode.removeChild(elements[0]); 
        }
        // 清空输入框
        userInput.value = '';
        
        // 添加用户消息到聊天界面
        addMessage(message, 'user');
        
        // 显示处理状态
        chatStatus.textContent = '正在处理您的请求...';
        chatStatus.className = 'typing';
        
        try {
            // 发送消息到服务器
            const response = await fetch('http://127.0.0.1:7020/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    context: conversationId ? { conversation_id: conversationId } : {}
                })
            });
            
            if (!response.ok) {
                throw new Error('网络请求失败');
            }
            
            const data = await response.json();
            
            // 保存会话ID
            conversationId = data.data.conversation_id;
            
            // 如果还没有WebSocket连接，则创建一个
            if (!ws) {
                connectWebSocket();
            }
            
            // 添加初始响应
            if (data.message && data.message !== '您的请求正在处理中，请稍候...') {
                addMessage(data.message, 'system');
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            chatStatus.textContent = '发送消息失败: ' + error.message;
            chatStatus.className = 'error';
        }
    }
    
    // 连接WebSocket
    function connectWebSocket() {
        // 确保有会话ID
        if (!conversationId) return;
        
        // 创建WebSocket连接
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//127.0.0.1:7020/api/ws/${conversationId}`;
        
        ws = new WebSocket(wsUrl);
        
        // 连接打开事件
        ws.onopen = function() {
            console.log('WebSocket连接已建立');
        };
        
        // 接收消息事件
        // 存储当前系统消息的DOM元素
        let currentSystemMessage = null;
        
        // 存储当前streaming消息的DOM元素
        let currentStreamingMessage = null;
        
        // 创建消息容器
        function createMessageContainer(className = 'system-message') {
            const container = document.createElement('div');
            container.className = className;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            container.appendChild(contentDiv);
            
            chatMessages.appendChild(container);
            return container;
        }
        
        // 更新消息内容
        function updateMessageContent(container, message, isMarkdown = true) {
            const contentDiv = container.querySelector('.message-content');
            if (isMarkdown && typeof marked !== 'undefined') {
                contentDiv.innerHTML =  contentDiv.innerHTML + marked.parse(message);
            } else {
                contentDiv.textContent = contentDiv.textContent + message;
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // 处理工具消息
        function handleToolMessage(data) {
            if (!currentSystemMessage) {
                currentSystemMessage = createMessageContainer();
            }
            
            let toolMessage = `正在使用工具: ${data.tool_name}\n`;
            if (data.message) {
                toolMessage += data.message;
            }
            
            updateMessageContent(currentSystemMessage, toolMessage);
        }
        
        // 处理流式消息
        function handleStreamingMessage(data) {
            if (!currentStreamingMessage) {
                currentStreamingMessage = createMessageContainer('system-message streaming');
            }
            updateMessageContent(currentStreamingMessage, data.message, false);
        }
        
        // 处理处理中消息
        function handleProcessingMessage(data) {
            if (currentStreamingMessage) {
                currentStreamingMessage.remove();
                currentStreamingMessage = null;
            }
            
            if (!currentSystemMessage) {
                currentSystemMessage = createMessageContainer();
            }
            updateMessageContent(currentSystemMessage, data.message);
        }
        
        // 修改后的ws.onmessage处理函数
        ws.onmessage = function(event) {
            if (!event.data) return;
            
            try {
                const data = JSON.parse(event.data);
                console.log('收到WebSocket消息:', data);
                
                if (data.status === 'started') {
                    chatStatus.textContent = '开始处理您的请求...';
                    chatStatus.className = 'typing';
                    return;
                }
                
                if (data.status === 'tool') {
                    handleToolMessage(data);
                    return;
                }
                
                if (data.status === 'streaming') {
                    handleStreamingMessage(data);
                    return;
                }
                
                if (data.status === 'processing') {
                    handleProcessingMessage(data);
                    return;
                }
                
                // 处理完成状态
                if (data.status === 'completed') {
                    if (currentStreamingMessage) {
                        currentStreamingMessage.remove();
                        currentStreamingMessage = null;
                    }
                    if (data.message) {
                        // 添加最终完成的回答
                        addMessage(data.message, 'system');
                    }
                    chatStatus.textContent = '';
                    currentSystemMessage = null;
                    return;
                }
                
                // 处理错误状态
                if (data.status === 'error') {
                    chatStatus.textContent = '处理请求时出错';
                    chatStatus.className = 'error';
                    addMessage(`抱歉，处理您的请求时出现错误: ${data.message}`, 'system');
                    currentSystemMessage = null;
                    return;
                }
                
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };
        
        // 连接关闭事件
        ws.onclose = function() {
            console.log('WebSocket连接已关闭');
            ws = null;
        };
        
        // 连接错误事件
        ws.onerror = function(error) {
            console.error('WebSocket错误:', error);
            chatStatus.textContent = 'WebSocket连接错误';
            chatStatus.className = 'error';
        };
    }
    
    // 添加消息到聊天界面
    // 修改添加消息到聊天界面的函数
    function addMessage(message, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = role + '-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // 根据角色决定是否解析Markdown
        if (role === 'system' && typeof marked !== 'undefined') {
            // 使用marked.js解析Markdown
            contentDiv.innerHTML = marked.parse(message);
        } else {
            // 用户消息或marked未加载时不解析Markdown，直接显示文本
            contentDiv.textContent = message;
        }
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // 滚动到底部
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 只有在marked未定义时才调用init，否则等待marked加载完成后调用
    if (typeof marked !== 'undefined') {
        init();
    }
});