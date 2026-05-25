// TCA-System V2.0 WebSocket客户端
// ================================

class TCAWebSocket {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.handlers = {};
    }

    connect() {
        this.socket = io(window.location.origin, {
            transports: ['websocket', 'polling'],
            withCredentials: true
        });

        this.socket.on('connect', () => {
            this.connected = true;
            console.log('[WS] 已连接');
            this.emit('connected', { status: 'connected' });
        });

        this.socket.on('disconnect', () => {
            this.connected = false;
            console.log('[WS] 已断开');
            this.emit('disconnected', { status: 'disconnected' });
        });

        this.socket.on('connected', (data) => {
            console.log('[WS] 服务器确认连接:', data);
            this.emit('server_connected', data);
        });

        this.socket.on('student_update', (data) => {
            console.log('[WS] 学生状态更新:', data);
            this.emit('student_update', data);
        });

        this.socket.on('teacher_override', (data) => {
            console.log('[WS] 教师干预:', data);
            this.emit('teacher_override', data);
        });

        this.socket.on('help_request', (data) => {
            console.log('[WS] 求助请求:', data);
            this.emit('help_request', data);
        });

        this.socket.on('agent_response', (data) => {
            console.log('[WS] 智能体响应:', data);
            this.emit('agent_response', data);
        });

        this.socket.on('room_joined', (data) => {
            console.log('[WS] 已加入房间:', data.room);
        });

        this.socket.on('help_sent', (data) => {
            console.log('[WS] 求助已发送:', data);
        });

        this.socket.on('override_sent', (data) => {
            console.log('[WS] 干预已发送:', data);
        });

        this.socket.on('error', (data) => {
            console.error('[WS] 错误:', data);
            this.emit('error', data);
        });
    }

    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    off(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event] = this.handlers[event].filter(h => h !== handler);
        }
    }

    emit(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => handler(data));
        }
    }

    sendStudentUpdate(studentId, action, data = {}) {
        if (!this.connected) {
            console.warn('[WS] 未连接');
            return;
        }
        this.socket.emit('student_update', {
            student_id: studentId,
            action: action,
            data: data
        });
    }

    sendTeacherOverride(studentId, overrideType, content, targetAgent = 'Guide') {
        if (!this.connected) {
            console.warn('[WS] 未连接');
            return;
        }
        this.socket.emit('teacher_override', {
            student_id: studentId,
            override_type: overrideType,
            content: content,
            target_agent: targetAgent
        });
    }

    sendHelpRequest(questionId, content) {
        if (!this.connected) {
            console.warn('[WS] 未连接');
            return;
        }
        this.socket.emit('help_request', {
            question_id: questionId,
            content: content
        });
    }

    joinRoom(roomName) {
        if (!this.connected) {
            console.warn('[WS] 未连接');
            return;
        }
        this.socket.emit('join_room', { room: roomName });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.connected = false;
        }
    }
}

window.TCAWebSocket = TCAWebSocket;
