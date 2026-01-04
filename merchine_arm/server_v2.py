#!/usr/bin/env python3
"""
农田机械臂系统 V2 - 模块化版本
每个功能独立测试，确保正确后再集成
支持远程API控制
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
import time
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ============================================================================
# 全局状态
# ============================================================================

# 当前系统状态
current_state = {
    'cart': {'x': 0.0, 'z': 0.0},
    'arm': {'shoulder': 0, 'elbow': 0, 'wrist': 0},
    'gripper': 0,  # 0=关闭, 1=打开
    'status': 'idle',  # idle, moving, working
    'current_cell': 0,
    'timestamp': time.time()
}

# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class Position3D:
    """3D位置"""
    x: float
    y: float
    z: float

@dataclass
class JointAngles:
    """四轴机械臂关节角度"""
    base: float = 0      # 底座旋转
    shoulder: float = 0  # 肩关节
    elbow: float = 0     # 肘关节
    wrist: float = 0     # 腕关节

# ============================================================================
# 测试API - 第一步：验证基础场景
# ============================================================================

@app.route('/')
def index():
    """主页"""
    response = app.make_response(render_template('test_step1.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取系统配置"""
    return jsonify({
        'grid_size': 4,
        'cell_size': 0.5,
        'farm_offset': {'x': -0.75, 'y': -0.75},
        'arm_lengths': {
            'L1': 0.10,
            'L2': 0.30,
            'L3': 0.25,
            'L4': 0.15
        }
    })

@app.route('/api/test/cart_positions', methods=['GET'])
def test_cart_positions():
    """
    测试API：返回小车访问16个格子的路径
    小车会停在每个格子的左侧，模拟工作位置
    """
    positions = [
        {'x': -1.5, 'y': -1.5, 'label': '起点'}
    ]
    
    # 农田配置
    grid_size = 4
    cell_size = 0.5
    farm_offset_x = -0.75
    farm_offset_y = -0.75
    cart_offset = 0.45  # 小车停在格子左侧的距离
    
    # Z字形路径访问所有格子
    for row in range(grid_size):
        # 偶数行从左到右，奇数行从右到左
        cols = range(grid_size) if row % 2 == 0 else range(grid_size - 1, -1, -1)
        
        for col in cols:
            # 格子中心位置
            cell_center_x = farm_offset_x + col * cell_size + cell_size / 2
            cell_center_y = farm_offset_y + row * cell_size + cell_size / 2
            
            # 小车停在格子左侧
            cart_x = cell_center_x - cart_offset
            cart_y = cell_center_y
            
            positions.append({
                'x': cart_x,
                'y': cart_y,
                'label': f'格子[{row},{col}]'
            })
    
    # 返回起点
    positions.append({'x': -1.5, 'y': -1.5, 'label': '返回起点'})
    
    return jsonify({'positions': positions})

# ============================================================================
# 远程控制API - 小车位置
# ============================================================================

@app.route('/api/cart/position', methods=['GET'])
def get_cart_position():
    """获取小车当前位置"""
    return jsonify({
        'success': True,
        'position': current_state['cart'],
        'timestamp': current_state['timestamp']
    })

@app.route('/api/cart/position', methods=['POST'])
def set_cart_position():
    """设置小车位置"""
    data = request.get_json()
    
    if 'x' in data:
        current_state['cart']['x'] = float(data['x'])
    if 'z' in data:
        current_state['cart']['z'] = float(data['z'])
    
    current_state['timestamp'] = time.time()
    
    # 广播更新到所有连接的客户端
    socketio.emit('cart_update', current_state['cart'])
    
    return jsonify({
        'success': True,
        'position': current_state['cart']
    })

@app.route('/api/cart/move', methods=['POST'])
def move_cart():
    """移动小车到指定位置（带动画）"""
    data = request.get_json()
    
    target_x = float(data.get('x', current_state['cart']['x']))
    target_z = float(data.get('z', current_state['cart']['z']))
    duration = float(data.get('duration', 1.5))  # 默认1.5秒
    
    # 广播移动命令
    socketio.emit('cart_move', {
        'target': {'x': target_x, 'z': target_z},
        'duration': duration
    })
    
    # 更新目标状态
    current_state['cart']['x'] = target_x
    current_state['cart']['z'] = target_z
    current_state['timestamp'] = time.time()
    
    return jsonify({
        'success': True,
        'from': current_state['cart'],
        'to': {'x': target_x, 'z': target_z},
        'duration': duration
    })

# ============================================================================
# 远程控制API - 机械臂
# ============================================================================

@app.route('/api/arm/joints', methods=['GET'])
def get_arm_joints():
    """获取机械臂关节角度"""
    return jsonify({
        'success': True,
        'joints': current_state['arm'],
        'timestamp': current_state['timestamp']
    })

@app.route('/api/arm/joints', methods=['POST'])
def set_arm_joints():
    """设置机械臂关节角度"""
    data = request.get_json()
    
    if 'shoulder' in data:
        current_state['arm']['shoulder'] = int(data['shoulder'])
    if 'elbow' in data:
        current_state['arm']['elbow'] = int(data['elbow'])
    if 'wrist' in data:
        current_state['arm']['wrist'] = int(data['wrist'])
    
    current_state['timestamp'] = time.time()
    
    # 广播更新
    socketio.emit('arm_update', current_state['arm'])
    
    return jsonify({
        'success': True,
        'joints': current_state['arm']
    })

