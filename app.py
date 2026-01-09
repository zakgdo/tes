from flask import Flask, request, jsonify, session, redirect, render_template
import json
import random
import string
from datetime import datetime, timedelta
import os
import sqlite3
from contextlib import closing

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_FILE = '/tmp/booking_data.db'

# 初始化数据库
def init_database():
    try:
        with closing(sqlite3.connect(DB_FILE)) as conn:
            cursor = conn.cursor()
            
            # 创建班次表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tours (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    vehicle_model TEXT DEFAULT '未指定',
                    max_seats INTEGER DEFAULT 6,
                    booked INTEGER DEFAULT 0
                )
            ''')
            
            # 创建预订表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    seat_numbers TEXT NOT NULL,
                    tour_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            print("数据库初始化成功")
    except Exception as e:
        print(f"数据库初始化失败: {e}")

# 初始化数据库（每次启动时执行）
init_database()

@app.context_processor
def utility_processor():
    def check_departed(date_str, time_str):
        try:
            tour_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            return tour_datetime < datetime.now()
        except:
            return False
    
    def calculate_available(tour):
        return tour['max_seats'] - tour['booked']
    
    return dict(
        is_tour_departed=check_departed,
        calculate_available=calculate_available,
        now=datetime.now
    )

def get_db_connection():
    return sqlite3.connect(DB_FILE)

def load_tours():
    """加载所有班次"""
    try:
        with closing(get_db_connection()) as conn:
            conn.row_factory = sqlite3.Row  # 使返回结果为字典格式
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tours ORDER BY date, time')
            tours = cursor.fetchall()
            return [dict(tour) for tour in tours]
    except Exception as e:
        print(f"加载班次失败: {e}")
        return []

def load_bookings():
    """加载所有预订"""
    try:
        with closing(get_db_connection()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bookings')
            bookings = cursor.fetchall()
            return [dict(booking) for booking in bookings]
    except Exception as e:
        print(f"加载预订失败: {e}")
        return []

def save_tour(tour):
    """保存班次"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            if 'id' in tour:
                # 更新现有班次
                cursor.execute('''
                    UPDATE tours SET 
                    date=?, time=?, destination=?, vehicle_model=?, max_seats=?, booked=?
                    WHERE id=?
                ''', (tour['date'], tour['time'], tour['destination'], 
                      tour.get('vehicle_model', '未指定'), tour['max_seats'], 
                      tour.get('booked', 0), tour['id']))
            else:
                # 插入新班次
                cursor.execute('''
                    INSERT INTO tours (date, time, destination, vehicle_model, max_seats, booked)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (tour['date'], tour['time'], tour['destination'], 
                      tour.get('vehicle_model', '未指定'), tour['max_seats'], tour.get('booked', 0)))
                tour['id'] = cursor.lastrowid
            conn.commit()
            return True
    except Exception as e:
        print(f"保存班次失败: {e}")
        return False

