# 农田机械臂系统 - API文档

## 📡 概述

本系统提供完整的REST API和WebSocket接口，支持远程控制小车、机械臂和执行预设动作。

**服务器地址**: `http://localhost:7070`（局域网内可用服务器IP地址访问）

---

## 🌐 API端点列表

### 系统状态

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/status` | 获取完整系统状态 |
| POST | `/api/reset` | 重置系统到初始状态 |

### 小车控制

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/cart/position` | 获取小车当前位置 |
| POST | `/api/cart/position` | 设置小车位置（瞬间移动） |
| POST | `/api/cart/move` | 移动小车（带动画） |

### 机械臂控制

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/arm/joints` | 获取关节角度 |
| POST | `/api/arm/joints` | 设置关节角度（瞬间移动） |
| POST | `/api/arm/move` | 移动机械臂（带动画） |

### 抓手控制

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/gripper` | 获取抓手状态 |
| POST | `/api/gripper` | 设置抓手状态 |

### 预设动作

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/action/pull_grass` | 执行拔草动作 |
| POST | `/api/action/plant_seed` | 执行播种动作 |
| POST | `/api/action/full_cycle` | 执行完整16格循环 |

---

## 📖 详细文档

### 1. 获取系统状态

**请求**:
```http
GET /api/status
```

**响应**:
```json
{
  "success": true,
  "state": {
    "cart": {"x": 0.0, "z": 0.0},
    "arm": {"shoulder": 0, "elbow": 0, "wrist": 0},
    "gripper": 0,
    "status": "idle",
    "current_cell": 0,
    "timestamp": 1698765432.123
  }
}
```

**curl示例**:
```bash
curl http://localhost:7070/api/status
```

---

### 2. 重置系统

**请求**:
```http
POST /api/reset
Content-Type: application/json
```

**响应**:
```json
{
  "success": true,
  "message": "System reset to initial state",
  "state": { /* 初始状态 */ }
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/reset
```

---

### 3. 获取小车位置

**请求**:
```http
GET /api/cart/position
```

**响应**:
```json
{
  "success": true,
  "position": {"x": 0.5, "z": -0.3},
  "timestamp": 1698765432.123
}
```

**curl示例**:
```bash
curl http://localhost:7070/api/cart/position
```

---

### 4. 设置小车位置（瞬间移动）

**请求**:
```http
POST /api/cart/position
Content-Type: application/json

{
  "x": 0.5,
  "z": -0.3
}
```

**参数**:
- `x` (可选): X轴位置，范围 -1.5 ~ 1.5
- `z` (可选): Z轴位置，范围 -1.5 ~ 1.5

**响应**:
```json
{
  "success": true,
  "position": {"x": 0.5, "z": -0.3}
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/cart/position \
  -H "Content-Type: application/json" \
  -d '{"x": 0.5, "z": -0.3}'
```

---

### 5. 移动小车（带动画）

**请求**:
```http
POST /api/cart/move
Content-Type: application/json

{
  "x": 0.5,
  "z": -0.3,
  "duration": 2.0
}
```

**参数**:
- `x` (必需): 目标X轴位置
- `z` (必需): 目标Z轴位置
- `duration` (可选): 动画时长（秒），默认1.5

**响应**:
```json
{
  "success": true,
  "from": {"x": 0.0, "z": 0.0},
  "to": {"x": 0.5, "z": -0.3},
  "duration": 2.0
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/cart/move \
  -H "Content-Type: application/json" \
  -d '{"x": 0.5, "z": -0.3, "duration": 2.0}'
```

---

### 6. 获取机械臂关节角度

**请求**:
```http
GET /api/arm/joints
```

**响应**:
```json
{
  "success": true,
  "joints": {
    "shoulder": 45,
    "elbow": -60,
    "wrist": 30
  },
  "timestamp": 1698765432.123
}
```

**curl示例**:
```bash
curl http://localhost:7070/api/arm/joints
```

---

### 7. 设置机械臂关节角度（瞬间移动）

**请求**:
```http
POST /api/arm/joints
Content-Type: application/json

{
  "shoulder": 45,
  "elbow": -60,
  "wrist": 30
}
```

**参数**:
- `shoulder` (可选): 肩关节角度，范围 -180 ~ 180
- `elbow` (可选): 肘关节角度，范围 -180 ~ 180
- `wrist` (可选): 腕关节角度，范围 -180 ~ 180

**响应**:
```json
{
  "success": true,
  "joints": {
    "shoulder": 45,
    "elbow": -60,
    "wrist": 30
  }
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/arm/joints \
  -H "Content-Type: application/json" \
  -d '{"shoulder": 45, "elbow": -60, "wrist": 30}'
```

---

### 8. 移动机械臂（带动画）

**请求**:
```http
POST /api/arm/move
Content-Type: application/json

{
  "shoulder": 45,
  "elbow": -60,
  "wrist": 30,
  "duration": 1.5
}
```

**参数**:
- `shoulder` (可选): 目标肩关节角度
- `elbow` (可选): 目标肘关节角度
- `wrist` (可选): 目标腕关节角度
- `duration` (可选): 动画时长（秒），默认1.0

**响应**:
```json
{
  "success": true,
  "target": {
    "shoulder": 45,
    "elbow": -60,
    "wrist": 30
  },
  "duration": 1.5
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/arm/move \
  -H "Content-Type: application/json" \
  -d '{"shoulder": 45, "elbow": -60, "wrist": 30, "duration": 1.5}'
```

---

### 9. 获取抓手状态

**请求**:
```http
GET /api/gripper
```

**响应**:
```json
{
  "success": true,
  "gripper": 1,
  "state": "open"
}
```

**curl示例**:
```bash
curl http://localhost:7070/api/gripper
```

---

### 10. 设置抓手状态

**请求**:
```http
POST /api/gripper
Content-Type: application/json

{
  "state": "open"
}
```

**参数**:
- `state`: `"open"` / `"closed"` / `1` / `0` / `true` / `false`

**响应**:
```json
{
  "success": true,
  "gripper": 1,
  "state": "open"
}
```

**curl示例**:
```bash
# 打开抓手
curl -X POST http://localhost:7070/api/gripper \
  -H "Content-Type: application/json" \
  -d '{"state": "open"}'

# 关闭抓手
curl -X POST http://localhost:7070/api/gripper \
  -H "Content-Type: application/json" \
  -d '{"state": "closed"}'
```

---

### 11. 执行拔草动作

**请求**:
```http
POST /api/action/pull_grass
Content-Type: application/json

{
  "cell": 0
}
```

**参数**:
- `cell` (可选): 格子索引（0-15），默认0

**响应**:
```json
{
  "success": true,
  "action": "pull_grass",
  "cell": 0
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/action/pull_grass \
  -H "Content-Type: application/json" \
  -d '{"cell": 5}'
```

---

### 12. 执行播种动作

**请求**:
```http
POST /api/action/plant_seed
Content-Type: application/json

{
  "cell": 0
}
```

**参数**:
- `cell` (可选): 格子索引（0-15），默认0

**响应**:
```json
{
  "success": true,
  "action": "plant_seed",
  "cell": 0
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/action/plant_seed \
  -H "Content-Type: application/json" \
  -d '{"cell": 5}'
```

---

### 13. 执行完整循环

**请求**:
```http
POST /api/action/full_cycle
```

**响应**:
```json
{
  "success": true,
  "action": "full_cycle",
  "message": "Starting full cycle for all 16 cells"
}
```

**curl示例**:
```bash
curl -X POST http://localhost:7070/api/action/full_cycle
```

---

## 🔌 WebSocket实时通信

除了REST API，系统还支持WebSocket实时双向通信。

**连接地址**: `ws://localhost:7070/socket.io/`

### 客户端事件（发送到服务器）

| 事件名 | 描述 | 数据 |
|--------|------|------|
| `connect` | 连接服务器 | - |
| `state_update` | 更新状态 | `{cart, arm, gripper}` |

### 服务器事件（服务器发送）

| 事件名 | 描述 | 数据 |
|--------|------|------|
| `connected` | 连接成功 | `{state}` |
| `cart_update` | 小车位置更新 | `{x, z}` |
| `cart_move` | 小车移动命令 | `{target, duration}` |
| `arm_update` | 机械臂角度更新 | `{shoulder, elbow, wrist}` |
| `arm_move` | 机械臂移动命令 | `{target, duration}` |
| `gripper_update` | 抓手状态更新 | `0/1` |
| `action` | 执行动作 | `{type, cell}` |
| `system_reset` | 系统重置 | `{state}` |
| `state_sync` | 状态同步 | `{state}` |

---

## 🐍 Python客户端示例

```python
import requests

# 初始化
BASE_URL = "http://localhost:7070"

# 获取状态
response = requests.get(f"{BASE_URL}/api/status")
print(response.json())

# 移动小车
requests.post(f"{BASE_URL}/api/cart/move", json={
    "x": 0.5,
    "z": 0.5,
    "duration": 2.0
})

# 移动机械臂
requests.post(f"{BASE_URL}/api/arm/move", json={
    "shoulder": 45,
    "elbow": -60,
    "wrist": 30,
    "duration": 1.5
})

# 控制抓手
requests.post(f"{BASE_URL}/api/gripper", json={"state": "open"})
requests.post(f"{BASE_URL}/api/gripper", json={"state": "closed"})

# 执行动作
requests.post(f"{BASE_URL}/api/action/pull_grass", json={"cell": 5})
requests.post(f"{BASE_URL}/api/action/plant_seed", json={"cell": 5})
```

---

## 🌍 JavaScript客户端示例

```javascript
const BASE_URL = "http://localhost:7070";

// 获取状态
fetch(`${BASE_URL}/api/status`)
  .then(res => res.json())
  .then(data => console.log(data));

// 移动小车
fetch(`${BASE_URL}/api/cart/move`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({x: 0.5, z: 0.5, duration: 2.0})
})
.then(res => res.json())
.then(data => console.log(data));

// 移动机械臂
fetch(`${BASE_URL}/api/arm/move`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    shoulder: 45,
    elbow: -60,
    wrist: 30,
    duration: 1.5
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 📱 从其他设备控制

### 1. 确定服务器IP地址

在运行服务器的电脑上：
```bash
# Linux/Mac
ifconfig | grep "inet "

# Windows
ipconfig
```

假设服务器IP是 `192.168.1.100`

### 2. 从手机/平板访问

浏览器访问:
```
http://192.168.1.100:7070
```

### 3. 从其他电脑控制

修改Python客户端的BASE_URL:
```python
BASE_URL = "http://192.168.1.100:7070"
```

### 4. 从树莓派/Arduino控制

```python
import requests
import time

SERVER = "http://192.168.1.100:7070"

# 示例：循环控制
while True:
    # 读取传感器数据
    sensor_value = read_sensor()
    
    # 根据传感器控制机械臂
    if sensor_value > threshold:
        requests.post(f"{SERVER}/api/action/pull_grass")
    
    time.sleep(1)
```

---

## ⚠️ 注意事项

1. **网络要求**: 
   - 所有设备必须在同一局域网内
   - 确保防火墙允许7070端口

2. **并发控制**:
   - 多个客户端可以同时连接
   - 状态会通过WebSocket实时同步

3. **安全性**:
   - 当前版本无身份验证
   - 建议仅在内网使用
   - 生产环境需添加认证机制

4. **性能**:
   - 建议控制请求频率 < 10次/秒
   - 动画执行期间避免发送新命令

---

## 🧪 测试工具

系统提供了测试客户端：

```bash
# 基础控制测试
python api_test_client.py basic

# 顺序动作测试
python api_test_client.py sequence

# 远程监控模式
python api_test_client.py monitor
```

---

## 📞 技术支持

遇到问题？检查：
1. 服务器是否正常运行
2. 网络连接是否正常
3. API端点和参数是否正确
4. 查看服务器控制台日志

---

**更新日期**: 2025-10-27  
**版本**: v2.0 - 远程控制版