@app.route('/api/arm/move', methods=['POST'])
def move_arm():
    """移动机械臂到指定角度（带动画）"""
    data = request.get_json()
    
    target = {
        'shoulder': int(data.get('shoulder', current_state['arm']['shoulder'])),
        'elbow': int(data.get('elbow', current_state['arm']['elbow'])),
        'wrist': int(data.get('wrist', current_state['arm']['wrist']))
    }
    duration = float(data.get('duration', 1.0))
    
    # 广播移动命令
    socketio.emit('arm_move', {
        'target': target,
        'duration': duration
    })
    
    # 更新状态
    current_state['arm'] = target
    current_state['timestamp'] = time.time()
    
    return jsonify({
        'success': True,
        'target': target,
        'duration': duration
    })

# ============================================================================
# 远程控制API - 抓手
# ============================================================================

@app.route('/api/gripper', methods=['GET'])
def get_gripper():
    """获取抓手状态"""
    return jsonify({
        'success': True,
        'gripper': current_state['gripper'],
        'state': 'open' if current_state['gripper'] == 1 else 'closed'
    })

@app.route('/api/gripper', methods=['POST'])
def set_gripper():
    """设置抓手状态"""
    data = request.get_json()
    
    if 'state' in data:
        current_state['gripper'] = 1 if data['state'] in [1, '1', 'open', True] else 0
    
    current_state['timestamp'] = time.time()
    
    # 广播更新
    socketio.emit('gripper_update', current_state['gripper'])
    
    return jsonify({
        'success': True,
        'gripper': current_state['gripper'],
        'state': 'open' if current_state['gripper'] == 1 else 'closed'
    })

# ============================================================================
# 远程控制API - 系统状态
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取完整系统状态"""
    return jsonify({
        'success': True,
        'state': current_state
    })

@app.route('/api/reset', methods=['POST'])
def reset_system():
    """重置系统到初始状态"""
    current_state['cart'] = {'x': 0.0, 'z': 0.0}
    current_state['arm'] = {'shoulder': 0, 'elbow': 0, 'wrist': 0}
    current_state['gripper'] = 0
    current_state['status'] = 'idle'
    current_state['current_cell'] = 0
    current_state['timestamp'] = time.time()
    
    # 广播重置命令
    socketio.emit('system_reset', current_state)
    
    return jsonify({
        'success': True,
        'message': 'System reset to initial state',
        'state': current_state
    })

# ============================================================================
# 远程控制API - 预设动作
# ============================================================================

@app.route('/api/action/pull_grass', methods=['POST'])
def action_pull_grass():
    """执行拔草动作"""
    data = request.get_json()
    cell = data.get('cell', 0)
    
    # 广播拔草命令
    socketio.emit('action', {
        'type': 'pull_grass',
        'cell': cell
    })
    
    return jsonify({
        'success': True,
        'action': 'pull_grass',
        'cell': cell
    })

@app.route('/api/action/plant_seed', methods=['POST'])
def action_plant_seed():
    """执行播种动作"""
    data = request.get_json()
    cell = data.get('cell', 0)
    
    # 广播播种命令
    socketio.emit('action', {
        'type': 'plant_seed',
        'cell': cell
    })
    
    return jsonify({
        'success': True,
        'action': 'plant_seed',
        'cell': cell
    })

@app.route('/api/action/full_cycle', methods=['POST'])
def action_full_cycle():
    """执行完整拔草+播种循环"""
    # 广播完整循环命令
    socketio.emit('action', {
        'type': 'full_cycle'
    })
    
    return jsonify({
        'success': True,
        'action': 'full_cycle',
        'message': 'Starting full cycle for all 16 cells'
    })

# ============================================================================
# WebSocket事件处理
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'state': current_state})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('state_update')
def handle_state_update(data):
    """接收客户端状态更新"""
    if 'cart' in data:
        current_state['cart'] = data['cart']
    if 'arm' in data:
        current_state['arm'] = data['arm']
    if 'gripper' in data:
        current_state['gripper'] = data['gripper']
    
    current_state['timestamp'] = time.time()
    
    # 广播到其他客户端
    emit('state_sync', current_state, broadcast=True, include_self=False)

if __name__ == '__main__':
    print("=" * 60)
    print("农田机械臂系统 V2 - 远程控制版本")
    print("=" * 60)
    print("Web界面: http://localhost:7070")
    print("API文档: http://localhost:7070/api/status")
    print("=" * 60)
    print("支持的API端点:")
    print("  GET  /api/status          - 获取系统状态")
    print("  POST /api/reset           - 重置系统")
    print("  GET  /api/cart/position   - 获取小车位置")
    print("  POST /api/cart/position   - 设置小车位置")
    print("  POST /api/cart/move       - 移动小车")
    print("  GET  /api/arm/joints      - 获取关节角度")
    print("  POST /api/arm/joints      - 设置关节角度")
    print("  POST /api/arm/move        - 移动机械臂")
    print("  GET  /api/gripper         - 获取抓手状态")
    print("  POST /api/gripper         - 设置抓手状态")
    print("  POST /api/action/pull_grass - 拔草动作")
    print("  POST /api/action/plant_seed - 播种动作")
    print("  POST /api/action/full_cycle - 完整循环")
    print("=" * 60)
    print("WebSocket已启用，支持实时双向通信")
    print("=" * 60)
    socketio.run(app, debug=True, host='0.0.0.0', port=7070, allow_unsafe_werkzeug=True)

