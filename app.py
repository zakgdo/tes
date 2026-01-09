from flask import Flask, request, jsonify, session, redirect, render_template
import json
import random
import string
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "simple-fixed-key-for-booking-system"

# 使用内存存储（在Vercel的无服务器环境中，每次请求都重新加载数据）
# 注意：这不会持久化保存数据，重启后会丢失，但至少能正常工作
class MemoryStorage:
    def __init__(self):
        self.tours = []
        self.bookings = []
        self.next_tour_id = 1
        
    def reset(self):
        # 重置数据，添加一些示例数据用于测试
        self.tours = []
        self.bookings = []
        self.next_tour_id = 1
        
        # 添加一些示例班次
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        after_tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        self.tours = [
            {
                'id': 1,
                'date': tomorrow,
                'time': '08:00',
                'destination': '上海南站',
                'vehicle_model': '大巴',
                'max_seats': 6,
                'booked': 0
            },
            {
                'id': 2,
                'date': tomorrow,
                'time': '14:00',
                'destination': '虹桥机场',
                'vehicle_model': '中巴',
                'max_seats': 4,
                'booked': 0
            },
            {
                'id': 3,
                'date': after_tomorrow,
                'time': '09:30',
                'destination': '浦东机场',
                'vehicle_model': '商务车',
                'max_seats': 3,
                'booked': 0
            }
        ]
        self.next_tour_id = 4
        
    def get_tours(self):
        if not self.tours:
            self.reset()
        return self.tours
        
    def get_bookings(self):
        return self.bookings
        
    def add_tour(self, tour_data):
        tour_id = self.next_tour_id
        self.next_tour_id += 1
        
        tour = {
            'id': tour_id,
            'date': tour_data['date'],
            'time': tour_data['time'],
            'destination': tour_data['destination'],
            'vehicle_model': tour_data.get('vehicle_model', '未指定'),
            'max_seats': tour_data.get('max_seats', 6),
            'booked': 0
        }
        self.tours.append(tour)
        return tour_id
        
    def add_booking(self, booking_data):
        self.bookings.append(booking_data)
        # 更新班次的预订人数
        for tour in self.tours:
            if tour['id'] == booking_data['tour_id']:
                tour['booked'] += len(booking_data['seat_numbers'])
                break
                
    def delete_tour(self, tour_id):
        self.tours = [t for t in self.tours if t['id'] != tour_id]
        self.bookings = [b for b in self.bookings if b['tour_id'] != tour_id]

# 创建全局存储实例
storage = MemoryStorage()

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

# 路由部分 - 保持和原来完全一样
@app.route('/')
def home():
    tours = storage.get_tours()
    
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
        storage.delete_tour(tour['id'])
    
    # 重新获取有效班次
    valid_tours = [t for t in storage.get_tours() if should_keep_tour(t['date'], t['time'])]
    
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
    tours = storage.get_tours()
    valid_tours = [t for t in tours if should_keep_tour(t['date'], t['time'])]
    return render_template('tours.html', valid_tours=valid_tours)

@app.route('/bookings')
def bookings_page():
    tours = storage.get_tours()
    bookings = storage.get_bookings()
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
                seat_count += len(b.get('seat_numbers', []))
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
    tours = storage.get_tours()
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
    tours = storage.get_tours()
    tour = next((t for t in tours if t['id'] == tour_id), None)
    
    if not tour:
        return render_template('error.html', message='班次不存在')
    
    if is_tour_departed(tour['date'], tour['time']):
        return render_template('error.html', message='该班次已发车，不能预订')
    
    # 获取已预订座位
    bookings = storage.get_bookings()
    taken_seats = []
    for b in bookings:
        if b['tour_id'] == tour_id:
            taken_seats.extend(b.get('seat_numbers', []))
    
    return render_template('book.html', tour=tour, taken_seats=taken_seats)

# 简化登录逻辑 - 直接检查密码，不依赖session
ADMIN_PASSWORD = "050522"
admin_logged_in = False

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    global admin_logged_in
    
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            admin_logged_in = True
            return redirect('/admin')
        else:
            return render_template('admin_login.html', error='密码错误，请重试！')
    return render_template('admin_login.html', error=None)

@app.route('/admin/logout')
def admin_logout():
    global admin_logged_in
    admin_logged_in = False
    return redirect('/')

@app.route('/admin')
def admin_page():
    global admin_logged_in
    
    # 直接检查密码参数，简化登录
    password = request.args.get('password')
    if password == ADMIN_PASSWORD:
        admin_logged_in = True
    
    if not admin_logged_in:
        return redirect('/admin/login')
    
    tours = storage.get_tours()
    bookings = storage.get_bookings()
    
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
        
        tours = storage.get_tours()
        tour = next((t for t in tours if t['id'] == tour_id), None)
        
        if not tour:
            return jsonify({'success': False, 'message': '班次不存在'})
        
        if is_tour_departed(tour['date'], tour['time']):
            return jsonify({'success': False, 'message': '该班次已发车，不能预订'})
        
        # 检查每个座位是否可用
        bookings = storage.get_bookings()
        all_taken_seats = []
        for b in bookings:
            if b['tour_id'] == tour_id:
                all_taken_seats.extend(b.get('seat_numbers', []))
        
        for seat in seat_numbers:
            if seat in all_taken_seats:
                return jsonify({'success': False, 'message': f'{seat}号座位已被预订'})
        
        # 检查是否超过剩余座位数
        available = tour['max_seats'] - tour['booked']
        if len(seat_numbers) > available:
            return jsonify({'success': False, 'message': f'剩余车位不足，仅剩{available}个'})
        
        # 生成预订码
        booking_code = 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # 保存预订
        booking = {
            'code': booking_code,
            'name': name,
            'phone': phone,
            'seat_numbers': seat_numbers,
            'tour_id': tour_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        storage.add_booking(booking)
        
        return jsonify({
            'success': True,
            'message': '预订成功',
            'booking_code': booking_code
        })
            
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
        
        tour_data = {
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'vehicle_model': vehicle_model,
            'max_seats': max_seats
        }
        
        tour_id = storage.add_tour(tour_data)
        
        return jsonify({'success': True, 'tour_id': tour_id})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/delete_tour', methods=['POST'])
def api_delete_tour():
    try:
        data = request.get_json()
        tour_id = data.get('tour_id')
        
        storage.delete_tour(tour_id)
        return jsonify({'success': True, 'message': '班次已删除'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_tour_bookings', methods=['GET'])
def api_get_tour_bookings():
    try:
        tour_id = int(request.args.get('tour_id'))
        
        bookings = storage.get_bookings()
        tour_bookings = [b for b in bookings if b['tour_id'] == tour_id]
        
        return jsonify({'success': True, 'data': tour_bookings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/search_booking', methods=['GET'])
def api_search_booking():
    query = request.args.get('q', '').lower()
    
    bookings = storage.get_bookings()
    results = []
    
    for booking in bookings:
        if (query in booking['code'].lower() or 
            query in booking['phone'] or
            query in booking['name'].lower()):
            results.append(booking)
    
    return jsonify({'success': True, 'data': results})

# 添加一个重置路由，用于测试
@app.route('/reset')
def reset_data():
    storage.reset()
    return "数据已重置，<a href='/'>返回首页</a>"

# Vercel专用
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