def save_booking(booking):
    """保存预订"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bookings (code, name, phone, seat_numbers, tour_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (booking['code'], booking['name'], booking['phone'], 
                  json.dumps(booking['seat_numbers']), booking['tour_id'], booking['created_at']))
            
            # 更新班次的预订人数
            cursor.execute('''
                UPDATE tours SET booked = booked + ? WHERE id = ?
            ''', (len(booking['seat_numbers']), booking['tour_id']))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"保存预订失败: {e}")
        return False

def delete_tour(tour_id):
    """删除班次"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            # 删除班次
            cursor.execute('DELETE FROM tours WHERE id = ?', (tour_id,))
            # 删除相关预订
            cursor.execute('DELETE FROM bookings WHERE tour_id = ?', (tour_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"删除班次失败: {e}")
        return False

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
        naive_tour_datetime = datetime.strptime(tour_datetime_str, '%Y-%m-%d %H:%M')
        
        if naive_tour_datetime < datetime.now():
            time_passed = datetime.now() - naive_tour_datetime
            return time_passed.days <= 7
        
        return True
    except Exception as e:
        print(f"检查班次保留状态出错: {e}, date={tour_date}, time={tour_time}")
        return True

@app.route('/')
def home():
    tours = load_tours()
    
    # 过滤有效班次
    valid_tours = []
    expired_tours = []
    for tour in tours:
        if should_keep_tour(tour['date'], tour['time']):
            valid_tours.append(tour)
        else:
            expired_tours.append(tour)
    
    # 删除过期班次
    for tour in expired_tours:
        delete_tour(tour['id'])
    
    # 计算统计数据
    valid_count = len(valid_tours)
    total_bookings = sum(t.get('booked', 0) for t in valid_tours)
    departed_count = sum(1 for t in valid_tours if is_tour_departed(t["date"], t["time"]))
    
    return render_template('index.html',
                         valid_tours=valid_tours,
                         valid_count=valid_count,
                         total_bookings=total_bookings,
                         departed_count=departed_count)

@app.route('/tours')
def tours_page():
    tours = load_tours()
    valid_tours = [t for t in tours if should_keep_tour(t['date'], t['time'])]
    return render_template('tours.html', valid_tours=valid_tours)

@app.route('/bookings')
def bookings_page():
    tours = load_tours()
    bookings = load_bookings()
    valid_tours = [t for t in tours if should_keep_tour(t['date'], t['time'])]
    tour_booking_counts = []
    total_bookings = 0
    for tour in valid_tours:
        tour_bookings = [b for b in bookings if b['tour_id'] == tour['id']]
        booking_count = len(tour_bookings)
        total_bookings += booking_count
        if booking_count > 0:
            seat_count = 0
            for b in tour_bookings:
                seats = json.loads(b.get('seat_numbers', '[]'))
                seat_count += len(seats)
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
    tours = load_tours()
    valid_tours = [t for t in tours if should_keep_tour(t['date'], t['time'])]
    
    departed_tours = []
    for tour in valid_tours:
        if is_tour_departed(tour['date'], tour['time']):
            tour_datetime_str = f"{tour['date']} {tour['time']}"
            try:
                tour_datetime = datetime.strptime(tour_datetime_str, '%Y-%m-%d %H:%M')
                time_passed = datetime.now() - tour_datetime
                days_passed = time_passed.days
                hours_passed = time_passed.seconds // 3600
            except:
                days_passed = 0
                hours_passed = 0
            
            tour_with_time = tour.copy()
            tour_with_time['days_passed'] = days_passed
            tour_with_time['hours_passed'] = hours_passed
            departed_tours.append(tour_with_time)
    
    return render_template('departed.html', departed_tours=departed_tours)

@app.route('/book/<int:tour_id>')
def book_page(tour_id):
    tours = load_tours()
    tour = next((t for t in tours if t['id'] == tour_id), None)
    
    if not tour:
        return render_template('error.html', message='班次不存在')
    
    if is_tour_departed(tour['date'], tour['time']):
        return render_template('error.html', message='该班次已发车，不能预订')
    bookings = load_bookings()
    taken_seats = []
    for b in bookings:
        if b['tour_id'] == tour_id:
            seats = json.loads(b.get('seat_numbers', '[]'))
            taken_seats.extend(seats)
    
    return render_template('book.html', tour=tour, taken_seats=taken_seats)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    ADMIN_PASSWORD = "050522"
    
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
def admin_page():
    if not session.get('is_admin'):
        return redirect('/admin/login')
    
    tours = load_tours()
    bookings = load_bookings()
    
    total_tours = len(tours)
    total_bookings_count = len(bookings)
    departed_count = sum(1 for tour in tours if is_tour_departed(tour['date'], tour['time']))
    full_count = sum(1 for tour in tours if tour['booked'] >= tour['max_seats'])
    
    return render_template('admin.html',
                         tours_db=tours,
                         bookings_db=bookings,
                         total_tours=total_tours,
                         total_bookings_count=total_bookings_count,
                         departed_count=departed_count,
                         full_count=full_count)

@app.route('/api/book', methods=['POST'])
def api_book():
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        name = data.get('name')
        phone = data.get('phone')
        seat_numbers = data.get('seat_numbers', [])
        
        if not seat_numbers:
            return jsonify({'success': False, 'message': '请至少选择一个座位'})
        
        # 加载数据
        tours = load_tours()
        tour = next((t for t in tours if t['id'] == tour_id), None)
        
        if not tour:
            return jsonify({'success': False, 'message': '班次不存在'})
        
        # 检查班次是否已发车
        if is_tour_departed(tour['date'], tour['time']):
            return jsonify({'success': False, 'message': '该班次已发车，不能预订'})
        
        # 检查每个座位是否可用
        bookings = load_bookings()
        all_taken_seats = []
        for b in bookings:
            if b['tour_id'] == tour_id:
                seats = json.loads(b.get('seat_numbers', '[]'))
                all_taken_seats.extend(seats)
        
        for seat in seat_numbers:
            if seat in all_taken_seats:
                return jsonify({'success': False, 'message': f'{seat}号座位已被预订'})
        
        # 检查是否超过剩余座位数
        available = tour['max_seats'] - tour['booked']
        if len(seat_numbers) > available:
            return jsonify({'success': False, 'message': f'剩余车位不足，仅剩{available}个'})
        
        # 生成预订码
        booking_code = 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # 创建预订对象
        booking = {
            'code': booking_code,
            'name': name,
            'phone': phone,
            'seat_numbers': seat_numbers,
            'tour_id': tour_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存预订
        if save_booking(booking):
            return jsonify({
                'success': True,
                'message': '预订成功',
                'booking_code': booking_code
            })
        else:
            return jsonify({'success': False, 'message': '保存预订失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/create_tour', methods=['POST'])
def api_create_tour():
    try:
        data = request.get_json()
        
        # 获取自定义座位数，默认为6
        max_seats = int(data.get('max_seats', 6))
        if max_seats < 1:
            max_seats = 6
        
        # 获取车辆型号，默认为空字符串
        vehicle_model = data.get('vehicle_model', '').strip()
        if not vehicle_model:
            vehicle_model = '未指定'
        
        new_tour = {
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'vehicle_model': vehicle_model,
            'max_seats': max_seats,
            'booked': 0
        }
        
        # 保存班次
        if save_tour(new_tour):
            return jsonify({'success': True, 'tour_id': new_tour.get('id')})
        else:
            return jsonify({'success': False, 'message': '保存班次失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_tour', methods=['POST'])
def api_delete_tour():
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        
        if delete_tour(tour_id):
            return jsonify({'success': True, 'message': '班次已删除'})
        else:
            return jsonify({'success': False, 'message': '删除班次失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_tour_bookings', methods=['GET'])
def api_get_tour_bookings():
    try:
        tour_id = int(request.args.get('tour_id'))
        
        bookings = load_bookings()
        tour_bookings = [b for b in bookings if b['tour_id'] == tour_id]
        
        for booking in tour_bookings:
            booking['seat_numbers'] = json.loads(booking.get('seat_numbers', '[]'))
        
        return jsonify({'success': True, 'data': tour_bookings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/search_booking', methods=['GET'])
def api_search_booking():
    query = request.args.get('q', '').lower()
    
    bookings = load_bookings()
    results = []
    
    for booking in bookings:
        if (query in booking['code'].lower() or 
            query in booking['phone'] or
            query in booking['name'].lower()):
            
            # 解析座位号
            booking_copy = booking.copy()
            booking_copy['seat_numbers'] = json.loads(booking.get('seat_numbers', '[]'))
            results.append(booking_copy)
    
    return jsonify({'success': True, 'data': results})

# Vercel专用
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
