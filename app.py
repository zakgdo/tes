from flask import Flask, request, jsonify, session, redirect, render_template
import json
import random
import string
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# 最简单的数据存储
tours = []
bookings = []
next_tour_id = 1

# 添加一些示例数据
tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
after_tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

tours = [
    {
        'id': 1,
        'date': tomorrow,
        'time': '08:00',
        'destination': '上海南站',
        'vehicle_model': '大巴',
        'max_seats': 6,
        'booked': 0
    }
]
next_tour_id = 2

# 最简单的主页
@app.route('/')
def home():
    return render_template('index.html', valid_tours=tours, valid_count=len(tours))

# 最简单的班次页面
@app.route('/tours')
def tours_page():
    return render_template('tours.html', valid_tours=tours)

# 最简单的预订页面
@app.route('/book/<int:tour_id>')
def book_page(tour_id):
    tour = next((t for t in tours if t['id'] == tour_id), None)
    if not tour:
        return "班次不存在"
    
    # 获取已预订座位
    taken_seats = []
    for b in bookings:
        if b['tour_id'] == tour_id:
            taken_seats.extend(b.get('seat_numbers', []))
    
    return render_template('book.html', tour=tour, taken_seats=taken_seats)

# 最简单的管理登录（直接访问，不需要密码）
@app.route('/admin')
def admin_page():
    return render_template('admin.html',
                         tours_db=tours,
                         bookings_db=bookings,
                         total_tours=len(tours),
                         total_bookings_count=len(bookings))

# 最简单的创建班次
@app.route('/api/create_tour', methods=['POST'])
def api_create_tour():
    global next_tour_id
    
    try:
        data = request.get_json()
        
        tour = {
            'id': next_tour_id,
            'date': data.get('date'),
            'time': data.get('time'),
            'destination': data.get('destination'),
            'vehicle_model': data.get('vehicle_model', '未指定'),
            'max_seats': int(data.get('max_seats', 6)),
            'booked': 0
        }
        
        tours.append(tour)
        next_tour_id += 1
        
        return jsonify({'success': True, 'tour_id': tour['id']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# 最简单的预订
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
        
        # 找到班次
        tour = next((t for t in tours if t['id'] == tour_id), None)
        if not tour:
            return jsonify({'success': False, 'message': '班次不存在'})
        
        # 检查座位是否可用
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
        
        bookings.append(booking)
        tour['booked'] += len(seat_numbers)
        
        return jsonify({
            'success': True,
            'message': '预订成功',
            'booking_code': booking_code
        })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Vercel专用
application = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
