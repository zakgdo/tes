from flask import Flask, request, jsonify, session, redirect, render_template
import json
import random
import string
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============== 数据存储 (和原来完全一样) ==============
DATA_FILE = '/tmp/booking_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'tours': [], 'bookings': []}
    return {'tours': [], 'bookings': []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- 工具函数 (和原来完全一样) ----------
def generate_booking_code():
    return 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

ADMIN_PASSWORD = "050522"

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

def is_tour_departed(tour_date, tour_time):
    try:
        tour_datetime_str = f"{tour_date} {tour_time}"
        tour_datetime = datetime.strptime(tour_datetime_str, '%Y-%m-%d %H:%M')
        return tour_datetime < datetime.now()
    except:
        return False

def should_keep_tour(tour_date, tour_time):
    try:
        tour_datetime_str = f"{tour_date} {tour_time}"
        tour_datetime = datetime.strptime(tour_datetime_str, '%Y-%m-%d %H:%M')
        current_time = datetime.now()
        if tour_datetime < current_time:
            time_passed = current_time - tour_datetime
            return time_passed.days <= 7
        return True
    except:
        return False

# ---------- 网站页面路由 ----------
@app.route('/')
def home():
    app_data = load_data()
    tours_db = app_data['tours']
    # 过滤掉超过一周的已发车班次
    valid_tours = []
    expired_tours = []
    for tour in tours_db:
        if should_keep_tour(tour['date'], tour['time']):
            valid_tours.append(tour)
        else:
            expired_tours.append(tour)
    # 删除过期的班次（超过一周）
    if expired_tours:
        app_data['tours'] = valid_tours
        save_data(app_data)
    # 计算统计数据
    valid_count = len(valid_tours)
    total_bookings = sum(t.get('booked', 0) for t in valid_tours)
    departed_count = sum(1 for t in valid_tours if is_tour_departed(t["date"], t["time"]))
    # 渲染首页模板，并传递数据
    return render_template('index.html',
                         valid_tours=valid_tours,
                         valid_count=valid_count,
                         total_bookings=total_bookings,
                         departed_count=departed_count)

@app.route('/tours')
def tours_page():
    app_data = load_data()
    tours_db = app_data['tours']
    valid_tours = [t for t in tours_db if should_keep_tour(t['date'], t['time'])]
    return render_template('tours.html', valid_tours=valid_tours)

@app.route('/bookings')
def bookings_page():
    app_data = load_data()
    tours_db = app_data['tours']
    bookings_db = app_data['bookings']
    valid_tours = [t for t in tours_db if should_keep_tour(t['date'], t['time'])]
    # 统计每个班次的预订人数
    tour_booking_counts = []
    total_bookings = 0
    for tour in valid_tours:
        tour_bookings = [b for b in bookings_db if b['tour_id'] == tour['id']]
        booking_count = len(tour_bookings)
        total_bookings += booking_count
        if booking_count > 0:
            seat_count = 0
            for b in tour_bookings:
                seats = b.get('seat_numbers', [])
                if isinstance(seats, list):
                    seat_count += len(seats)
                elif seats:
                    seat_count += 1
            tour_booking_counts.append({
                'tour': tour,
                'booking_count': booking_count,
                'seat_count': seat_count
            })
    tour_booking_counts.sort(key=lambda x: x['booking_count'], reverse=True)
    return render_template('bookings.html',
                         tour_booking_counts=tour_booking_counts,
                         total_bookings=total_bookings,
                         valid_tours=valid_tours)

@app.route('/departed')
def departed_page():
    app_data = load_data()
    tours_db = app_data['tours']
    valid_tours = [t for t in tours_db if should_keep_tour(t['date'], t['time'])]
    departed_tours = [t for t in valid_tours if is_tour_departed(t['date'], t['time'])]
    return render_template('departed.html', departed_tours=departed_tours)

@app.route('/book/<int:tour_id>')
def book_page(tour_id):
    app_data = load_data()
    tours_db = app_data['tours']
    tour = next((t for t in tours_db if t['id'] == tour_id), None)
    if not tour:
        return render_template('error.html', message='班次不存在')
    if is_tour_departed(tour['date'], tour['time']):
        return render_template('error.html', message='该班次已发车，不能预订')
    bookings_for_tour = [b for b in app_data['bookings'] if b['tour_id'] == tour_id]
    taken_seats = []
    for b in bookings_for_tour:
        seat_nums = b.get('seat_numbers', [])
        if isinstance(seat_nums, list):
            taken_seats.extend(seat_nums)
        elif seat_nums:
            taken_seats.append(seat_nums)
    return render_template('book.html', tour=tour, taken_seats=taken_seats)

# ---------- 管理员页面 ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error='密码错误，请重试！')
    return render_template('admin_login.html', error=None)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/')

@app.route('/admin')
@admin_required
def admin_page():
    app_data = load_data()
    tours_db = app_data['tours']
    bookings_db = app_data['bookings']
    return render_template('admin.html', tours_db=tours_db, bookings_db=bookings_db)

# ---------- API 接口（处理数据）----------
# 注意：以下所有API路由代码需要从你原来的app.py中完整复制过来
# 请找到你原来app.py中以下部分，复制粘贴到这里：
# 1. @app.route('/api/book', methods=['POST'])
# 2. @app.route('/api/create_tour', methods=['POST'])
# 3. @app.route('/api/delete_tour', methods=['POST'])
# 4. @app.route('/api/get_tour_bookings', methods=['GET'])
# 5. @app.route('/api/search_booking', methods=['GET'])
# 这是保持你所有预订、创建班次、删除班次功能正常的关键！

# 示例格式（你需要复制完整代码，这只是个样子）：
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
        
        # 检查班次是否已发车
        if is_tour_departed(tour['date'], tour['time']):
            return jsonify({'success': False, 'message': '该班次已发车，不能预订'})
        
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
    """创建新团期（新增车辆型号）"""
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
        
        # 获取车辆型号，默认为空字符串
        vehicle_model = data.get('vehicle_model', '').strip()
        if not vehicle_model:
            vehicle_model = '未指定'
        
        new_tour = {
            'id': new_id,
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'vehicle_model': vehicle_model,  # 新增车辆型号字段
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

@app.route('/api/get_tour_bookings', methods=['GET'])
def api_get_tour_bookings():
    """获取指定班次的所有预订信息"""
    try:
        tour_id = int(request.args.get('tour_id'))
        
        # 从文件加载最新数据
        app_data = load_data()
        bookings_db = app_data['bookings']
        
        # 过滤出该班次的所有预订
        tour_bookings = [b for b in bookings_db if b['tour_id'] == tour_id]
        
        return jsonify({'success': True, 'data': tour_bookings})
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

#Vercel 专用启动方式
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
