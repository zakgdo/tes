from flask import Flask, request, jsonify, session, redirect, render_template
import json
import random
import string
from datetime import datetime, timedelta
import os
import sqlite3
from contextlib import closing

app = Flask(__name__)
# 使用固定密钥而不是随机密钥（重要！）
app.secret_key = "your-fixed-secret-key-for-vercel-123456"

# 数据库文件路径
DB_FILE = '/tmp/booking_data.db'

# 初始化数据库（确保表存在）
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
            print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")

# 在应用启动时初始化数据库
init_database()

@app.before_request
def before_request():
    """每次请求前确保数据库存在"""
    try:
        # 简单检查数据库连接
        with closing(sqlite3.connect(DB_FILE)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            if not tables:
                init_database()
    except:
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

# 数据库操作辅助函数
def get_db_connection():
    return sqlite3.connect(DB_FILE)

def load_tours():
    """加载所有班次"""
    try:
        with closing(get_db_connection()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tours ORDER BY date, time')
            tours = cursor.fetchall()
            return [dict(tour) for tour in tours]
    except Exception as e:
        print(f"❌ 加载班次失败: {e}")
        # 如果出错，尝试重新初始化数据库
        try:
            init_database()
        except:
            pass
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
        print(f"❌ 加载预订失败: {e}")
        return []

def save_tour(tour):
    """保存班次"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tours (date, time, destination, vehicle_model, max_seats, booked)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (tour['date'], tour['time'], tour['destination'], 
                  tour.get('vehicle_model', '未指定'), tour['max_seats'], tour.get('booked', 0)))
            tour['id'] = cursor.lastrowid
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ 保存班次失败: {e}")
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
            
            cursor.execute('''
                UPDATE tours SET booked = booked + ? WHERE id = ?
            ''', (len(booking['seat_numbers']), booking['tour_id']))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ 保存预订失败: {e}")
        return False

def delete_tour(tour_id):
    """删除班次"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tours WHERE id = ?', (tour_id,))
            cursor.execute('DELETE FROM bookings WHERE tour_id = ?', (tour_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ 删除班次失败: {e}")
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

# 路由部分
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
            session.permanent = True  # 使session持久
            print("✅ 登录成功，session设置:", session.get('is_admin'))
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
    print("📋 访问/admin，session状态:", session.get('is_admin'))
    
    # 检查是否是管理员
    if not session.get('is_admin'):
        print("⛔ 未登录，重定向到登录页")
        return redirect('/admin/login')
    
    print("✅ 已登录，加载数据")
    tours = load_tours()
    bookings = load_bookings()
    
    print(f"📊 加载了 {len(tours)} 个班次，{len(bookings)} 个预订")
    
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
        
        tours = load_tours()
        tour = next((t for t in tours if t['id'] == tour_id), None)
        
        if not tour:
            return jsonify({'success': False, 'message': '班次不存在'})
        
        if is_tour_departed(tour['date'], tour['time']):
            return jsonify({'success': False, 'message': '该班次已发车，不能预订'})
        
        bookings = load_bookings()
        all_taken_seats = []
        for b in bookings:
            if b['tour_id'] == tour_id:
                seats = json.loads(b.get('seat_numbers', '[]'))
                all_taken_seats.extend(seats)
        
        for seat in seat_numbers:
            if seat in all_taken_seats:
                return jsonify({'success': False, 'message': f'{seat}号座位已被预订'})
        
        available = tour['max_seats'] - tour['booked']
        if len(seat_numbers) > available:
            return jsonify({'success': False, 'message': f'剩余车位不足，仅剩{available}个'})
        
        booking_code = 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        booking = {
            'code': booking_code,
            'name': name,
            'phone': phone,
            'seat_numbers': seat_numbers,
            'tour_id': tour_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
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
        
        max_seats = int(data.get('max_seats', 6))
        if max_seats < 1:
            max_seats = 6
        
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
        
        print(f"📝 创建新班次: {new_tour}")
        
        if save_tour(new_tour):
            print(f"✅ 班次创建成功，ID: {new_tour.get('id')}")
            return jsonify({'success': True, 'tour_id': new_tour.get('id')})
        else:
            print("❌ 班次创建失败")
            return jsonify({'success': False, 'message': '保存班次失败'})
            
    except Exception as e:
        print(f"❌ 创建班次异常: {e}")
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
            
            booking_copy = booking.copy()
            booking_copy['seat_numbers'] = json.loads(booking.get('seat_numbers', '[]'))
            results.append(booking_copy)
    
    return jsonify({'success': True, 'data': results})

# 添加一个测试路由，查看数据库状态
@app.route('/debug/db-status')
def debug_db_status():
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            
            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # 检查数据
            cursor.execute("SELECT COUNT(*) FROM tours")
            tour_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bookings")
            booking_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'tables': [table[0] for table in tables],
                'tour_count': tour_count,
                'booking_count': booking_count,
                'db_file': DB_FILE,
                'db_exists': os.path.exists(DB_FILE)
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Vercel专用
application = app

if __name__ == '__main__':
    print("🚀 启动订车助手...")
    app.run(debug=True, host='0.0.0.0', port=3000)
