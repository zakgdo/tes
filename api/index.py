from flask import Flask, request, jsonify
import json
import random
import string
from datetime import datetime
import os

app = Flask(__name__)

# ============== 核心修改1：用文件存储替代内存，解决数据丢失问题 ==============
# 定义数据文件路径，保存在Vercel的可写临时目录
DATA_FILE = '/tmp/booking_data.json'

def load_data():
    """从文件加载所有数据（团期和预订记录）"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            # 如果文件读取失败，返回初始空数据
            return {'tours': [], 'bookings': []}
    # 文件不存在，返回初始空数据
    return {'tours': [], 'bookings': []}

def save_data(data):
    """将所有数据保存到文件"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 程序启动时加载数据
app_data = load_data()
# 为了方便，将两个列表单独取出作为变量，但记住它们来自 app_data
tours_db = app_data['tours']
bookings_db = app_data['bookings']
# ============== 核心修改1结束 ==============

# ---------- 工具函数 ----------
def generate_booking_code():
    return 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_html_template(title, body_content):
    """生成完整的HTML页面框架（未做修改）"""
    return f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>{title} - 车位预订系统</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* 全局CSS样式 */
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; }}
        body {{ background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: #333; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .navbar {{ background: white; padding: 15px 25px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .logo {{ font-size: 1.5rem; font-weight: bold; color: #6a11cb; text-decoration: none; }}
        .nav-links a {{ margin-left: 20px; color: #555; text-decoration: none; font-weight: 500; }}
        .card {{ background: white; border-radius: 16px; padding: 25px; margin-bottom: 25px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); transition: transform 0.3s; }}
        .card:hover {{ transform: translateY(-5px); }}
        .btn {{ display: inline-block; background: linear-gradient(to right, #6a11cb, #2575fc); color: white; padding: 12px 28px; border-radius: 50px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; font-size: 1rem; }}
        .btn:hover {{ opacity: 0.9; }}
        .tour-card {{ border-left: 6px solid #6a11cb; }}
        .status-available {{ background: #d4edda; color: #155724; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; display: inline-block; }}
        .status-full {{ background: #f8d7da; color: #721c24; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; display: inline-block; }}
        .progress-bar {{ height: 10px; background: #e9ecef; border-radius: 5px; overflow: hidden; margin: 15px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(to right, #00b09b, #96c93d); border-radius: 5px; }}
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .container {{ padding: 0 10px; }}
            .navbar {{ flex-direction: column; text-align: center; padding: 15px; }}
            .nav-links {{ margin-top: 15px; }}
            .nav-links a {{ margin: 0 10px; }}
            .card {{ padding: 20px; }}
        }}
        /* ============== 核心修改2：新增的座位选择样式 ============== */
        .seat-map {{
            display: grid;
            grid-template-columns: repeat(5, 1fr); /* 每行最多5个座位 */
            gap: 10px;
            margin: 20px 0;
        }}
        .seat {{
            padding: 15px;
            text-align: center;
            background: #e9ecef;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            border: 2px solid #dee2e6;
            transition: all 0.2s;
        }}
        .seat:hover {{
            background: #d0ebff;
            border-color: #74c0fc;
        }}
        .seat.selected {{
            background: #51cf66;
            color: white;
            border-color: #2b8a3e;
        }}
        .seat.unavailable {{
            background: #ffc9c9;
            color: #868e96;
            cursor: not-allowed;
            border-color: #fa5252;
        }}
        /* ============== 核心修改2结束 ============== */
    </style>
</head>
<body>
    <!-- ============== 核心修改3：修改导航栏，区分主/子系统入口 ============== -->
    <nav class="navbar">
        <a href="/" class="logo"><i class="fas fa-bus"></i> 车位预订</a>
        <div class="nav-links">
            <!-- 这是给客人看的首页链接 -->
            <a href="/"><i class="fas fa-home"></i> 预订首页</a>
            <!-- 这是管理员入口，直接链接到管理后台，没有密码保护 -->
            <a href="/admin"><i class="fas fa-cog"></i> 管理后台</a>
        </div>
    </nav>
    <!-- ============== 核心修改3结束 ============== -->
    <div class="container">
        {body_content}
    </div>
    <footer style="text-align: center; color: white; margin-top: 50px; padding: 20px; opacity: 0.8;">
        <p>© 2024 车位预订系统 | 数据已持久化保存 | 适配所有设备</p>
    </footer>
    <script>
        function showAlert(msg, type='success') {{
            alert(msg);
        }}
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => alert('已复制: ' + text));
        }}
    </script>
</body>
</html>
'''

# ---------- 网站页面路由 ----------
@app.route('/')
def home():
    """系统首页（客人子系统）"""
    # 从文件加载最新数据
    global tours_db
    app_data = load_data()
    tours_db = app_data['tours']
    
    tours_html = ''
    for tour in tours_db:
        available = tour['max_seats'] - tour['booked']
        percent = int((tour['booked'] / tour['max_seats']) * 100) if tour['max_seats'] > 0 else 0
        status = 'status-full' if available == 0 else 'status-available'
        status_text = '已满员' if available == 0 else f'可预订 ({available}个空位)'
        
        tours_html += f'''
        <div class="card tour-card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <h2 style="color: #2575fc;">{tour['destination']}</h2>
                <span class="{status}">{status_text}</span>
            </div>
            <p><i class="far fa-calendar"></i> {tour['date']} {tour['time']} 出发</p>
            <p><i class="fas fa-users"></i> 座位: {tour['booked']}/{tour['max_seats']} (满{tour['max_seats']}人发车)</p>
            <div class="progress-bar"><div class="progress-fill" style="width:{percent}%"></div></div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px;">
                <span>已报名 {tour['booked']} 人</span>
                {'<button class="btn" onclick="location.href=\'/book/' + str(tour['id']) + '\'"><i class="fas fa-ticket-alt"></i> 选择座位并预订</button>' if available > 0 else '<button class="btn" style="background:#6c757d;" disabled><i class="fas fa-ban"></i> 已满员</button>'}
            </div>
        </div>
        '''
    
    body_content = f'''
    <h1 style="color: white; text-align: center; margin-bottom: 30px;">🚌 在线车位预订（客人）</h1>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px;">
        <div class="card" style="text-align: center; background: rgba(255,255,255,0.95);">
            <h3><i class="fas fa-calendar-day"></i> 进行中团期</h3>
            <p style="font-size: 2.5rem; color: #6a11cb; margin: 10px 0;">{len(tours_db)}</p>
        </div>
        <div class="card" style="text-align: center; background: rgba(255,255,255,0.95);">
            <h3><i class="fas fa-user-check"></i> 总预订人数</h3>
            <p style="font-size: 2.5rem; color: #00b09b; margin: 10px 0;">{sum(t.get('booked', 0) for t in tours_db)}</p>
        </div>
    </div>
    <h2 style="color: white; margin-bottom: 20px;">可预订班次</h2>
    {tours_html if tours_html else '<div class="card"><p style="text-align:center;color:#666;">暂无团期，请稍后查看。</p></div>'}
    <div class="card">
        <h3><i class="fas fa-info-circle"></i> 使用说明</h3>
        <ul style="margin-left: 20px; margin-top: 15px; color: #555;">
            <li>点击<strong>“选择座位并预订”</strong>进入选座页面。</li>
            <li>每个座位都需要单独选择，支持为多人同时预订。</li>
            <li>预订成功后，请保存好唯一的预订码。</li>
            <li>如需管理班次或查看数据，请使用<strong>管理后台</strong>。</li>
        </ul>
    </div>
    '''
    return get_html_template('首页', body_content)

@app.route('/book/<int:tour_id>')
def book_page(tour_id):
    """预订页面（客人子系统）- 新增选座功能"""
    # 从文件加载最新数据
    global tours_db
    app_data = load_data()
    tours_db = app_data['tours']
    
    tour = next((t for t in tours_db if t['id'] == tour_id), None)
    if not tour:
        return get_html_template('错误', '<div class="card"><h2>班次不存在</h2></div>')
    
    # ============== 核心修改2：生成座位图数据 ==============
    # 获取该班次的所有预订，找出已被选的座位号
    bookings_for_tour = [b for b in app_data['bookings'] if b['tour_id'] == tour_id]
    taken_seats = []
    for b in bookings_for_tour:
        # 将预订的座位号加入已选列表（一个预订可能有多个座位）
        seat_nums = b.get('seat_numbers', [])
        if isinstance(seat_nums, list):
            taken_seats.extend(seat_nums)
        elif seat_nums:  # 如果是单个数字
            taken_seats.append(seat_nums)
    
    # 生成座位图的HTML
    seat_html = ''
    for seat_num in range(1, tour['max_seats'] + 1):
        seat_status = 'unavailable' if seat_num in taken_seats else 'available'
        seat_html += f'<div class="seat {seat_status}" data-seat="{seat_num}" onclick="selectSeat(this)">{seat_num}号</div>'
    # ============== 核心修改2结束 ==============
    
    body_content = f'''
    <div style="max-width: 900px; margin: 0 auto;">
        <a href="/" class="btn" style="background: #6c757d; margin-bottom: 20px;"><i class="fas fa-arrow-left"></i> 返回首页</a>
        <div class="card">
            <h1><i class="fas fa-ticket-alt"></i> 预订 {tour['destination']}</h1>
            <p style="color: #666; margin: 15px 0;"><i class="far fa-calendar"></i> {tour['date']} {tour['time']} 出发</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px;">
                <div>
                    <h3><i class="fas fa-edit"></i> 1. 选择座位</h3>
                    <p style="color: #666; margin-bottom: 10px;">请点击下方选择座位（绿色可选，红色已订）：</p>
                    <div class="seat-map" id="seatMap">
                        {seat_html}
                    </div>
                    <p style="color: #666; margin-top: 10px;">已选座位：<span id="selectedSeatsDisplay">无</span></p>
                    
                    <h3 style="margin-top: 30px;"><i class="fas fa-user-edit"></i> 2. 填写信息</h3>
                    <form id="bookingForm" onsubmit="submitBooking(event, {tour_id})" style="margin-top: 20px;">
                        <input type="hidden" id="selectedSeatsInput" name="selectedSeats" value="">
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600;">姓名 *</label>
                            <input type="text" id="customerName" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem;">
                        </div>
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600;">手机号 *</label>
                            <input type="tel" id="customerPhone" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem;" pattern="[0-9]{{11}}">
                        </div>
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 25px 0;">
                            <p><i class="fas fa-info-circle"></i> 本班次总座位: <strong>{tour['max_seats']}</strong> 个</p>
                            <p><i class="fas fa-chair"></i> 剩余空位: <strong style="color:#00b09b;">{tour['max_seats'] - tour['booked']}</strong> 个</p>
                            <p id="seatSelectionWarning" style="color:#e74c3c; display:none;"><i class="fas fa-exclamation-triangle"></i> 请至少选择一个座位！</p>
                        </div>
                        <button type="submit" class="btn" style="width: 100%; padding: 15px; font-size: 1.1rem;">
                            <i class="fas fa-check-circle"></i> 提交预订
                        </button>
                    </form>
                </div>
                
                <div>
                    <h3><i class="fas fa-list-check"></i> 班次详情</h3>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <span>目的地:</span><strong>{tour['destination']}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <span>出发时间:</span><strong>{tour['date']} {tour['time']}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <span>总座位数:</span><strong>{tour['max_seats']} 座</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <span>已预订:</span><strong>{tour['booked']} 人</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                            <span>状态:</span>
                            <span class="{'status-full' if tour['max_seats'] - tour['booked'] == 0 else 'status-available'}">
                                {'已满员' if tour['max_seats'] - tour['booked'] == 0 else '正常预订中'}
                            </span>
                        </div>
                    </div>
                    
                    <h3 style="margin-top: 30px;"><i class="fas fa-users"></i> 已选座位预览</h3>
                    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <p style="color: #856404;"><i class="fas fa-lightbulb"></i> 左侧选择的座位号将显示在这里。请确保座位选择正确后再提交。</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    let selectedSeats = [];
    
    function selectSeat(element) {{
        // 如果座位不可用，直接返回
        if (element.classList.contains('unavailable')) return;
        
        const seatNum = parseInt(element.getAttribute('data-seat'));
        const index = selectedSeats.indexOf(seatNum);
        
        if (index === -1) {{
            // 选中座位
            selectedSeats.push(seatNum);
            element.classList.add('selected');
        }} else {{
            // 取消选中
            selectedSeats.splice(index, 1);
            element.classList.remove('selected');
        }}
        
        // 更新显示
        document.getElementById('selectedSeatsDisplay').textContent = 
            selectedSeats.length > 0 ? selectedSeats.join(', ') : '无';
        document.getElementById('selectedSeatsInput').value = selectedSeats.join(',');
        
        // 隐藏警告
        document.getElementById('seatSelectionWarning').style.display = 'none';
    }}
    
    async function submitBooking(event, tourId) {{
        event.preventDefault();
        
        // 验证是否选择了座位
        if (selectedSeats.length === 0) {{
            document.getElementById('seatSelectionWarning').style.display = 'block';
            return;
        }}
        
        const name = document.getElementById('customerName').value;
        const phone = document.getElementById('customerPhone').value;
        const seats = selectedSeats; // 现在使用选择的座位数组
        
        const btn = event.target.querySelector('button[type="submit"]');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';
        btn.disabled = true;
        
        try {{
            const response = await fetch('/api/book', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    tour_id: tourId, 
                    name: name, 
                    phone: phone, 
                    seat_numbers: seats  // 改为传递座位号数组
                }})
            }});
            const result = await response.json();
            
            if (result.success) {{
                document.getElementById('bookingForm').innerHTML = `
                    <div style="text-align: center; padding: 40px 20px;">
                        <i class="fas fa-check-circle" style="font-size: 4rem; color: #00b09b;"></i>
                        <h2>预订成功！</h2>
                        <p>您的座位已确认，请保存好预订码</p>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0; font-family: monospace;">
                            <p style="color: #666;">预订码</p>
                            <h1 style="color: #e74c3c; letter-spacing: 3px;">${{result.booking_code}}</h1>
                        </div>
                        <p><strong>已选座位：</strong>${{seats.join(', ')}}号</p>
                        <p><button class="btn" onclick="copyToClipboard('${{result.booking_code}}')" style="margin-top: 15px;"><i class="fas fa-copy"></i> 复制预订码</button></p>
                        <p style="margin-top: 20px;"><a href="/" class="btn" style="background: #6c757d;">返回首页</a></p>
                    </div>
                `;
            }} else {{
                alert('预订失败: ' + result.message);
                btn.innerHTML = '<i class="fas fa-check-circle"></i> 提交预订';
                btn.disabled = false;
            }}
        }} catch (error) {{
            alert('网络错误，请重试');
            btn.innerHTML = '<i class="fas fa-check-circle"></i> 提交预订';
            btn.disabled = false;
        }}
    }}
    </script>
    '''
    return get_html_template(f'预订 {tour["destination"]}', body_content)

@app.route('/admin')
def admin_page():
    """管理后台页面（主系统/管理员专用）"""
    # 从文件加载最新数据
    global tours_db, bookings_db
    app_data = load_data()
    tours_db = app_data['tours']
    bookings_db = app_data['bookings']
    
    # ============== 核心修改3：管理员界面显示更多信息 ==============
    # 生成团期管理表格
    tours_table_html = ''
    for t in tours_db:
        tours_table_html += f'''
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px;">{t['id']}</td>
            <td style="padding: 12px;"><strong>{t['destination']}</strong></td>
            <td style="padding: 12px;">{t['date']} {t['time']}</td>
            <td style="padding: 12px;">{t['max_seats']}</td>
            <td style="padding: 12px;">{t['booked']}</td>
            <td style="padding: 12px;">
                <span class="{'status-full' if t['booked'] >= t['max_seats'] else 'status-available'}">
                    {'已满员' if t['booked'] >= t['max_seats'] else '进行中'}
                </span>
            </td>
            <td style="padding: 12px;">
                <a href="/book/{t['id']}" class="btn" style="padding: 6px 12px; font-size: 0.8rem; margin-right: 5px;">查看</a>
                <button class="btn" style="padding: 6px 12px; font-size: 0.8rem; background: #e74c3c;" onclick="deleteTour({t['id']})">删除</button>
            </td>
        </tr>
        '''
    
    # 生成预订详情表格（管理员能看到所有信息）
    bookings_table_html = ''
    for b in bookings_db:
        # 找到对应的团期信息
        tour_info = next((t for t in tours_db if t['id'] == b['tour_id']), {'destination': '未知'})
        bookings_table_html += f'''
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px;">{b['code']}</td>
            <td style="padding: 10px;">{b['name']}</td>
            <td style="padding: 10px;">{b['phone']}</td>
            <td style="padding: 10px;">{tour_info['destination']}</td>
            <td style="padding: 10px;">{b.get('seat_numbers', ['无'])}</td>
            <td style="padding: 10px;">{b['created_at']}</td>
        </tr>
        '''
    # ============== 核心修改3结束 ==============
    
    body_content = f'''
    <div style="max-width: 1200px; margin: 0 auto;">
        <h1 style="color: white;"><i class="fas fa-cog"></i> 管理后台（管理员）</h1>
        <p style="color: rgba(255,255,255,0.8); margin-bottom: 30px;">所有数据总览与管理 | 客人无法看到此页面</p>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div class="card" style="text-align: center;">
                <h3>总班次数</h3>
                <p style="font-size: 2rem; color: #6a11cb;">{len(tours_db)}</p>
            </div>
            <div class="card" style="text-align: center;">
                <h3>总预订数</h3>
                <p style="font-size: 2rem; color: #00b09b;">{len(bookings_db)}</p>
            </div>
            <div class="card" style="text-align: center;">
                <h3>已满员班次</h3>
                <p style="font-size: 2rem; color: #ff6b6b;">{len([t for t in tours_db if t['booked'] >= t['max_seats']])}</p>
            </div>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-bus"></i> 班次管理</h2>
            <div style="overflow-x: auto; margin-top: 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">ID</th>
                            <th style="padding: 12px; text-align: left;">目的地</th>
                            <th style="padding: 12px; text-align: left;">出发时间</th>
                            <th style="padding: 12px; text-align: left;">总座位</th>
                            <th style="padding: 12px; text-align: left;">已预订</th>
                            <th style="padding: 12px; text-align: left;">状态</th>
                            <th style="padding: 12px; text-align: left;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tours_table_html if tours_table_html else '<tr><td colspan="7" style="text-align:center;padding:20px;color:#666;">暂无班次</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- ============== 核心修改4：创建班次时可自定义座位数量 ============== -->
        <div class="card">
            <h2><i class="fas fa-plus-circle"></i> 创建新班次</h2>
            <form onsubmit="createTour(event)" style="margin-top: 20px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 600;">出发日期</label>
                        <input type="date" id="newTourDate" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px;">
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 8px; font-weight: 600;">出发时间</label>
                        <input type="time" id="newTourTime" required value="08:00" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px;">
                    </div>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">目的地</label>
                    <input type="text" id="newTourDest" required placeholder="例如：北京故宫" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px;">
                </div>
                <!-- 新增：自定义座位数输入框 -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">总座位数</label>
                    <input type="number" id="newTourSeats" required min="1" max="50" value="6" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px;">
                    <small style="color: #666;">可设置1-50之间的数字，例如：大巴车可设40座，商务车可设6座</small>
                </div>
                <button type="submit" class="btn" style="width: 100%;">
                    <i class="fas fa-plus"></i> 创建新班次
                </button>
            </form>
        </div>
        <!-- ============== 核心修改4结束 ============== -->
        
        <div class="card">
            <h2><i class="fas fa-list-alt"></i> 所有预订详情（仅管理员可见）</h2>
            <p style="color: #666; margin-bottom: 15px;">这里显示所有客户的完整预订信息，客人页面看不到这些。</p>
            <div style="overflow-x: auto; margin-top: 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px; text-align: left;">预订码</th>
                            <th style="padding: 10px; text-align: left;">姓名</th>
                            <th style="padding: 10px; text-align: left;">手机</th>
                            <th style="padding: 10px; text-align: left;">班次</th>
                            <th style="padding: 10px; text-align: left;">座位号</th>
                            <th style="padding: 10px; text-align: left;">预订时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        {bookings_table_html if bookings_table_html else '<tr><td colspan="6" style="text-align:center;padding:20px;color:#666;">暂无预订记录</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
    // 设置默认日期为明天
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById('newTourDate').value = tomorrow.toISOString().split('T')[0];
    
    async function createTour(event) {{
        event.preventDefault();
        const date = document.getElementById('newTourDate').value;
        const time = document.getElementById('newTourTime').value;
        const dest = document.getElementById('newTourDest').value;
        const seats = parseInt(document.getElementById('newTourSeats').value); // 获取自定义座位数
        
        const response = await fetch('/api/create_tour', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ date: date, time: time, destination: dest, max_seats: seats }}) // 传递自定义座位数
        }});
        
        const result = await response.json();
        if (result.success) {{
            alert('创建成功！页面将刷新...');
            location.reload();
        }} else {{
            alert('创建失败: ' + result.message);
        }}
    }}
    
    async function deleteTour(tourId) {{
        if (!confirm('确定要删除这个班次吗？相关的所有预订也将被删除！')) return;
        
        const response = await fetch('/api/delete_tour', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ tour_id: tourId }})
        }});
        
        const result = await response.json();
        if (result.success) {{
            alert('删除成功！页面将刷新...');
            location.reload();
        }} else {{
            alert('删除失败: ' + result.message);
        }}
    }}
    </script>
    '''
    return get_html_template('管理后台', body_content)

# ---------- API 接口（处理数据）----------
@app.route('/api/book', methods=['POST'])
def api_book():
    """处理预订请求（已修改为支持选座）"""
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        name = data.get('name')
        phone = data.get('phone')
        seat_numbers = data.get('seat_numbers', [])  # 改为接收座位号列表
        
        if not seat_numbers:
            return jsonify({'success': False, 'message': '请至少选择一个座位'})
        
        # 从文件加载最新数据
        app_data = load_data()
        tours_db = app_data['tours']
        bookings_db = app_data['bookings']
        
        # 找到对应团期
        tour = next((t for t in tours_db if t['id'] == tour_id), None)
        if not tour:
            return jsonify({'success': False, 'message': '班次不存在'})
        
        # 检查每个座位是否可用
        existing_bookings = [b for b in bookings_db if b['tour_id'] == tour_id]
        all_taken_seats = []
        for b in existing_bookings:
            seats = b.get('seat_numbers', [])
            if isinstance(seats, list):
                all_taken_seats.extend(seats)
            elif seats:
                all_taken_seats.append(seats)
        
        for seat in seat_numbers:
            if seat in all_taken_seats:
                return jsonify({'success': False, 'message': f'{seat}号座位已被预订'})
        
        # 检查是否超过剩余座位数
        available = tour['max_seats'] - tour['booked']
        if len(seat_numbers) > available:
            return jsonify({'success': False, 'message': f'剩余车位不足，仅剩{available}个'})
        
        # 生成预订码
        booking_code = generate_booking_code()
        
        # 保存预订
        booking = {
            'code': booking_code,
            'name': name,
            'phone': phone,
            'seat_numbers': seat_numbers,  # 保存座位号数组
            'tour_id': tour_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        bookings_db.append(booking)
        
        # 更新团期预订人数（增加已选座位数量）
        tour['booked'] += len(seat_numbers)
        
        # ============== 核心修改1：保存数据到文件 ==============
        app_data['tours'] = tours_db
        app_data['bookings'] = bookings_db
        save_data(app_data)
        # ============== 核心修改1结束 ==============
        
        return jsonify({
            'success': True,
            'message': '预订成功',
            'booking_code': booking_code,
            'data': booking
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/create_tour', methods=['POST'])
def api_create_tour():
    """创建新团期（已修改为支持自定义座位数）"""
    try:
        data = request.get_json()
        
        # 从文件加载最新数据
        app_data = load_data()
        tours_db = app_data['tours']
        
        # 生成新ID
        new_id = max([t['id'] for t in tours_db], default=0) + 1
        
        # 获取自定义座位数，默认为6
        max_seats = int(data.get('max_seats', 6))
        if max_seats < 1:
            max_seats = 6
        
        new_tour = {
            'id': new_id,
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'max_seats': max_seats,  # 使用自定义座位数
            'booked': 0
        }
        tours_db.append(new_tour)
        
        # ============== 核心修改1：保存数据到文件 ==============
        app_data['tours'] = tours_db
        save_data(app_data)
        # ============== 核心修改1结束 ==============
        
        return jsonify({'success': True, 'tour_id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_tour', methods=['POST'])
def api_delete_tour():
    """删除班次（管理员功能）"""
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        
        # 从文件加载最新数据
        app_data = load_data()
        tours_db = app_data['tours']
        bookings_db = app_data['bookings']
        
        # 删除班次
        tours_db = [t for t in tours_db if t['id'] != tour_id]
        
        # 删除与该班次相关的所有预订
        bookings_db = [b for b in bookings_db if b['tour_id'] != tour_id]
        
        # ============== 核心修改1：保存数据到文件 ==============
        app_data['tours'] = tours_db
        app_data['bookings'] = bookings_db
        save_data(app_data)
        # ============== 核心修改1结束 ==============
        
        return jsonify({'success': True, 'message': '班次已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/search_booking', methods=['GET'])
def api_search_booking():
    """查询预订"""
    query = request.args.get('q', '').lower()
    
    # 从文件加载最新数据
    app_data = load_data()
    bookings_db = app_data['bookings']
    
    results = []
    for booking in bookings_db:
        if (query in booking['code'].lower() or 
            query in booking['phone'] or
            query in booking['name'].lower()):
            results.append(booking)
    
    return jsonify({'success': True, 'data': results})

# ---------- Vercel 专用启动方式 ----------
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
