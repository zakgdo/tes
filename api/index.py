from flask import Flask, request, jsonify
import json
import random
import string
from datetime import datetime
from urllib.parse import parse_qs

app = Flask(__name__)

# ---------- 内存数据库（简单演示用）----------
tours_db = [
    {"id": 1, "date": "2024-12-25", "time": "08:00", "destination": "北京故宫一日游", "max_seats": 6, "booked": 2},
    {"id": 2, "date": "2024-12-26", "time": "09:00", "destination": "八达岭长城半日游", "max_seats": 6, "booked": 4},
    {"id": 3, "date": "2024-12-27", "time": "10:00", "destination": "颐和园休闲游", "max_seats": 6, "booked": 0}
]
bookings_db = []

# ---------- 工具函数 ----------
def generate_booking_code():
    return 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_html_template(title, body_content):
    """生成完整的HTML页面框架"""
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
    </style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="logo"><i class="fas fa-bus"></i> 车位预订系统</a>
        <div class="nav-links">
            <a href="/"><i class="fas fa-home"></i> 首页</a>
            <a href="/admin"><i class="fas fa-cog"></i> 管理</a>
        </div>
    </nav>
    <div class="container">
        {body_content}
    </div>
    <footer style="text-align: center; color: white; margin-top: 50px; padding: 20px; opacity: 0.8;">
        <p>© 2024 车位预订系统 | 每满6人自动发车 | 适配所有设备</p>
        <p style="font-size: 0.9rem; margin-top: 10px;">当前运行于 <strong>Vercel</strong> 云平台</p>
    </footer>
    <script>
        // 全局工具函数
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
    """系统首页"""
    # 生成团期列表的HTML
    tours_html = ''
    for tour in tours_db:
        available = tour['max_seats'] - tour['booked']
        percent = int((tour['booked'] / tour['max_seats']) * 100)
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
                {'<button class="btn" onclick="location.href=\'/book/' + str(tour['id']) + '\'"><i class="fas fa-ticket-alt"></i> 立即预订</button>' if available > 0 else '<button class="btn" style="background:#6c757d;" disabled><i class="fas fa-ban"></i> 已满员</button>'}
            </div>
        </div>
        '''
    
    body_content = f'''
    <h1 style="color: white; text-align: center; margin-bottom: 30px;">🚌 在线车位预订</h1>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px;">
        <div class="card" style="text-align: center; background: rgba(255,255,255,0.95);">
            <h3><i class="fas fa-calendar-day"></i> 进行中团期</h3>
            <p style="font-size: 2.5rem; color: #6a11cb; margin: 10px 0;">{len(tours_db)}</p>
        </div>
        <div class="card" style="text-align: center; background: rgba(255,255,255,0.95);">
            <h3><i class="fas fa-user-check"></i> 总预订人数</h3>
            <p style="font-size: 2.5rem; color: #00b09b; margin: 10px 0;">{sum(t['booked'] for t in tours_db)}</p>
        </div>
        <div class="card" style="text-align: center; background: rgba(255,255,255,0.95);">
            <h3><i class="fas fa-car-side"></i> 即将发车</h3>
            <p style="font-size: 2.5rem; color: #ff6b6b; margin: 10px 0;">{len([t for t in tours_db if t['booked'] == t['max_seats']])}</p>
        </div>
    </div>
    <h2 style="color: white; margin-bottom: 20px;">可预订团期</h2>
    {tours_html if tours_html else '<div class="card"><p style="text-align:center;color:#666;">暂无团期，请稍后查看。</p></div>'}
    <div class="card">
        <h3><i class="fas fa-info-circle"></i> 使用说明</h3>
        <ul style="margin-left: 20px; margin-top: 15px; color: #555;">
            <li>每个团期满 <strong>6人自动发车</strong>，系统实时更新。</li>
            <li>点击"立即预订"填写信息，成功后获得唯一预订码。</li>
            <li>可在"管理"页面查看所有报名情况。</li>
            <li>本系统已适配手机、平板和电脑访问。</li>
        </ul>
    </div>
    '''
    return get_html_template('首页', body_content)

@app.route('/book/<int:tour_id>')
def book_page(tour_id):
    """预订页面"""
    tour = next((t for t in tours_db if t['id'] == tour_id), None)
    if not tour:
        return get_html_template('错误', '<div class="card"><h2>团期不存在</h2></div>')
    
    available = tour['max_seats'] - tour['booked']
    
    body_content = f'''
    <div style="max-width: 800px; margin: 0 auto;">
        <a href="/" class="btn" style="background: #6c757d; margin-bottom: 20px;"><i class="fas fa-arrow-left"></i> 返回首页</a>
        <div class="card">
            <h1><i class="fas fa-ticket-alt"></i> 预订 {tour['destination']}</h1>
            <p style="color: #666; margin: 15px 0;"><i class="far fa-calendar"></i> {tour['date']} {tour['time']} 出发</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px;">
                <div>
                    <h3><i class="fas fa-edit"></i> 填写信息</h3>
                    <form id="bookingForm" onsubmit="submitBooking(event, {tour_id})" style="margin-top: 20px;">
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600;">姓名 *</label>
                            <input type="text" id="customerName" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem;">
                        </div>
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600;">手机号 *</label>
                            <input type="tel" id="customerPhone" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem;" pattern="[0-9]{{11}}">
                        </div>
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600;">预订车位数 (最多{min(3, available)}个) *</label>
                            <select id="seats" required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem;">
                                {' '.join([f'<option value="{i}">{i}个车位</option>' for i in range(1, min(3, available)+1)])}
                            </select>
                        </div>
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 25px 0;">
                            <p><i class="fas fa-info-circle"></i> 剩余车位: <strong style="color:#00b09b;">{available}</strong> 个</p>
                            {'<p style="color:#e74c3c;"><i class="fas fa-exclamation-triangle"></i> 车位紧张，请尽快预订！</p>' if available < 3 else ''}
                        </div>
                        <button type="submit" class="btn" style="width: 100%; padding: 15px; font-size: 1.1rem;">
                            <i class="fas fa-check-circle"></i> 提交预订
                        </button>
                    </form>
                </div>
                
                <div>
                    <h3><i class="fas fa-list-check"></i> 团期详情</h3>
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
                            <span>已报名:</span><strong>{tour['booked']} 人</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                            <span>状态:</span>
                            <span class="{'status-full' if available == 0 else 'status-available'}">
                                {'已满员' if available == 0 else '正常预订中'}
                            </span>
                        </div>
                    </div>
                    
                    <h3 style="margin-top: 30px;"><i class="fas fa-users"></i> 报名进度</h3>
                    <div class="progress-bar" style="margin: 15px 0;">
                        <div class="progress-fill" style="width: {int((tour['booked']/tour['max_seats'])*100)}%"></div>
                    </div>
                    <p style="text-align: center; color: #666;">还需 {tour['max_seats'] - tour['booked']} 人即可发车</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    async function submitBooking(event, tourId) {{
        event.preventDefault();
        const name = document.getElementById('customerName').value;
        const phone = document.getElementById('customerPhone').value;
        const seats = document.getElementById('seats').value;
        
        const btn = event.target.querySelector('button[type="submit"]');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';
        btn.disabled = true;
        
        try {{
            const response = await fetch('/api/book', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ tour_id: tourId, name: name, phone: phone, seats: parseInt(seats) }})
            }});
            const result = await response.json();
            
            if (result.success) {{
                // 显示成功信息
                document.getElementById('bookingForm').innerHTML = `
                    <div style="text-align: center; padding: 40px 20px;">
                        <i class="fas fa-check-circle" style="font-size: 4rem; color: #00b09b;"></i>
                        <h2>预订成功！</h2>
                        <p>您的预订已确认，请保存好预订码</p>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0; font-family: monospace;">
                            <p style="color: #666;">预订码</p>
                            <h1 style="color: #e74c3c; letter-spacing: 3px;">${{result.booking_code}}</h1>
                        </div>
                        <p><button class="btn" onclick="copyToCliptext('${{result.booking_code}}')"><i class="fas fa-copy"></i> 复制预订码</button></p>
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
    """管理后台页面"""
    body_content = f'''
    <div style="max-width: 1000px; margin: 0 auto;">
        <h1 style="color: white;"><i class="fas fa-cog"></i> 管理后台</h1>
        <p style="color: rgba(255,255,255,0.8); margin-bottom: 30px;">实时监控所有团期和预订情况</p>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div class="card" style="text-align: center;">
                <h3>总团期数</h3>
                <p style="font-size: 2rem; color: #6a11cb;">{len(tours_db)}</p>
            </div>
            <div class="card" style="text-align: center;">
                <h3>总预订数</h3>
                <p style="font-size: 2rem; color: #00b09b;">{len(bookings_db)}</p>
            </div>
            <div class="card" style="text-align: center;">
                <h3>已满员团期</h3>
                <p style="font-size: 2rem; color: #ff6b6b;">{len([t for t in tours_db if t['booked'] >= t['max_seats']])}</p>
            </div>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-bus"></i> 团期管理</h2>
            <div style="overflow-x: auto; margin-top: 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 12px; text-align: left;">ID</th>
                            <th style="padding: 12px; text-align: left;">目的地</th>
                            <th style="padding: 12px; text-align: left;">时间</th>
                            <th style="padding: 12px; text-align: left;">座位情况</th>
                            <th style="padding: 12px; text-align: left;">状态</th>
                            <th style="padding: 12px; text-align: left;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([f'''
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 12px;">{t['id']}</td>
                            <td style="padding: 12px;"><strong>{t['destination']}</strong></td>
                            <td style="padding: 12px;">{t['date']} {t['time']}</td>
                            <td style="padding: 12px;">{t['booked']}/{t['max_seats']}</td>
                            <td style="padding: 12px;">
                                <span class="{'status-full' if t['booked'] >= t['max_seats'] else 'status-available'}">
                                    {'已满员' if t['booked'] >= t['max_seats'] else '进行中'}
                                </span>
                            </td>
                            <td style="padding: 12px;">
                                <a href="/book/{t['id']}" class="btn" style="padding: 8px 15px; font-size: 0.9rem;">查看</a>
                            </td>
                        </tr>
                        ''' for t in tours_db])}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-plus-circle"></i> 创建新团期</h2>
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
                <button type="submit" class="btn" style="width: 100%;">
                    <i class="fas fa-plus"></i> 创建新团期
                </button>
            </form>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-search"></i> 预订查询</h2>
            <div style="margin-top: 20px;">
                <input type="text" id="searchInput" placeholder="输入预订码或手机号后4位" style="width: 70%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; margin-right: 10px;">
                <button class="btn" onclick="searchBooking()">查询</button>
            </div>
            <div id="searchResult" style="margin-top: 20px;"></div>
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
        
        const response = await fetch('/api/create_tour', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ date: date, time: time, destination: dest, max_seats: 6 }})
        }});
        
        const result = await response.json();
        if (result.success) {{
            alert('创建成功！页面将刷新...');
            location.reload();
        }} else {{
            alert('创建失败: ' + result.message);
        }}
    }}
    
    async function searchBooking() {{
        const query = document.getElementById('searchInput').value.trim();
        if (!query) return;
        
        const response = await fetch('/api/search_booking?q=' + encodeURIComponent(query));
        const result = await response.json();
        const resultDiv = document.getElementById('searchResult');
        
        if (result.success && result.data.length > 0) {{
            resultDiv.innerHTML = `
                <div class="card">
                    <h3>查询结果</h3>
                    ${{result.data.map(b => `
                        <div style="border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-top: 10px;">
                            <p><strong>预订码:</strong> ${{b.code}}</p>
                            <p><strong>姓名:</strong> ${{b.name}}</p>
                            <p><strong>手机:</strong> ${{b.phone}}</p>
                            <p><strong>团期:</strong> 团期#${{b.tour_id}}</p>
                            <p><strong>时间:</strong> ${{b.created_at}}</p>
                        </div>
                    `).join('')}}
                </div>
            `;
        }} else {{
            resultDiv.innerHTML = '<p style="color:#666; text-align:center;">未找到相关预订</p>';
        }}
    }}
    </script>
    '''
    return get_html_template('管理后台', body_content)

# ---------- API 接口（处理数据）----------
@app.route('/api/book', methods=['POST'])
def api_book():
    """处理预订请求"""
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        name = data.get('name')
        phone = data.get('phone')
        seats = int(data.get('seats', 1))
        
        # 找到对应团期
        tour = next((t for t in tours_db if t['id'] == tour_id), None)
        if not tour:
            return jsonify({'success': False, 'message': '团期不存在'})
        
        # 检查座位是否足够
        available = tour['max_seats'] - tour['booked']
        if available < seats:
            return jsonify({'success': False, 'message': f'车位不足，仅剩{available}个'})
        
        # 生成预订码
        booking_code = generate_booking_code()
        
        # 保存预订
        booking = {
            'code': booking_code,
            'name': name,
            'phone': phone,
            'seats': seats,
            'tour_id': tour_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        bookings_db.append(booking)
        
        # 更新团期预订数
        tour['booked'] += seats
        
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
    """创建新团期"""
    try:
        data = request.get_json()
        new_id = max([t['id'] for t in tours_db], default=0) + 1
        
        new_tour = {
            'id': new_id,
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'max_seats': int(data.get('max_seats', 6)),
            'booked': 0
        }
        tours_db.append(new_tour)
        
        return jsonify({'success': True, 'tour_id': new_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/search_booking', methods=['GET'])
def api_search_booking():
    """查询预订"""
    query = request.args.get('q', '').lower()
    results = []
    
    for booking in bookings_db:
        if (query in booking['code'].lower() or 
            query in booking['phone'] or
            query in booking['name'].lower()):
            results.append(booking)
    
    return jsonify({'success': True, 'data': results})

# ---------- Vercel 专用启动方式 ----------
# 这是必须的，Vercel 会调用这个变量
application = app

# 本地开发时运行
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
